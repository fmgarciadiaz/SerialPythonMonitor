import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch,MagicMock
from PyQt5 import QtWidgets,QtTest
from monitor.v11.app import SerialMonitorWindow
from experimentos.tasas_spi.receiver.unoq_acquisition import Configuration

class FastMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v11.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
    def tearDown(self):self.w.serial_worker=None;self.w.close()
    def test_only_measured_rates_are_offered_and_auto_applied(self):
        w=self.w;combo=w.config_rate_combo
        self.assertGreaterEqual(combo.findData(100000),0)
        for rate in (125000,200000,250000):self.assertEqual(combo.findData(rate),-1)
        w.serial_worker=MagicMock();combo.setCurrentIndex(combo.findData(100000));QtTest.QTest.qWait(80)
        w.serial_worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(14,100000))
    def test_high_rate_to_oversampling_is_one_safe_profile(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(100000))
        w.serial_worker=MagicMock();w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(16));QtTest.QTest.qWait(80)
        w.serial_worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(16,50000))
        self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(100000)).isEnabled())
    def test_uart_retains_safe_ceiling(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(100000))
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(1))
        self.assertEqual(w.config_rate_combo.currentData(),31250)
        self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(100000)).isEnabled())
    def test_fast_spectral_refresh_keeps_samples_and_heatmap_hops(self):
        import numpy as np
        w=self.w;display=w.spectral;display.set_mode(2);w.current_fs_hz=100000
        def append(start,count):
            indices=np.arange(start,start+count)
            w.sample_numbers.extend(indices)
            for name,history in w.series.items():
                history.extend(indices*10 if name=='Tiempo (us)' else np.sin(indices/20))
            w.sample_counter+=count
        append(0,12000)
        with patch('monitor.v11.spectrum.time.monotonic',return_value=10):display.render()
        first=display.last_end;append(12000,10000)
        with patch('monitor.v11.spectrum.time.monotonic',return_value=10.02):display.render()
        self.assertEqual(display.last_end,first)
        with patch('monitor.v11.spectrum.time.monotonic',return_value=10.06):display.render()
        self.assertGreater(display.last_end,first)
        self.assertGreaterEqual(len(display.frames),3)
        self.assertEqual(w.sample_counter,22000)
        self.assertEqual(len(w.series['V_IN']),22000)
