import struct
import unittest
import zlib
from experimentos.radio_io_process_v17.prototype import Audio
from experimentos.radio_io_process_v17.wire_adapter import ProtocolIngress,ChunkRequests
from monitor.v17.receiver.unoq_usb import ProtocolError
from tests.v17.test_compact_protocol import packet,seal


def ack(sequence=0,rid=0x80000000,session=11):
    p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',4,12,sequence,972)
    struct.pack_into('<IIBBHIIIIII',p,16,rid,session,1,0,29,480,0,48000,40000,7,30)
    return seal(p)


class WireTests(unittest.TestCase):
    def test_fragmented_mixed_frames_keep_ack_before_following_samples(self):
        events=[];ingress=ProtocolIngress(lambda kind,value:events.append((kind,value)))
        data=packet(count=2)+ack(1)+packet(index=2,count=2,t0=16,seq=2)
        for i in range(0,len(data),137):ingress.feed(data[i:i+137])
        self.assertEqual([kind for kind,_ in events],['samples','wav','samples'])
        self.assertEqual(events[1][1].request_id,0x80000000)
        self.assertEqual([row[3] for kind,rows in events if kind=='samples' for row in rows],[0,1,2,3])
        self.assertEqual(ingress.eof(),'transport_eof')
        with self.assertRaises(RuntimeError):ingress.feed(b'')

    def test_ack_callback_runs_before_next_adc_frame_is_decoded(self):
        observed=[]
        def callback(kind,value):
            if kind=='wav':observed.append(ingress.decoder.previous_index)
        ingress=ProtocolIngress(callback)
        ingress.feed(packet(count=2)+ack(1)+packet(index=2,count=2,t0=16,seq=2))
        self.assertEqual(observed,[1]);self.assertEqual(ingress.decoder.previous_index,3)

    def test_contradictory_wav_status_is_rejected_by_existing_decoder(self):
        for offset,value,fmt in ((26,31,'<H'),(32,481,'<I'),(48,31,'<I'),(52,1,'<B')):
            frame=bytearray(ack());struct.pack_into(fmt,frame,offset,value)
            ingress=ProtocolIngress(lambda *_:self.fail('Invalid ACK reached consumer'))
            with self.assertRaises(ProtocolError):ingress.feed(seal(frame))

    def test_crc_sequence_and_adc_discontinuity_poison_ingress(self):
        broken=bytearray(ack());broken[100]^=1
        cases=[bytes(broken),packet(count=2)+ack(2),
               packet(count=2)+packet(index=3,count=2,t0=16,seq=1)]
        for data in cases:
            with self.subTest(length=len(data)):
                ingress=ProtocolIngress(lambda *_:None)
                with self.assertRaises(ProtocolError):ingress.feed(data)
                with self.assertRaises(RuntimeError):ingress.feed(ack())

    def test_partial_eof_is_error_and_retention_is_one_frame(self):
        ingress=ProtocolIngress(lambda *_:None);ingress.feed(ack()[:991])
        self.assertEqual(len(ingress.decoder.buffer),991)
        with self.assertRaises(ProtocolError):ingress.eof()

    def test_callback_failure_stops_before_next_frame(self):
        seen=[]
        def callback(kind,value):
            seen.append(kind);raise RuntimeError('consumer failed')
        ingress=ProtocolIngress(callback)
        with self.assertRaisesRegex(RuntimeError,'consumer failed'):ingress.feed(ack()+packet(seq=1))
        self.assertEqual(seen,['wav']);self.assertIsNone(ingress.decoder.previous_index)
        self.assertTrue(ingress.closed)

    def test_payload_bound_rejects_before_decoding(self):
        ingress=ProtocolIngress(lambda *_:None)
        for data in (bytearray(992),bytes(32*992+1)):
            with self.assertRaises(ValueError):ingress.feed(data)
        self.assertEqual(len(ingress.decoder.buffer),0)

    def test_real_chunk_encoding_and_ack_correlation_after_cancel(self):
        requests=ChunkRequests();rid,encoded=requests.encode(Audio(1,11,0,b'\x01\x00'*480))
        self.assertEqual(struct.unpack_from('<4sHHII',encoded),(b'SCP1',4,13,rid,972))
        self.assertEqual(struct.unpack_from('<IIHH',encoded,16),(11,0,480,0))
        self.assertEqual(zlib.crc32(encoded[:988]),struct.unpack_from('<I',encoded,988)[0])
        requests.cancel();new,_=requests.encode(Audio(2,11,0,bytes(960)))
        events=[];ingress=ProtocolIngress(lambda kind,value:events.append(value))
        ingress.feed(ack(rid=rid)+ack(1,rid=new))
        self.assertFalse(requests.acknowledge(events[0],2))
        self.assertTrue(requests.acknowledge(events[1],2))
        with self.assertRaises(ValueError):requests.acknowledge(events[1],2)

    def test_real_rid_range_never_emits_reserved_upper_value(self):
        requests=ChunkRequests();requests.journal.next_rid=0xfffffffd
        rid,_=requests.encode(Audio(1,11,0,bytes(960)))
        self.assertEqual(rid,0xfffffffe)
        with self.assertRaises(ValueError):requests.encode(Audio(1,11,480,bytes(960)))
