import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from tools.private_numpy_any_trace_v20 import trace_numpy_any


class NumpyAnyTraceTests(unittest.TestCase):
    def test_records_main_thread_callsite_and_restores_exact_function(self):
        original = np.any
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'trace.jsonl'
            with trace_numpy_any(path):
                self.assertTrue(np.any(np.array([False, True])))
                self.assertFalse(np.any(np.array([False, False])))
            entries = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertIs(np.any, original)
        self.assertEqual([item['stage'] for item in entries],
                         ['enter', 'exit', 'enter', 'exit'])
        self.assertEqual(entries[0]['file'], __file__)
        self.assertEqual(entries[0]['shape'], [2])


if __name__ == '__main__':
    unittest.main()
