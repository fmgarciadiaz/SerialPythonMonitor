import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from monitor.v18.io.flow_trace import record


class FlowTraceTests(unittest.TestCase):
    def test_disabled_creates_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'MONITOR_V18_FLOW_TRACE': ''}):
                record('disabled', 1)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_records_atomic_lines_across_threads(self):
        with tempfile.TemporaryDirectory() as directory:
            started=time.monotonic()
            with patch.dict(os.environ, {'MONITOR_V18_FLOW_TRACE': directory}):
                threads=[threading.Thread(target=lambda i=i:record('batch', i)) for i in range(20)]
                for thread in threads:thread.start()
                for thread in threads:thread.join()
            files=list(Path(directory).glob('*.jsonl'))
            self.assertEqual(len(files),1)
            records=[json.loads(line) for line in files[0].read_text().splitlines()]
            self.assertEqual({row['batch_id'] for row in records},set(range(20)))
            for row in records:
                self.assertEqual(row['pid'],os.getpid())
                self.assertGreaterEqual(row['monotonic'],started)
                self.assertIsInstance(row['thread_id'],int)
