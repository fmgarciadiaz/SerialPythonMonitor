from contextlib import nullcontext
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.gui_reader_stages_v19 import TRACE_ENV,capture_stage_connection
from monitor.v19.receiver import unoq_config_receiver as core


class ReaderStageCaptureTests(unittest.TestCase):
    def test_discovers_tracker_created_before_connection(self):
        tracker=core._ChildStageTiming()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stages.json'
            with patch.dict(os.environ,{TRACE_ENV:str(path)}), \
                 patch.object(core,'_child_stage_timing_enabled',True), \
                 patch('tools.relay_wire_metrics_v19.accepted_metrics_connection',return_value=nullcontext(object())):
                with capture_stage_connection('test'):
                    tracker._observe('tick',10,10.001,.0002)
            report=json.loads(path.read_text())
            self.assertEqual(len(report['trackers']),1)
            self.assertIn('tick',report['trackers'][0]['snapshot']['max_ms'])

    def test_slow_stage_survives_exception_and_methods_restore(self):
        cls=core._ChildStageTiming;initialize=cls.__init__;observe=cls._observe
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stages.json'
            with patch.dict(os.environ,{TRACE_ENV:str(path)}), \
                 patch.object(core,'_child_stage_timing_enabled',True), \
                 patch('tools.relay_wire_metrics_v19.accepted_metrics_connection',return_value=nullcontext(object())):
                with self.assertRaisesRegex(RuntimeError,'screen'):
                    with capture_stage_connection('test'):
                        tracker=cls();tracker._observe('read',10,10.25,.002)
                        raise RuntimeError('screen')
            report=json.loads(path.read_text())
            self.assertEqual(report['slow'][0]['wall_ms'],250)
            self.assertEqual(report['slow'][0]['cpu_ms'],2)
            self.assertEqual(len(report['trackers']),1)
        self.assertIs(cls.__init__,initialize);self.assertIs(cls._observe,observe)
