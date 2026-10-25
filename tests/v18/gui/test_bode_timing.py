"""V18 GUI parity regressions adapted from the corresponding V17 suite."""
import unittest
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

from monitor.v18.bode import BodeSweep, tone_transfer
from monitor.v18.bode_timing import channel_delay_us, pair_delay_us, correct_phase
from monitor.v18.receiver.unoq_acquisition import Configuration



class BodeTimingTests(unittest.TestCase):
    def test_bode_buttons_start_all_methods_with_filter_off(self):
        from PyQt6 import QtWidgets
        from unittest.mock import MagicMock
        from monitor.v18.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window.serial_worker=MagicMock();window.is_running=True
            window._pulse_us_capable=True;window._auto_apply_timer.stop()
            self.assertEqual(window.filter_config.source,'OFF')
            window.spectral.set_mode(3)
            for index,panel in enumerate(window.spectral.bode.panels):
                with self.subTest(method=index):
                    window.spectral.select_bode(index)
                    window._generator_requested=None;window._generator_state_known=True
                    window.serial_worker.request_generator.reset_mock()
                    panel.button.click()
                    self.assertTrue(panel.active,panel.status.text())
                    window.serial_worker.request_generator.assert_called()
                    self.assertGreater(panel.result_delay_us,0)
                    panel.cancel()
                    window._generator_requested=None
                    panel.response_channel.setCurrentText('FILTER')
                    window.serial_worker.request_generator.reset_mock()
                    panel.button.click()
                    self.assertFalse(panel.active)
                    self.assertIn('fuente del filtro',panel.status.text())
                    window.serial_worker.request_generator.assert_not_called()
                    self.assertIn('fuente del filtro',window.analysis_status_box.toolTip())
        finally:
            for panel in window.spectral.bode.panels:
                if panel.active:panel.cancel()
            window.serial_worker=None;window.close()


    def test_gui_toggle_preserves_raw_and_history_profiles(self):
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices', return_value=[]):
            window = SerialMonitorWindow()
        try:
            for panel in window.spectral.bode.panels:
                self.assertTrue(panel.correction.isChecked())
                panel.result_profile = Configuration(16, 40000)
                panel.result_delay_us = channel_delay_us(panel.result_profile)
                phase = 360*1000*panel.result_delay_us/1e6
                panel.result = [(1000, 0, phase)]
                panel.history = [[(1000, 0, 360*1000*6.5185185185/1e6)]]
                panel.history_profiles = [Configuration(16, 76226)]
                panel.history_delays = [6.5185185185]
                panel.draw()
                self.assertAlmostEqual(panel.curve_sets[1][1].getData()[1][0], 0)
                self.assertAlmostEqual(panel.curve_sets[0][1].getData()[1][0], 0)
                panel.correction.setChecked(False)
                self.assertAlmostEqual(panel.curve_sets[1][1].getData()[1][0], phase)
                panel.correction.setChecked(True)
                self.assertEqual(panel.result[0][2], phase)
        finally:
            window.close()


