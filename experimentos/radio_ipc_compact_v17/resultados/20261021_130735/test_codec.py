import pickle
from dataclasses import replace
from types import SimpleNamespace
import unittest

import numpy as np

from experimentos.radio_ipc_compact_v17.codec import compact, expand, RegularRadioBatch
from monitor.v17.digital_filter import FilterConfig
from monitor.v17.processing import BatchProcessor, ProcessingSettings
from monitor.v17.receiver.unoq_acquisition import Configuration


CONFIG = Configuration(8, 1600000)
SETTINGS = ProcessingSettings(acquisition=CONFIG, radio_enabled=True, radio_frequency=50000)


def batch(first=0, count=4096, start_time=None):
    offsets = np.arange(count)
    indices = ((offsets.astype(np.uint64)+first) & 0xffffffff).astype(np.uint32)
    times = offsets*CONFIG.dt_us + (first*CONFIG.dt_us if start_time is None else start_time)
    return SimpleNamespace(columns={'Muestra': indices, 'Tiempo (us)': times,
        'CH1': 1.65+.2*np.cos(offsets*.4)}, acquisition=CONFIG)


class CodecTests(unittest.TestCase):
    def test_roundtrip_exact_readonly_strided_and_wrap(self):
        for first in (0, 100000, 0xfffffff0):
            original = batch(first)
            for value in original.columns.values():
                value.flags.writeable = False
            packed = compact(original, SETTINGS)
            self.assertIsInstance(packed, RegularRadioBatch)
            restored = expand(pickle.loads(pickle.dumps(packed)))
            for key, value in original.columns.items():
                self.assertEqual(value.dtype, restored.columns[key].dtype)
                self.assertEqual(value.tobytes(), restored.columns[key].tobytes())
            sliced = SimpleNamespace(columns={k:v[::2] for k,v in original.columns.items()}, acquisition=CONFIG)
            self.assertIs(compact(sliced, SETTINGS), sliced)

    def test_damaged_metadata_is_not_regularized(self):
        for key, delta in (('Muestra', 1), ('Tiempo (us)', .000001), ('Tiempo (us)', float('nan'))):
            original = batch()
            original.columns[key][100] += delta
            self.assertIs(compact(original, SETTINGS), original)

    def test_empty_and_unsupported_paths_fall_back(self):
        original = batch(count=0)
        self.assertIs(compact(original, SETTINGS), original)
        for settings in (replace(SETTINGS, radio_enabled=False),
                         replace(SETTINGS, filter=FilterConfig(source='CH1'))):
            original = batch()
            self.assertIs(compact(original, settings), original)
        original = batch()
        original.acquisition = Configuration(10, 100000)
        self.assertIs(compact(original, SETTINGS), original)

    def test_stream_equivalence_wrap_levels_and_generation(self):
        baseline, candidate = BatchProcessor(), BatchProcessor()
        first = 0xfffff000
        for row in range(5):
            settings = replace(SETTINGS, generation=row, radio_gain=2+row,
                continuity_epoch=1 if row >= 3 else 0)
            original = batch((first+row*4096) & 0xffffffff, start_time=row*4096*CONFIG.dt_us)
            other = expand(compact(original, settings))
            expected = baseline.process(original, settings).processing
            actual = candidate.process(other, settings).processing
            for key in ('audio', 'audio_filter'):
                np.testing.assert_array_equal(actual[key], expected[key])
            for key in ('generation', 'radio_status', 'audio_first_time_us', 'radio_key'):
                self.assertEqual(actual[key], expected[key])

    def test_cross_batch_index_and_time_gaps_still_raise(self):
        for gap in ('index', 'time'):
            processor = BatchProcessor()
            processor.process(expand(compact(batch(), SETTINGS)), SETTINGS)
            following = batch(4097 if gap == 'index' else 4096,
                              start_time=4096*CONFIG.dt_us+(1 if gap == 'time' else 0))
            with self.assertRaisesRegex(ValueError, 'Discontinuidad'):
                processor.process(expand(compact(following, SETTINGS)), SETTINGS)

    def test_radio_filter_equivalence(self):
        settings = replace(SETTINGS, filter=FilterConfig(source='RADIO', mode='bypass'))
        original = batch(count=32000)
        expected = BatchProcessor().process(original, settings).processing
        actual = BatchProcessor().process(expand(compact(original, settings)), settings).processing
        np.testing.assert_array_equal(expected['audio_filter'], actual['audio_filter'])


if __name__ == '__main__':
    unittest.main()
