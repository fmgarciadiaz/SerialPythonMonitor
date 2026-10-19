import unittest
from unittest.mock import patch,Mock
from PyQt6 import QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.receiver.unoq_acquisition import Configuration

class SynthAdcLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v16.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
    def tearDown(self):self.w.close()
    def test_enter_caps_and_leave_restores_previous_rate(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(363636))
        w.generator_mode.setCurrentIndex(5)
        self.assertEqual(w.config_rate_combo.currentData(),40000)
        for i in range(w.config_rate_combo.count()):
            if w.config_rate_combo.itemData(i)>40000:self.assertFalse(w.config_rate_combo.model().item(i).isEnabled())
        w.generator_mode.setCurrentIndex(0)
        self.assertEqual(w.config_rate_combo.currentData(),363636)
        self.assertTrue(w.config_rate_combo.model().item(w.config_rate_combo.findData(363636)).isEnabled())
    def test_lower_rate_is_preserved(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(20000))
        w.generator_mode.setCurrentIndex(5)
        self.assertEqual(w.config_rate_combo.currentData(),20000)
        w.generator_mode.setCurrentIndex(0)
        self.assertEqual(w.config_rate_combo.currentData(),20000)
    def test_play_waits_for_actual_acquisition_confirmation(self):
        w=self.w;w.generator_mode.setCurrentIndex(5)
        w.serial_worker=Mock();w._wav_capable=True
        w.applied_configuration=Configuration(14,100000)
        w.fm_panel.toggle();w.serial_worker.request_wav.assert_not_called()
        w.applied_configuration=Configuration(14,40000);w.output_pending=True
        w.fm_panel.toggle();w.serial_worker.request_wav.assert_not_called()
        w.serial_worker=None

if __name__=='__main__':unittest.main()
