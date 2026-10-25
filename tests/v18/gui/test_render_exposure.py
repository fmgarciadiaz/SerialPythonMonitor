import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from monitor.v18.app import SerialMonitorWindow


class RenderExposureTests(unittest.TestCase):
    def test_ready_gui_backlog_drains_before_paint_without_delaying_single(self):
        for ready,single in ((0,False),(1,False),(2,False),(5,False),(5,True)):
            with self.subTest(ready=ready,single=single):
                window=SimpleNamespace(windowHandle=lambda:SimpleNamespace(isExposed=lambda:True),
                    single_shot_armed=single,serial_worker=SimpleNamespace(ready_gui_batches=lambda:ready),
                    radio_output_panel=SimpleNamespace(refresh_meter=Mock()),render_frame=Mock(),
                    spectral=SimpleNamespace(render=Mock()),_note_gui_callback=Mock())
                SerialMonitorWindow._render_with_diagnostics(window)
                if ready<2 or single:window.render_frame.assert_called_once()
                else:window.render_frame.assert_not_called()
    def test_hidden_window_skips_only_paint_work_and_preserves_single_capture(self):
        for exposed,single in ((False,False),(False,True),(True,False)):
            with self.subTest(exposed=exposed,single=single):
                window=SimpleNamespace(windowHandle=lambda:SimpleNamespace(isExposed=lambda:exposed),
                    single_shot_armed=single,radio_output_panel=SimpleNamespace(refresh_meter=Mock()),
                    render_frame=Mock(),spectral=SimpleNamespace(render=Mock()),_note_gui_callback=Mock())
                SerialMonitorWindow._render_with_diagnostics(window)
                if exposed or single:
                    window.render_frame.assert_called_once();window.spectral.render.assert_called_once()
                else:
                    window.render_frame.assert_not_called();window.spectral.render.assert_not_called()
                    window.radio_output_panel.refresh_meter.assert_not_called()
