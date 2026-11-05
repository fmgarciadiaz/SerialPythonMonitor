import json
from pathlib import Path
import struct
import unittest
import zlib
from monitor.v20.receiver.unoq_acquisition import Configuration,SPI_RATES
from monitor.v20.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v20.receiver.unoq_usb import ProtocolError
from monitor.v20.q_support import prepare
from monitor.v20.q_support.service import RECEIPT

ROOT=Path(__file__).resolve().parents[2]


def frame(rate=1860465,queue=12):
    c=Configuration(8,rate);p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,0,972)
    struct.pack_into('<IIIIHBBIII',p,48,rate,0,0,0,4,8,1,c.period,0,2)
    struct.pack_into('<8I',p,84,c.node_pairs,queue,queue,1,2,100,1000,1)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return p


class Sram3TrialTests(unittest.TestCase):
    def test_unqualified_v20_cannot_prepare_v19(self):
        self.assertIn('/scope-v20',prepare.APP)
        self.assertEqual(prepare.CONTAINER,'serialmonitor-usb-stream-v20')
        self.assertIn('/arduino/v20/',str(prepare.APP_SOURCES))
        with self.assertRaises(ValueError):prepare.load_acceptance(RECEIPT)
        self.assertFalse(json.loads(RECEIPT.read_text())['accepted'])

    def test_candidate_rates_available_privately_but_not_public(self):
        for rate in (2000000,2051282):
            c=Configuration(8,rate)
            self.assertEqual(c._native['queue_slots'],16)
            self.assertFalse(c._native['combined_qualified'])
            self.assertNotIn(rate,SPI_RATES)
        self.assertEqual(Configuration(8,1860465)._native['queue_slots'],16)

    def test_decoder_accepts_expanded_queue_and_checks_crc(self):
        decoder=ConfigurationDecoder();decoder.config=Configuration(8,1860465);decoder.epoch=1
        decoder.feed(frame());self.assertEqual(decoder.pairs,4)
        bad=frame();bad[118]^=1
        with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(bad)

    def test_decoder_rejects_capacity_overflow(self):
        decoder=ConfigurationDecoder();decoder.config=Configuration(8,1860465);decoder.epoch=1
        with self.assertRaises(ProtocolError):decoder.feed(frame(queue=17))
