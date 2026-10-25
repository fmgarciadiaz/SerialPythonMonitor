import unittest
import numpy as np
from monitor.v18.io.rf_batch import take_rf_prefix


class RfPrefixTests(unittest.TestCase):
    def test_delayed_backlog_is_split_without_loss_reorder_or_extra_copy(self):
        original=np.arange(4000,dtype=np.uint32).reshape(1000,4)
        chunks=[original[:17],original[17:550],original[550:]]
        received=[]
        while chunks:
            prefix,chunks,count=take_rf_prefix(chunks,40)
            self.assertLessEqual(count,40)
            self.assertEqual(count,sum(map(len,prefix)))
            self.assertTrue(all(np.shares_memory(chunk,original) for chunk in prefix+chunks))
            received.extend(prefix)
        np.testing.assert_array_equal(np.concatenate(received),original)

    def test_small_batch_and_empty_input(self):
        array=np.ones((3,4),dtype=np.uint32)
        prefix,remaining,count=take_rf_prefix([array],40)
        self.assertEqual((len(prefix),remaining,count),(1,[],3))
        self.assertEqual(take_rf_prefix([],40),([],[],0))
        with self.assertRaises(ValueError):take_rf_prefix([array],0)
