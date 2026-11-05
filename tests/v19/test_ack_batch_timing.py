import unittest
from tools.ack_batch_timing_v19 import AckBatchTiming


class AckTimingTests(unittest.TestCase):
    def test_wire_fixture_matches_chunk_ack_and_native_metadata_across_reads(self):
        import struct
        import zlib
        import numpy as np
        from tools.relay_wire_metrics_v19 import WireMetrics
        from tests.v19.test_relay_wire_metrics import packet
        from tests.v19.test_spi_batch_timing import timed
        from monitor.v19.receiver.unoq_wav import chunk
        observer=WireMetrics();rid=0x80000009
        observer.sent(chunk(rid,7,0,np.zeros(480,dtype=np.uint16)))
        ack=bytearray(packet(kind=12))
        struct.pack_into('<I',ack,8,10)
        struct.pack_into('<II',ack,16,rid,7)
        struct.pack_into('<I',ack,988,zlib.crc32(ack[:988]))
        observer.feed(ack[:500]);observer.feed(ack[500:]+timed(11,prepare=123,check=156))
        summary=observer.report()['ack_batch_timing']
        self.assertEqual(summary['matched_replies'],1)
        self.assertEqual(summary['groups'][0]['ack_command'],'chunk')
        self.assertEqual(summary['groups'][0]['check']['mean_us'],156)

    def test_session_matching_second_half_and_dedup(self):
        t=AckBatchTiming();t.sent(9,7,'chunk');t.replied(10,9,7,0)
        t.native(1,10,'playing',99,99) # first half deliberately excluded
        t.native(1,11,'playing',10,20);t.native(1,11,'playing',10,20)
        t.native(1,13,'playing',30,40)
        groups=t.report()['groups']
        chunk=next(g for g in groups if g['ack_command']=='chunk')
        self.assertEqual(chunk['check']['count'],1)
        self.assertEqual(chunk['check']['mean_us'],20)
        self.assertEqual(next(g for g in groups if g['ack_command']=='no_wav_ack')['check']['mean_us'],40)
        t.sent(11,7,'query');t.replied(14,11,8,0);t.native(1,15,'playing',1,2)
        self.assertEqual(t.report()['unmatched_replies'],1)
        self.assertTrue(any(g['ack_command']=='unmatched_ack' for g in t.report()['groups']))

    def test_pending_is_bounded_and_global_query_can_match_active_session(self):
        t=AckBatchTiming()
        for n in range(70):t.sent(n,1,'chunk')
        self.assertEqual(t.report()['pending'],64);self.assertEqual(t.report()['evicted'],6)
        t.sent(100,0,'query');t.replied(10,100,22,0);t.native(1,11,'stopped',1,2)
        self.assertEqual(t.report()['groups'][0]['ack_command'],'query')
