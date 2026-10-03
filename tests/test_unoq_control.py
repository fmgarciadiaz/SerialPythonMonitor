import struct
import unittest
import zlib
from test_spi_native import adc_frame
from diagnosticos.verificar_spi import ping
from transport.unoq_usb import ProtocolError
from transport.unoq_control import StatusSession, status_request


class EchoMCU:
    """Fragmented PC socket with old DATA followed by the requested MCU ACK."""
    def __init__(self, wrong_ack=False, corrupt=False):
        self.socket=self
        self.request=bytearray()
        self.output=bytearray()
        self.sequence=0
        self.wrong_ack=wrong_ack
        self.corrupt=corrupt

    def sendall(self,data):
        self.request.extend(data)
        if len(self.request)==512:
            request_id=struct.unpack_from('<I',self.request,8)[0]
            if bytes(self.request)!=ping(request_id): raise AssertionError('Wire contract mismatch')
            self.request.clear()
            for ack in (self.sequence,request_id-1 if self.wrong_ack else request_id):
                packet=adc_frame(seq=self.sequence,index=self.sequence,count=1,timestamp=self.sequence*32)
                struct.pack_into('<I',packet,16,ack)
                packet[-4:]=struct.pack('<I',zlib.crc32(packet[:-4]))
                if self.corrupt: packet[-1]^=1
                self.output.extend(packet)
                self.sequence+=1

    def read(self):
        chunk=bytes(self.output[:37]);del self.output[:37]
        return chunk


class ControlTests(unittest.TestCase):
    def test_pc_request_is_existing_firmware_ping(self):
        for request_id in (0x80000000,0xaabbccdd,0xfffffffe):
            self.assertEqual(status_request(request_id),ping(request_id))
        for request_id in (0,0x7fffffff,0xffffffff,0x100000000):
            with self.assertRaises(ValueError):status_request(request_id)

    def test_explicit_ack_with_fragmented_requests_and_responses(self):
        session=StatusSession(EchoMCU())
        first=session.query(fragmented=True)
        second=session.query()
        self.assertEqual(first['ack'],first['request_id'])
        self.assertEqual(second['ack'],second['request_id'])
        self.assertNotEqual(first['request_id'],second['request_id'])
        self.assertEqual((first['sample_rate_hz'],first['adc_bits'],first['channels'],first['period_us']),
                         (31250,14,2,32))
        self.assertEqual(session.decoder.pairs,4)

    def test_old_or_wrong_ack_does_not_confirm(self):
        with self.assertRaises(TimeoutError):
            StatusSession(EchoMCU(wrong_ack=True)).query(timeout=0.01)

    def test_crc_still_required_for_status(self):
        with self.assertRaisesRegex(ProtocolError,'CRC'):
            StatusSession(EchoMCU(corrupt=True)).query()

    def test_nonce_wrap_skips_boot_sentinel(self):
        session=StatusSession(EchoMCU())
        session.next_id=0xfffffffe
        self.assertEqual(session.query()['request_id'],0xfffffffe)
        self.assertEqual(session.query()['request_id'],0x80000000)
