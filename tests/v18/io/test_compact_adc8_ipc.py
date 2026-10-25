import pickle
import unittest

import numpy as np

from monitor.v18.io.rf_batch import (
    CompactAdc8RfBatch, RawRfBatch, should_compact_adc8_ipc, take_rf_prefix,
)
from monitor.v18.numeric_batch import SampleClock
from monitor.v18.receiver.unoq_acquisition import Configuration


class CompactAdc8IpcTests(unittest.TestCase):
    def setUp(self):
        self.config = Configuration(8, 1600000)

    def records(self, count, first_timestamp=0xfffffff0, first_index=0xfffffff8):
        offsets = np.arange(count, dtype=np.uint32)
        records = np.zeros((count, 4), dtype=np.uint32)
        records[:, 0] = first_timestamp + offsets * self.config.period
        records[:, 1] = offsets % 256
        records[:, 3] = first_index + offsets
        return records

    def test_pickle_exact_columns_wrap_metadata_and_ownership(self):
        records = self.records(72727)
        original = RawRfBatch(records, self.config, 3, 4, 12.)
        compact = CompactAdc8RfBatch.from_records(records, self.config, 3, 4, 12.)
        self.assertFalse(np.shares_memory(compact.values, records))
        copied = pickle.loads(pickle.dumps(compact, protocol=pickle.HIGHEST_PROTOCOL))
        self.assertEqual((len(copied), copied.receiver_generation,
                          copied.receiver_batch_id, copied.published_at),
                         (len(records), 3, 4, 12.))
        before = original.materialize(SampleClock(self.config.timestamp_hz))
        after = copied.materialize(SampleClock(self.config.timestamp_hz))
        for name in before.columns:
            np.testing.assert_array_equal(after.columns[name], before.columns[name])
        self.assertLess(len(pickle.dumps(compact)), len(pickle.dumps(original)) // 8)

    def test_normal_splits_and_forced_remainder_keep_all_samples_and_clock(self):
        records = self.records(92000)
        chunks = [records[:872], records[872:53000], records[53000:]]
        expected_clock = SampleClock(self.config.timestamp_hz)
        actual_clock = SampleClock(self.config.timestamp_hz)
        ordinal = 0
        while chunks:
            if ordinal < 2:
                prefix, chunks, count = take_rf_prefix(chunks, 24000)
            else:
                prefix, chunks = chunks, []
                count = sum(map(len, prefix))
            raw = np.concatenate(prefix)
            ordinal += 1
            compact = pickle.loads(pickle.dumps(
                CompactAdc8RfBatch.from_records(raw, self.config, 9, ordinal, float(ordinal))))
            self.assertEqual(len(compact), count)
            actual = compact.materialize(actual_clock)
            expected = RawRfBatch(raw, self.config, 9, ordinal, float(ordinal)).materialize(expected_clock)
            for name in expected.columns:
                np.testing.assert_array_equal(actual.columns[name], expected.columns[name])
        self.assertEqual(ordinal, 3)

    def test_gating_and_invalid_layout(self):
        self.assertFalse(should_compact_adc8_ipc(self.config, False))
        self.assertTrue(should_compact_adc8_ipc(self.config, True))
        self.assertFalse(should_compact_adc8_ipc(Configuration(8, 40000), True))
        self.assertFalse(should_compact_adc8_ipc(Configuration(14, 40000), True))
        invalid = self.records(2).astype(np.uint16)
        with self.assertRaises(ValueError):
            CompactAdc8RfBatch.from_records(invalid, self.config, 1, 1, 1.)
        with self.assertRaises(ValueError):
            CompactAdc8RfBatch.from_records(self.records(2), Configuration(8, 40000), 1, 1, 1.)


if __name__ == '__main__':
    unittest.main()
