import queue
import struct
import unittest
from experimentos.radio_io_process_v17.audio_pump import AudioPump
from experimentos.radio_io_process_v17.prototype import Audio
from monitor.v17.receiver import unoq_wav as wav
from tests.v17.test_compact_protocol import packet,seal


class LocalTransport:
    """Deterministic SCP1 peer; no DAC clock, socket, hardware or Qt."""
    def __init__(self,write_limit=992,read_limit=32*992):
        self.write_limit=write_limit;self.read_limit=read_limit
        self.sent=bytearray();self.incoming=bytearray();self.frames=[];self.close_calls=0
        self.session=0;self.total=0;self.accepted=self.played=0;self.state=wav.State.IDLE
        self.sequence=0;self.eof=False;self.fail_send=False;self.block_send=False;self.drop=False

    def send(self,data):
        if self.fail_send:raise OSError('injected write error')
        if self.block_send:raise BlockingIOError()
        count=min(len(data),self.write_limit);self.sent.extend(data[:count])
        if len(self.sent)==992:
            frame=bytes(self.sent);self.sent.clear();self.frames.append(frame)
            kind=struct.unpack_from('<H',frame,6)[0];rid=struct.unpack_from('<I',frame,8)[0]
            session=struct.unpack_from('<I',frame,16)[0]
            if kind==13:
                offset,points=struct.unpack_from('<IH',frame,20)
                if session!=self.session or offset!=self.accepted:raise AssertionError('Invalid peer chunk')
                self.accepted+=points
            else:
                op=frame[20]
                if op==1:
                    self.session=session;self.total=struct.unpack_from('<I',frame,24)[0]
                    self.accepted=self.played=0;self.state=wav.State.BUFFERING
                elif op==2:self.state=wav.State.PLAYING
                elif op==3:self.state=wav.State.IDLE
            response=bytearray(992)
            struct.pack_into('<4sHHII',response,0,b'SCP1',4,12,self.sequence,972);self.sequence+=1
            free=30-(self.accepted-self.played+479)//480
            struct.pack_into('<IIBBHIIIIII',response,16,rid,self.session,self.state,0,free,
                             self.accepted,self.played,self.total,40000,7,30)
            if not self.drop:self.incoming.extend(seal(response))
        return count

    def recv(self,limit):
        if self.incoming:
            count=min(limit,self.read_limit,len(self.incoming))
            result=bytes(self.incoming[:count]);del self.incoming[:count];return result
        if self.eof:return b''
        raise BlockingIOError()

    def close(self):self.close_calls+=1


