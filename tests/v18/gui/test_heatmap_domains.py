import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.radio_stream import RadioTimeline
from monitor.v18.receiver.unoq_acquisition import Configuration

class HeatmapDomainsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v18.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.applied_configuration=Configuration(12,40000)
        self.w.current_fs_hz=40000;self.w.is_running=True
        n=8192;t=np.arange(n)/40000
        for name,values in {'CH1':np.sin(2*np.pi*1250*t),'CH2':np.sin(2*np.pi*2500*t),'Tiempo (us)':t*1e6}.items():self.w.series[name].extend(values)
        self.w.sample_numbers.extend(np.arange(n));self.w.sample_counter=n
        self.s=self.w.spectral;self.s.size.setCurrentText('256');self.s.set_mode(2)
    def tearDown(self):self.w.close()
    def draw(self,a,b):
        self.s.channels[0].setCurrentText(a);self.s.channels[1].setCurrentText(b)
        self.s.last_fast_render=0;self.s.render()
        for i in range(2):
            image=self.s.images[i].image
            self.assertIsNotNone(image)
            self.assertTrue(np.isfinite(image[:,-1]).all())
        return [np.argmax(self.s.images[i].image[:,-1]) for i in range(2)]
    def test_dual_adc_draws_both_tones(self):self.assertEqual(self.draw('CH1','CH2'),[8,16])
    def test_rf_and_audio_use_independent_nyquist_and_history(self):
        self.w.radio_stream=RadioTimeline(48000)
        t=np.arange(4096)/48000;self.w.radio_stream.append(np.sin(2*np.pi*1500*t),None)
        self.assertEqual(self.draw('CH1','RADIO'),[8,8])
        self.assertAlmostEqual(self.s._heatmap_states[0]['context'][3],40000)
        self.assertAlmostEqual(self.s._heatmap_states[1]['context'][3],48000)
    def test_switch_to_none_clears_old_image(self):
        self.draw('CH1','CH2');self.s.channels[1].setCurrentText('Ninguno')
        self.s.last_fast_render=0;self.s.render();self.assertIsNone(self.s.images[1].image)

class Radio48PlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_play_requests_supported_dac_rate_and_keeps_48k_radio(self):
        from unittest.mock import MagicMock
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            w.radio_frequency.setValue(400)
            w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(48000))
            w._auto_apply_timer.stop();w.serial_worker=MagicMock();w._wav_capable=True
            w.wav_rate.model().item(w.wav_rate.findData(40000)).setEnabled(True)
            w.radio_output_panel.toggle()
            source=w.radio_output_panel.source
            self.assertIsNotNone(source,w.radio_output_panel.state.text())
            self.assertEqual((source.input_rate,source.rate),(48000,40000))
            self.assertEqual(w.radio_output_rate.currentData(),48000)
            self.assertEqual(w.serial_worker.request_wav.call_args.args,(1,source,40000))
        finally:w.serial_worker=None;w.close()
