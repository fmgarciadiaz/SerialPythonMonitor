import struct
import unittest
from unittest.mock import patch, Mock
import zlib
from test_spi_native import adc_frame
from transport.unoq_usb import Decoder, ProtocolError, Connection, usb_devices


def seal(frame):
    frame[-4:] = struct.pack('<I', zlib.crc32(frame[:-4]))
    return frame


class USBDecoderTests(unittest.TestCase):
    def test_fragmented_and_combined_reads(self):
        a = adc_frame(count=34, index=2014)
        b = adc_frame(seq=1, index=2048, timestamp=(0xfffffff0+34*32)&0xffffffff)
        decoder = Decoder()
        samples=[]
        for byte in a:
            samples.extend(decoder.feed(bytes([byte])))
        samples.extend(decoder.feed(b))
        self.assertEqual((decoder.blocks, decoder.pairs), (2,87))
        self.assertEqual(samples[0],(0xfffffff0,0,16383,2014))
        self.assertEqual(samples[-1][3],2100)
        self.assertEqual(len(decoder.buffer),0)

    def test_crc_header_metadata_and_padding(self):
        for offset in (0,4,6,12,48,64,66,67,68,72,507):
            frame=adc_frame(); frame[offset]^=1; seal(frame)
            with self.subTest(offset=offset),self.assertRaises(ProtocolError):
                Decoder().feed(frame)
        frame=adc_frame();frame[100]^=1
        with self.assertRaisesRegex(ProtocolError,'CRC'):
            Decoder().feed(frame)

    def test_all_hardware_errors_are_fatal(self):
        for offset in (20,24,28,36,56,60,76):
            frame=adc_frame();struct.pack_into('<I',frame,offset,1);seal(frame)
            with self.subTest(offset=offset),self.assertRaises(ProtocolError):
                Decoder().feed(frame)

    def test_missing_blocks_samples_ack_and_timestamp(self):
        for offset in (8,16,52,80):
            decoder=Decoder();decoder.feed(adc_frame())
            frame=adc_frame(seq=1,index=53,timestamp=(0xfffffff0+53*32)&0xffffffff)
            frame[offset]^=1;seal(frame)
            with self.subTest(offset=offset),self.assertRaises(ProtocolError):
                decoder.feed(frame)
        frame=adc_frame();struct.pack_into('<H',frame,84,16384);seal(frame)
        with self.assertRaisesRegex(ProtocolError,'rango'):
            Decoder().feed(frame)

    def test_wrap_and_no_partial_sample_delivery_on_error(self):
        decoder=Decoder();decoder.feed(adc_frame(index=0xffffffff,count=1))
        frame=adc_frame(seq=1,index=0,count=1,timestamp=16)
        struct.pack_into('<I',frame,72,0x200000);seal(frame)
        self.assertEqual(decoder.feed(frame)[0][3],0)
        bad=adc_frame(seq=2,index=1,timestamp=48)
        struct.pack_into('<I',bad,72,0x200000)
        struct.pack_into('<H',bad,92,16384);seal(bad)
        with self.assertRaises(ProtocolError):
            decoder.feed(bad)
        self.assertEqual(decoder.pairs,2)

    def test_only_usb_devices_and_own_tunnel_cleanup(self):
        with patch('transport.unoq_usb.adb',return_value='List of devices attached\nQ device usb:123\n192.168.0.1:5555 device\nX unauthorized usb:345'):
            self.assertEqual(usb_devices(),['Q'])
        conn=Connection('Q');conn.local_port=12345;conn.socket=Mock()
        with patch('transport.unoq_usb.adb') as adb:
            conn.close();conn.close()
            adb.assert_called_once_with('-s','Q','forward','--remove','tcp:12345')