class PumpTests(unittest.TestCase):
    def setup_pump(self,**kwargs):
        transport=LocalTransport(**kwargs);pump=AudioPump(transport)
        self.addCleanup(pump.close)
        now=0.
        def until(predicate,steps=500):
            nonlocal now
            for _ in range(steps):
                now+=.001;pump.turn(now)
                if predicate():return now
            self.fail('Condition not reached')
        until(lambda:pump.control.state=='ready')
        return transport,pump,until

    def test_partial_write_and_fragmented_read_complete_radio_or_wav_session(self):
        peer,pump,until=self.setup_pump(write_limit=37,read_limit=53)
        pump.begin(1,11,960,40000,pump.now)
        pump.enqueue(Audio(1,11,0,bytes(960)));pump.enqueue(Audio(1,11,480,bytes(960)))
        until(lambda:pump.control.state=='playing')
        self.assertEqual([f[20] for f in peer.frames if struct.unpack_from('<H',f,6)[0]==11],[0,1,2])
        self.assertEqual(len([f for f in peer.frames if struct.unpack_from('<H',f,6)[0]==13]),2)
        self.assertEqual(pump.control.credits.accepted,960)
        pump.stop(pump.now);until(lambda:pump.control.state=='stopped')
        pump.close();pump.close();self.assertEqual(peer.close_calls,1)

    def test_pcm_queue_is_bounded_and_full_does_not_advance_offset(self):
        peer,pump,until=self.setup_pump();pump.capacity=1
        pump.begin(1,11,960,40000,pump.now);pump.enqueue(Audio(1,11,0,bytes(960)))
        with self.assertRaises(queue.Full):pump.enqueue(Audio(1,11,480,bytes(960)))
        self.assertEqual(pump.queued_end,480)
        pump.stop(pump.now);until(lambda:pump.control.state=='stopped')
        self.assertEqual(pump.cancelled_pcm,1)
        self.assertEqual([f[20] for f in peer.frames],[0,3])
        self.assertEqual(struct.unpack_from('<I',peer.frames[-1],16)[0],0)

    def test_stop_finishes_partial_frame_before_sending_stop(self):
        peer,pump,until=self.setup_pump(write_limit=97)
        pump.begin(1,11,960,40000,pump.now)
        pump.enqueue(Audio(1,11,0,bytes(960)))
        until(lambda:pump.control.state=='buffering' and pump.outgoing is not None and pump.written>0)
        pump.stop(pump.now);until(lambda:pump.control.state=='stopped')
        self.assertEqual(len(peer.sent),0)
        self.assertEqual(peer.frames[-1][20],3)
        self.assertEqual(pump.control.credits,None)

    def test_write_failure_is_not_retried_or_reported_as_restored(self):
        peer,pump,until=self.setup_pump();peer.fail_send=True
        pump.begin(1,11,960,40000,pump.now)
        with self.assertRaisesRegex(OSError,'write error'):pump.turn(pump.now+.001)
        self.assertTrue(pump.closed);self.assertEqual(pump.control.state,'fault')
        self.assertEqual(peer.close_calls,1)
        with self.assertRaises(RuntimeError):pump.turn(pump.now+.002)
        pump.close();self.assertEqual(peer.close_calls,1)

    def test_eof_and_truncated_eof_are_terminal(self):
        for partial in (b'',b'SCP1'):
            peer,pump,until=self.setup_pump();peer.incoming.extend(partial);peer.eof=True
            with self.assertRaises((EOFError,ValueError,RuntimeError)):
                # ProtocolError derives from RuntimeError.
                for _ in range(3):pump.turn(pump.now+.001)
            self.assertTrue(pump.closed);self.assertEqual(pump.control.state,'fault')

    def test_missing_ack_times_out_with_no_retry(self):
        peer,pump,until=self.setup_pump();peer.drop=True
        pump.begin(1,11,960,40000,pump.now);pump.turn(pump.now+.001)
        count=len(peer.frames)
        with self.assertRaises(TimeoutError):pump.turn(pump.now+.51)
        self.assertEqual(len(peer.frames),count);self.assertTrue(pump.closed)

    def test_blocked_partial_write_has_bounded_stop_deadline(self):
        peer,pump,until=self.setup_pump(write_limit=31)
        pump.begin(1,11,960,40000,pump.now);pump.turn(pump.now+.001)
        self.assertGreater(pump.written,0)
        peer.block_send=True;pump.stop(pump.now)
        with self.assertRaises(TimeoutError):pump.turn(pump.now+.51)
        self.assertTrue(pump.closed);self.assertEqual(peer.close_calls,1)

    def test_ack_refills_before_next_adc_frame_is_delivered(self):
        peer,pump,until=self.setup_pump()
        pump.begin(1,11,1440,40000,pump.now)
        for i in range(3):pump.enqueue(Audio(1,11,i*480,bytes(960)))
        until(lambda:pump.control.state=='play_wait')
        peer.incoming.extend(packet(seq=peer.sequence,count=2));peer.sequence+=1
        seen=[]
        def observe(kind,value):
            if kind=='samples':
                seen.append(len([f for f in peer.frames if struct.unpack_from('<H',f,6)[0]==13]))
        pump.on_event=observe
        until(lambda:bool(seen))
        self.assertEqual(seen,[3])
        pump.stop(pump.now);until(lambda:pump.control.state=='stopped')

    def test_full_dac_is_queried_even_while_pcm_is_waiting(self):
        peer,pump,until=self.setup_pump();pump.control.prebuffer=30*480
        pump.begin(1,11,32*480,40000,pump.now)
        for i in range(32):pump.enqueue(Audio(1,11,i*480,bytes(960)))
        until(lambda:pump.control.state=='playing' and pump.control.offset==30*480)
        self.assertEqual(pump.control.credits.available,0)
        peer.played=480 # Only a confirmed QUERY may make this free slot usable.
        until(lambda:pump.control.offset==31*480)
        queries=[f for f in peer.frames if struct.unpack_from('<H',f,6)[0]==11 and f[20]==0]
        self.assertGreaterEqual(len(queries),2)
        pump.stop(pump.now);until(lambda:pump.control.state=='stopped')

    def test_zero_byte_write_is_terminal_without_retry(self):
        peer,pump,until=self.setup_pump();peer.write_limit=0
        pump.begin(1,11,960,40000,pump.now)
        with self.assertRaises(ConnectionError):pump.turn(pump.now+.001)
        self.assertTrue(pump.closed);self.assertEqual(peer.close_calls,1)
