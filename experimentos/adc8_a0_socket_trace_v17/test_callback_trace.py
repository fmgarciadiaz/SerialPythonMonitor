from types import SimpleNamespace
import unittest
from .gc_trace import GcTrace
from .gui_trace import GuiTrace


class CallbackTraceTests(unittest.TestCase):
    def test_gui_gate_nested_owner_and_exception(self):
        trace = GuiTrace()
        window = SimpleNamespace(is_running=True, _wav_active=False)
        display = SimpleNamespace(owner=window)
        self.assertEqual(trace.call('render', lambda owner: 7, display), 7)
        self.assertEqual(trace.stages, {})
        window._wav_active = True
        def fail(owner):
            raise ValueError('original')
        with self.assertRaisesRegex(ValueError,'original'):
            trace.call('render', fail, display)
        self.assertEqual(trace.stages['render']['count'],1)
        self.assertIs(trace.window,window)

    def test_gc_missing_start_and_bounded_top(self):
        trace = GcTrace(lambda: True)
        trace.callback('stop',dict(generation=0))
        for _ in range(20):
            trace.callback('start',dict(generation=2))
            trace.callback('stop',dict(generation=2,collected=4,uncollectable=0))
        self.assertEqual(trace.count,20)
        self.assertEqual(len(trace.top),8)
        self.assertTrue(all(x['active_a0'] for x in trace.top))
        self.assertEqual(trace.starts,{})
