import unittest
from unittest.mock import patch

import numpy as np

from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v18.receiver.unoq_usb import ProtocolError
from monitor.v18.receiver.unoq_native import PROFILES, code
from tests.v18.io.rf_vectors import native_frame


class EventsOnlyDecoderTests(unittest.TestCase):
    def test_all_formats_preserve_events_and_continuity_without_return_copy(self):
        for bits in (8,10,12,14,16):
            for channels in (1,2):
                profile=next((p for p in PROFILES if p['bits']==bits and p['channels']==channels),None)
                if profile is None:
                    continue
                config=Configuration.from_wire(bits,code(profile))
                with self.subTest(bits=bits,channels=channels):
                    decoder=ConfigurationDecoder();decoder.numeric=True
                    for seq in range(2):
                        packet,expected=native_frame(config,index=seq*4,
                            timestamp=seq*4*config.period,sequence=seq)
                        with patch('monitor.v18.receiver.unoq_config_decoder.join_records',
                                   side_effect=AssertionError('Unused return copy')):
                            self.assertEqual(decoder.feed(packet,collect_samples=False),[])
                        np.testing.assert_array_equal(decoder.events[-1][1].array,expected)
                    self.assertEqual(decoder.pairs,8)
                    self.assertEqual(decoder.previous_index,7)

    def test_default_return_and_crc_validation_are_preserved(self):
        config=Configuration(8,1600000)
        packet,expected=native_frame(config)
        decoder=ConfigurationDecoder();decoder.numeric=True
        np.testing.assert_array_equal(decoder.feed(packet).array,expected)
        corrupted=bytearray(packet);corrupted[120]^=1
        with self.assertRaises(ProtocolError):
            ConfigurationDecoder().feed(corrupted,collect_samples=False)


if __name__=='__main__':unittest.main()
