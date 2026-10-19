import unittest
from types import SimpleNamespace
import numpy as np
from unittest.mock import Mock,patch
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.radio_loop_guard import RadioLoopGuard


class RadioRatesTests(unittest.TestCase):
    def test_panel_requests_twenty_k_and_stops_when_rate_changes(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            w.generator_mode.setCurrentIndex(7)
            w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(20000))
            worker=Mock();w.serial_worker=worker;w._wav_capable=True;w.output_pending=False
            w.radio_output_panel.toggle()
            source=w.radio_output_panel.source
            self.assertIsNotNone(source,w.radio_output_panel.state.text())
            worker.request_wav.assert_called_with(1,source,20000)
            self.assertEqual(source.rate,20000)
            w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(40000))
            self.assertIsNone(w.radio_output_panel.source)
            worker.request_wav.assert_called_with(3)
        finally:
            w.serial_worker=None;w._wav_active=False;w.close();app.processEvents()

    def test_twenty_k_audio_and_duration_reserves(self):
        source=RadioDacSource(volume=1,rate=20000)
        self.assertEqual(source.prebuffer_samples,10000)
        self.assertEqual(source.chunk_interval,.012)
        source.feed_result(dict(settings=SimpleNamespace(radio_offset=1.65),
                                audio=np.full(10000,1.8),radio_key=(1600000,550000,20000)))
        codes=source.try_codes(0,480)
        self.assertEqual(len(codes),480)
        np.testing.assert_array_equal(codes,np.full(480,round(1.8*4095/3.3)))
        self.assertIsNone(source.error)

    def test_loop_guard_twenty_k_packet_boundaries_and_detection(self):
        rng=np.random.default_rng(8)
        codes=np.repeat(rng.integers(600,3400,6000),5).astype('<u2')
        guard=RadioLoopGuard(20000)
        for start in range(0,len(codes),479):guard.sent(codes[start:start+479],start)
        expected=codes[::5].astype(float)*3.3/4095
        np.testing.assert_allclose(guard.output,expected)
        for index in range(3):
            self.assertEqual(guard.observe(expected[1000+index*512:1512+index*512],4000),index==2)

    def test_unsupported_and_mismatched_rate_fail_explicitly(self):
        with self.assertRaises(ValueError):RadioDacSource(rate=48000)
        source=RadioDacSource(rate=20000)
        source.feed_result(dict(settings=SimpleNamespace(radio_offset=1.65),
                                audio=np.ones(480),radio_key=(1600000,550000,40000)))
        self.assertIn('20 kHz',source.error)
        self.assertIsNone(source.try_codes(0,480))
