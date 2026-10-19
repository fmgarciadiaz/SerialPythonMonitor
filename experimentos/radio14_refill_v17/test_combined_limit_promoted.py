import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
import numpy as np
from monitor.v17.radio_output import acquisition_error,RadioDacSource
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_acquisition import Configuration


class CombinedLimitTests(unittest.TestCase):
    def test_exact_scope_and_source_fail_closed(self):
        for bits,rate in ((8,1600000),(10,1250000),(12,1066666),(14,599250)):
            self.assertIsNone(acquisition_error(Configuration(bits,rate)))
        source=RadioDacSource(buffer_seconds=0)
        settings=ProcessingSettings(acquisition=SimpleNamespace(bits=14,rate=851064))
        source.feed_result(dict(settings=settings,audio=np.ones(480),radio_key=(851063,20000,40000)))
        self.assertIn('851,063',source.error)
        self.assertIsNone(source.try_codes(0,480))

    def test_target_rate_play_and_upper_bound(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(14,851063);w.generator_mode.setCurrentIndex(7)
            worker=Mock();w.serial_worker=worker;w._wav_capable=True;w.output_pending=False
            w.wav_rate.model().item(w.wav_rate.findData(40000)).setEnabled(True)
            before=w.applied_configuration;w.radio_output_panel.toggle()
            self.assertIsNotNone(w.radio_output_panel.source,w.radio_output_panel.state.text())
            self.assertEqual(w.applied_configuration,before)
            worker.request_output.assert_not_called()
            self.assertTrue(w.radio_enabled.isChecked())
            w.applied_configuration=SimpleNamespace(bits=14,rate=851064)
            w.radio_output_panel.radio_changed()
            self.assertIsNone(w.radio_output_panel.source)
            self.assertTrue(w.radio_enabled.isChecked())
            worker.request_wav.assert_called_with(3)
            self.assertIn('851,063',w.radio_output_panel.state.text())
            w.applied_configuration=before
        finally:
            w.serial_worker=None;w._wav_active=False;w.close();app.processEvents()
