import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PyQt5 import QtWidgets
from monitor.v10.app import SerialMonitorWindow

class ConfigurationUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v10.app.usb_devices',return_value=['test-q']): self.window=SerialMonitorWindow()
    def tearDown(self):self.window.close()
    def test_selectors_are_visible_on_main_screen(self):
        w=self.window;w.show();self.app.processEvents()
        self.assertTrue(w.configuration_panel.isVisible())
        for combo in (w.port_combo,w.destination_combo,w.config_bits_combo,w.config_rate_combo):
            self.assertTrue(combo.isVisible())
        self.assertFalse(hasattr(w,'configuration_toggle'))
        self.assertFalse(w.r4_combo.isVisible())
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(1))
        self.assertTrue(w.r4_combo.isVisible())
    def test_applied_settings_update_read_only_summary_and_clear_stop_trace(self):
        w=self.window;w.is_running=False
        w._update_curve_items(['V_IN']);w.line_items['V_IN'].setData([0,1],[2,3])
        w._acquisition_confirmed(8,10000);w._output_confirmed(0,'')
        self.assertEqual(w.adc_max,255)
        self.assertIn('8 bits',w.confirmed_output_label.text());self.assertIn('10 kHz',w.confirmed_output_label.text())
        x,y=w.line_items['V_IN'].getData();self.assertTrue(x is None or len(x)==0)
        self.assertFalse(w.is_running)

    def test_uart_disables_spi_rates_and_selects_safe_rate(self):
        w=self.window
        w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(62500))
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(1))
        self.assertEqual(w.config_rate_combo.currentData(),31250)
        for rate in (40000,50000,62500):
            self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(rate)).isEnabled())
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(0))
        self.assertTrue(w.config_rate_combo.model().item(w.config_rate_combo.findData(62500)).isEnabled())

    def test_rate_selection_applies_automatically(self):
        from unittest.mock import MagicMock
        from PyQt5 import QtTest
        from transport.unoq_acquisition import Configuration
        w=self.window;worker=MagicMock();w.serial_worker=worker
        w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(62500))
        QtTest.QTest.qWait(80)
        worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(14,62500))
        self.assertTrue(w.output_pending)
        self.assertFalse(hasattr(w,'apply_output_button'))
    def test_uart_waits_for_r4_then_applies_safe_rate(self):
        from unittest.mock import MagicMock
        from PyQt5 import QtTest
        from transport.unoq_acquisition import Configuration
        w=self.window;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(62500))
        worker=MagicMock();w.serial_worker=worker
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(1))
        QtTest.QTest.qWait(80);worker.request_output.assert_not_called()
        w.r4_combo.addItem('Test R4','r4');w.r4_combo.setCurrentIndex(w.r4_combo.findData('r4'))
        QtTest.QTest.qWait(80)
        worker.request_output.assert_called_once_with(1,'r4',Configuration())

    def test_oversampling_caps_rate_and_restores_native_rates(self):
        w=self.window
        w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(62500))
        w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(16))
        self.assertEqual(w.config_rate_combo.currentData(),50000)
        self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(62500)).isEnabled())
        w._acquisition_confirmed(16,12500)
        self.assertEqual(w.adc_max,65535)
        w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(14))
        self.assertTrue(w.config_rate_combo.model().item(w.config_rate_combo.findData(62500)).isEnabled())

    def test_fast_oversampling_selection_applies_one_safe_profile(self):
        from unittest.mock import MagicMock
        from PyQt5 import QtTest
        from transport.unoq_acquisition import Configuration
        w=self.window
        w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(62500))
        w.serial_worker=MagicMock()
        w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(16))
        QtTest.QTest.qWait(80)
        w.serial_worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(16,50000))
        self.assertIn('Adq 0,125 µs',w.config_rate_combo.currentText())

    def test_finished_receiver_can_be_stopped_without_deleted_thread_error(self):
        from PyQt5 import QtCore, QtTest
        class FinishedWorker(QtCore.QObject):
            batch_ready=QtCore.pyqtSignal(object)
            headers_detected=QtCore.pyqtSignal(object)
            status_changed=QtCore.pyqtSignal(str)
            output_confirmed=QtCore.pyqtSignal(int,str)
            acquisition_confirmed=QtCore.pyqtSignal(int,int)
            generator_confirmed=QtCore.pyqtSignal(object)
            switching=QtCore.pyqtSignal(bool)
            error_occurred=QtCore.pyqtSignal(str)
            finished=QtCore.pyqtSignal()
            def __init__(self,*args):super().__init__()
            def run(self):self.finished.emit()
            def stop(self):pass
        w=self.window
        with patch('monitor.v10.app.OutputWorker',FinishedWorker):
            w.connect_serial()
            QtTest.QTest.qWait(100)
            self.assertFalse(w.serial_thread.isRunning())
            w.stop_input()
            self.assertIsNone(w.serial_thread)
            self.assertIsNone(w.serial_worker)
            w.stop_input()
