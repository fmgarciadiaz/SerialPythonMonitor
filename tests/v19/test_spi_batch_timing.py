import struct
import unittest
import zlib
from tools.spi_batch_timing_v19 import BatchTiming
from tools.relay_wire_metrics_v19 import WireMetrics
from tests.v19.test_relay_wire_metrics import packet


def timed(sequence,prepare=10,check=20,count=4,dropped=0):
    p=bytearray(packet())
    struct.pack_into('<I',p,8,sequence)
    struct.pack_into('<II',p,40,prepare,check)
    struct.pack_into('<I',p,56,dropped)
    struct.pack_into('<H',p,64,count)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return bytes(p)


class BatchTimingTests(unittest.TestCase):
    def test_halves_dedup_and_previous_batch_coverage_including_empty_rf(self):
        observer=WireMetrics()
        observer.feed(timed(10)+timed(11)+timed(12,prepare=30,check=40,count=0)+timed(13,count=0))
        groups=observer.report()['spi_batch_timing']['groups']
        self.assertEqual(sum(g['prepare']['count'] for g in groups),2)
        known=next(g for g in groups if g['previous_batch']!='unknown')
        self.assertEqual(known['previous_batch'],'acquisition:rf+rf')
        self.assertEqual(known['prepare']['mean_us'],30)
        self.assertEqual(known['check']['mean_us'],40)
        self.assertEqual(known['prepare']['histogram'][3],1)

    def test_empty_error_frame_is_not_silently_classified_as_success(self):
        with self.assertRaisesRegex(ValueError,'Invalid acquisition'):
            WireMetrics().feed(timed(0,count=0,dropped=1))

    def test_empty_status_updates_health_without_reweighting_node_send(self):
        observer=WireMetrics();observer.feed(timed(0))
        p=bytearray(timed(1,count=0))
        struct.pack_into('<I',p,92,7);struct.pack_into('<I',p,104,0)
        struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
        observer.feed(p)
        summary=observer.report()['all']
        self.assertEqual(summary['mcu_queue_peak'],7)
        self.assertEqual(summary['min_slack_ticks'],0)
        self.assertEqual(summary['frames'],1)
        self.assertEqual(summary['empty_status_frames'],1)
        self.assertEqual(summary['samples'],4)
        self.assertEqual(summary['send_nodes'],1)

    def test_previous_epoch_boundary_is_explicit(self):
        observer=WireMetrics();observer.feed(timed(0)+timed(1))
        p=bytearray(timed(2))
        struct.pack_into('<I',p,76,4) # Epoch2, previous batch was epoch1.
        struct.pack_into('<I',p,988,zlib.crc32(p[:988]));observer.feed(p)
        groups=observer.report()['spi_batch_timing']['groups']
        self.assertEqual({g['previous_origin'] for g in groups},{'unknown','different_epoch_profile'})

    def test_epoch_wrap_bound_and_histogram_limits(self):
        metrics=BatchTiming()
        metrics.observe(1,0x7fffffff,'playing',0,5000,None)
        metrics.observe(1,0,'playing',10,50,None)
        metrics.observe(2,0,'playing',20,60,None)
        group=metrics.report()['groups'][0]
        self.assertEqual(group['prepare']['count'],3)
        self.assertEqual(group['prepare']['zero_count'],1)
        self.assertEqual(group['prepare']['mean_us'],10)
        self.assertEqual(group['check']['histogram'][-1],1)
        for i in range(130):metrics.observe(3,i,str(i),1,1,None)
        self.assertEqual(len(metrics.groups),128)
        self.assertEqual(metrics.omitted,3)
