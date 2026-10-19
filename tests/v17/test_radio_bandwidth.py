import unittest
from unittest.mock import patch
import numpy as np
from monitor.v17.radio_am import AMDemodulator,RadioConfig


class RadioBandwidthTests(unittest.TestCase):
    def test_narrow_channel_rejects_outer_sidebands(self):
        rate=200000
        t=np.arange(int(rate*.3))/rate
        rf=(1+.3*np.sin(2*np.pi*3000*t))*np.cos(2*np.pi*50000*t)
        levels=[]
        for width in (4000,9000):
            demod=AMDemodulator(RadioConfig(rate,50000,width))
            audio=demod.process(rf)
            levels.append(np.std(audio[len(audio)//2:]))
        self.assertLess(levels[0],levels[1]*.15)

    def test_wide_channel_preserves_audio_above_four_khz(self):
        rate=200000
        t=np.arange(int(rate*.3))/rate
        rf=(1+.3*np.sin(2*np.pi*6000*t))*np.cos(2*np.pi*50000*t)
        levels=[]
        for width in (10000,20000):
            demod=AMDemodulator(RadioConfig(rate,50000,width))
            audio=demod.process(rf)
            levels.append(np.std(audio[len(audio)//2:]))
        self.assertGreater(levels[1],levels[0]*3)

    def test_ui_default_and_settings_generation(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            self.assertEqual(w._processing_settings().radio_bandwidth,8000)
            self.assertEqual([w.radio_bandwidth.itemData(i) for i in range(w.radio_bandwidth.count())],[6000,8000,10000,12000,20000])
            before=w._processing_generation
            w.radio_bandwidth.setCurrentIndex(w.radio_bandwidth.findData(12000))
            self.assertEqual(w._processing_settings().radio_bandwidth,12000)
            self.assertGreater(w._processing_generation,before)
        finally:w.close();app.processEvents()
