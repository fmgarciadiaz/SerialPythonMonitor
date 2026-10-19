import unittest
from unittest.mock import patch,Mock
from PyQt6 import QtWidgets

class ScanA0Tests(unittest.TestCase):
    def test_waits_stop_then_scan_and_resumes_same_output(self):
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.generator_mode.setCurrentIndex(7);w.radio_enabled.setChecked(True)
            w.serial_worker=Mock();w._wav_active=True
            panel=w.radio_output_panel;panel.volume.setValue(37)
            panel.stop=Mock();panel.toggle=Mock()
            w._radio_scan=Mock();w._radio_scan_future=Mock()
            w._pause_a0_for_radio_scan()
            panel.stop.assert_called_once()
            w._wait_a0_for_radio_scan();w._radio_scan.assert_not_called()
            w._wav_active=False;w.output_pending=False
            w._wait_a0_for_radio_scan();w._radio_scan.assert_called_once()
            self.assertFalse(panel.isEnabled())
            w._finish_radio_scan_a0(True)
            panel.toggle.assert_called_once()
            self.assertEqual(panel.volume.value(),37)
            self.assertTrue(panel.isEnabled())
        finally:
            w._radio_scan_future=None;w.serial_worker=None;w.close();app.processEvents()

    def test_failed_scan_does_not_restart_output(self):
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.serial_worker=Mock();p=w.radio_output_panel;p.stop=Mock();p.toggle=Mock()
            w._pause_a0_for_radio_scan();w._finish_radio_scan_a0(False)
            p.toggle.assert_not_called();self.assertTrue(p.isEnabled())
        finally:w.serial_worker=None;w.close();app.processEvents()

    def test_stop_waits_until_dac_played_fade(self):
        from types import SimpleNamespace
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.serial_worker=Mock();w._wav_active=True
            panel=w.radio_output_panel
            source=SimpleNamespace(fade_out=Mock(return_value=1760),played=1440,error=None)
            panel.source=source;panel.stop=Mock()
            w._pause_a0_for_radio_scan()
            panel.stop.assert_not_called()
            w._wait_a0_for_radio_scan();panel.stop.assert_not_called()
            source.played=1920
            w._wait_a0_for_radio_scan();panel.stop.assert_called_once()
        finally:
            w._finish_radio_scan_a0(False);panel.source=None;w.serial_worker=None;w.close();app.processEvents()

    def test_failed_pending_fade_stops_instead_of_leaving_silent_source(self):
        from types import SimpleNamespace
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.serial_worker=Mock();panel=w.radio_output_panel
            panel.source=SimpleNamespace(fade_out=Mock(return_value=2000),played=0,error=None)
            panel.stop=Mock();panel.toggle=Mock()
            w._pause_a0_for_radio_scan();w._finish_radio_scan_a0(False)
            panel.stop.assert_called_once();panel.toggle.assert_not_called()
        finally:
            panel.source=None;w.serial_worker=None;w.close();app.processEvents()
