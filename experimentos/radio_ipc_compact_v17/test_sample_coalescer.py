import unittest
import numpy as np
from monitor.v17.receiver.native_unpack import NativeRecords
from experimentos.radio_ipc_compact_v17.sample_coalescer import SampleCoalescer


def records(start,count):
    offsets=np.arange(count,dtype=np.uint64)+start
    rows=np.zeros((count,4),dtype=np.uint32)
    rows[:,0]=(offsets*100)&0xffffffff;rows[:,3]=offsets&0xffffffff
    return NativeRecords(rows)


class CoalescerTests(unittest.TestCase):
    def test_exact_order_wrap_and_originals_not_mutated(self):
        output=[];callback=output.append;c=SampleCoalescer(maximum=10)
        parts=[records(0xfffffffc,4),records(0x100000000,5),records(0x100000005,6)]
        before=[p.array.copy() for p in parts]
        for p in parts:c.push(p,callback,'same')
        c.flush()
        np.testing.assert_array_equal(np.concatenate([p.array for p in output]),np.concatenate(before))
        self.assertLessEqual(max(map(len,output)),10)
        for p,b in zip(parts,before):np.testing.assert_array_equal(p.array,b)

    def test_deadline_is_cooperative_and_maximum_is_hard(self):
        now=[0.];out=[];callback=out.append
        c=SampleCoalescer(maximum=10,clock=lambda:now[0])
        c.push(records(0,2),callback,1);now[0]=.009;c.expire();self.assertFalse(out)
        now[0]=.011;c.expire();self.assertEqual(len(out),1)
        c.push(records(2,35),callback,1);c.flush()
        self.assertLessEqual(max(map(len,out)),10)

    def test_context_and_callback_boundaries_flush_old_first(self):
        out=[];first=lambda rows:out.append(('first',len(rows)))
        second=lambda rows:out.append(('second',len(rows)))
        c=SampleCoalescer();c.push(records(0,2),first,1)
        c.push(records(2,3),second,2)
        self.assertEqual(out,[('first',2)])
        c.flush();self.assertEqual(out,[('first',2),('second',3)])

    def test_explicit_boundary_and_no_duplicate_after_callback_error(self):
        def fail(rows):raise RuntimeError('delivery failed')
        c=SampleCoalescer();c.push(records(0,3),fail,1)
        with self.assertRaisesRegex(RuntimeError,'delivery failed'):c.flush()
        self.assertEqual(c.count,0);c.flush()

    def test_many_tiny_inputs_are_bounded_and_final_flush_is_idempotent(self):
        out=[];callback=out.append;c=SampleCoalescer()
        for i in range(200):c.push(records(i,1),callback,1)
        c.flush();c.flush()
        self.assertLessEqual(c.stats['peak_parts'],32)
        self.assertEqual(sum(map(len,out)),200)

    def test_long_retention_records_bounded_timeline_and_reason(self):
        now=[0.];out=[];callback=out.append
        c=SampleCoalescer(clock=lambda:now[0])
        for i in range(20):
            c.push(records(i,1),callback,1)
            now[0]+=.05;c.expire()
        self.assertEqual(len(c.slow_top),8)
        row=c.slow_top[0]
        self.assertEqual(row['reason'],'deadline')
        self.assertAlmostEqual(row['flushed_at']-row['start'],row['age_ms']/1000)


if __name__=='__main__':unittest.main()
