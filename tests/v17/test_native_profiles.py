import struct
import unittest
import zlib
from unittest.mock import patch

from monitor.v17.receiver import unoq_native
from monitor.v17.receiver.unoq_acquisition import Configuration, acquisition_request
from monitor.v17.receiver.unoq_acquisition import AcquisitionReply
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_switch import Phase, Reason
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_usb import ProtocolError


class NativeProfilesTests(unittest.TestCase):
    def test_values_clock_wrap_and_wire_identity(self):
        for bits, channels in ((8, 1), (10, 1), (14, 1), (12, 2), (16, 2)):
            profile = dict(bits=bits, channels=channels, ticks=224, node_pairs=7936)
            with patch.object(unoq_native, 'PROFILES', (profile,)):
                config = Configuration(bits, 714285)
                self.assertEqual(config.timestamp_hz, 160000000)
                self.assertEqual(config.channels, channels)
                self.assertEqual(Configuration.from_wire(bits, config.request_period).request_period,
                                 config.request_period)
                self.assertEqual(struct.unpack_from('<I', acquisition_request(0x80000001, config), 20)[0],
                                 config.request_period)
                values = [0, (1 << bits)-1, 1, (1 << bits)-2]*channels
                packet = bytearray(992)
                struct.pack_into('<4sHHII', packet, 0, b'SCP1', 4, 20, 0, 972)
                struct.pack_into('<i', packet, 32, 992)
                struct.pack_into('<IIIIHBBIII', packet, 48, config.rate, 0, 0, 0, 4,
                                 bits, channels, config.period, 0, 0)
                struct.pack_into('<I', packet, 80, 0xfffffff0)
                struct.pack_into('<8I', packet, 84, 7936, 1, 2, 100, 100, 100, 100, 1)
                packed = sum(value << (bits*i) for i, value in enumerate(values))
                used = len(values)*bits//8
                packet[116:116+used] = packed.to_bytes(used, 'little')
                def seal():
                    struct.pack_into('<I', packet, 988, zlib.crc32(packet[:988]))
                    return bytes(packet)
                rows = ConfigurationDecoder().feed(seal())
                self.assertEqual([row[1] for row in rows], values[::channels])
                self.assertEqual([row[2] for row in rows], values[1::2] if channels==2 else [0]*4)
                self.assertEqual(rows[-1][0], (0xfffffff0+3*224)&0xffffffff)
                packet[987] = 1
                with self.assertRaises(ProtocolError):
                    ConfigurationDecoder().feed(seal())

    def test_unaccepted_native_profile_rejected(self):
        with self.assertRaises(ValueError):
            Configuration.from_wire(10, (8192 << 16) | 175)

    def test_same_rate_legacy_and_native_remain_distinct(self):
        profile = dict(bits=14, channels=1, ticks=242, node_pairs=7936)
        with patch.object(unoq_native, 'PROFILES', (profile,)):
            native = Configuration(14, 661157)
            legacy = Configuration.from_wire(14, 242)
            self.assertNotEqual(native, legacy)
            self.assertEqual(legacy.node_pairs, 2048)
            self.assertEqual(native.node_pairs, 7936)

    def test_receiver_ack_matches_full_profile_code(self):
        profile = dict(bits=10, channels=1, ticks=176, node_pairs=8192)
        with patch.object(unoq_native, 'PROFILES', (profile,)):
            config = Configuration(10, 909090)
            receiver = OutputReceiver(object(), lambda rows: None)
            receiver.config_pending = (0x80000001, config)
            def reply(period):
                return AcquisitionReply(0x80000001,10,config,Phase.APPLIED,Reason.OK,period,1)
            receiver.decoder.events = [('configuration',reply(config.request_period))]
            receiver._process_decoder_events()
            self.assertEqual(receiver.config_applied.active,config)
            receiver.decoder.events = [('configuration',reply(config.period))]
            with self.assertRaises(ProtocolError): receiver._process_decoder_events()
