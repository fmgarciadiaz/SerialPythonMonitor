import gc
import unittest
from experimentos.radio_ipc_compact_v17.gc_audit import GcAudit,observe_gc


class GcAuditTests(unittest.TestCase):
    def test_exact_interval_generation_and_cpu(self):
        now=[10.];cpu=[1.]
        audit=GcAudit(clock=lambda:now[0],cpu=lambda:cpu[0],thread=lambda:7)
        audit.observe('start',dict(generation=2))
        now[0]=10.125;cpu[0]=1.1
        audit.observe('stop',dict(generation=2,collected=4,uncollectable=1))
        row=audit.snapshot()['top'][0]
        self.assertAlmostEqual(row['wall_ms'],125)
        self.assertAlmostEqual(row['thread_cpu_ms'],100)
        self.assertEqual(row['collected'],4)
        self.assertEqual(audit.generations[2]['over100ms'],1)

    def test_bounded_storage_and_unmatched_stop(self):
        now=[0.];audit=GcAudit(clock=lambda:now[0],cpu=lambda:0.,thread=lambda:1)
        audit.observe('stop',dict(generation=1))
        for _ in range(1000):
            audit.observe('start',dict(generation=0));now[0]+=.001
            audit.observe('stop',dict(generation=0))
        self.assertEqual(len(audit.top),16);self.assertEqual(len(audit.recent),64)
        self.assertEqual(audit.unmatched,1);self.assertFalse(audit.pending)

    def test_registration_is_reversed_on_exception_without_gc_policy_change(self):
        callbacks=list(gc.callbacks);enabled=gc.isenabled();thresholds=gc.get_threshold()
        audit=GcAudit()
        with self.assertRaisesRegex(RuntimeError,'test'):
            with observe_gc(audit):
                self.assertIn(audit.observe,gc.callbacks)
                raise RuntimeError('test')
        self.assertEqual(gc.callbacks,callbacks)
        self.assertEqual(gc.isenabled(),enabled);self.assertEqual(gc.get_threshold(),thresholds)

    def test_different_thread_stop_does_not_match_another_collection(self):
        thread=[1];audit=GcAudit(thread=lambda:thread[0])
        audit.observe('start',dict(generation=0));thread[0]=2
        audit.observe('stop',dict(generation=0))
        self.assertEqual(audit.unmatched,1);self.assertEqual(len(audit.pending),1)


if __name__=='__main__':unittest.main()
