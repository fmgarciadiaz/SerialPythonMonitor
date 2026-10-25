import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v17.app import SerialMonitorWindow
from monitor.v17.receiver.unoq_acquisition import Configuration
from diagnosticos.wav_cases_v17 import STABILITY_MATRIX,select_window_configuration


class WavDiagnosticUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_hidden_legacy_rate_is_selected_with_valid_data_in_every_case(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            initial=window.config_rate_combo.count()
            self.assertEqual(window.config_rate_combo.findData(100000),-1)
            for bits,rate,_ in STABILITY_MATRIX:
                expected=Configuration(bits,rate)
                select_window_configuration(window,expected)
                self.app.processEvents()
                actual=Configuration(window.config_bits_combo.currentData(),window.config_rate_combo.currentData())
                self.assertEqual(actual,expected)
                self.assertFalse(window._auto_apply_timer.isActive())
            self.assertEqual(window.config_rate_combo.count(),initial+1)
        finally:
            window.close()
