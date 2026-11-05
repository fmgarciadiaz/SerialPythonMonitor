import struct
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib
import numpy as np
from tools.relay_wire_metrics_v19 import WireMetrics,observe_connection,ACK_LATENCY_ENV
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
from monitor.v19.receiver.unoq_wav import chunk
from tests.v19.test_relay_wire_metrics import packet


def reply(rid,session=9):
    p=bytearray(packet(kind=12))
    struct.pack_into('<II',p,16,rid,session)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return bytes(p)


class RawAckTests(unittest.TestCase):
    def test_optional_observer_restores_inline_handler_after_exception(self):
        original=OutputReceiver._process_decoder_events
        connection=SimpleNamespace(read=lambda:b'')
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{ACK_LATENCY_ENV:'1'}):
            with self.assertRaisesRegex(RuntimeError,'screen'):
                with observe_connection(connection,Path(folder)/'metrics.json'):
                    self.assertIsNot(OutputReceiver._process_decoder_events,original)
                    self.assertTrue(OutputReceiver._radio_chunk_ack_refresh)
                    raise RuntimeError('screen')
        self.assertIs(OutputReceiver._process_decoder_events,original)

    def test_raw_arrival_and_decode_delay_are_distinct_and_correlated(self):
        rid=0x80000001;observer=WireMetrics(raw_ack_latency=True)
        with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10):
            observer.sent(chunk(rid,9,0,np.zeros(480,dtype=np.uint16)))
        observer.feed(reply(rid),received_at=10.025)
        receiver=SimpleNamespace(wav_inflight={rid:(10,13)},
            decoder=SimpleNamespace(events=[('wav',SimpleNamespace(request_id=rid))]))
        with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10.030):
            observer.decoded_events(receiver)
        r=observer.report()['raw_chunk_ack_latency']
        self.assertEqual((r['matched'],r['decoded']),(1,1))
        self.assertAlmostEqual(r['raw_max_ms'],25)
        self.assertAlmostEqual(r['decode_max_ms'],5)
        self.assertAlmostEqual(r['slow'][0]['decoded_roundtrip_ms'],30)
        self.assertFalse(observer.raw_pending or observer.raw_receipts)

    def test_incomplete_unknown_and_wrong_session_cannot_complete_timing(self):
        rid=0x80000001;observer=WireMetrics(raw_ack_latency=True)
        with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10):
            observer.sent(chunk(rid,9,0,np.zeros(480,dtype=np.uint16)))
        observer.feed(reply(rid,10),received_at=10.01)
        observer.feed(reply(rid+1),received_at=10.02)
        data=reply(rid);observer.feed(data[:200],received_at=10.03)
        self.assertEqual(observer.raw_ack_count,0)
        observer.feed(data[200:],received_at=10.04)
        self.assertEqual(observer.raw_ack_count,1)
        self.assertAlmostEqual(observer.raw_ack_max_ms,40)

    def test_pending_tracking_is_bounded_without_touching_commands(self):
        observer=WireMetrics(raw_ack_latency=True)
        with patch('tools.relay_wire_metrics_v19.time.monotonic',return_value=10):
            for i in range(100):observer.sent(chunk(0x80000001+i,9,i*480,np.zeros(480,dtype=np.uint16)))
        self.assertEqual(len(observer.raw_pending),64)
        self.assertEqual(observer.raw_ack_omitted,36)
