import unittest
from unittest.mock import patch
import numpy as np
from monitor.v17.radio_am import radio_tuning_max


class FsLimitTests(unittest.TestCase):
    def test_maximum_tracks_clock_and_channel_width(self):
        self.assertEqual(radio_tuning_max(1600000),795999)
        self.assertEqual(radio_tuning_max(1600000,6000),796999)
        for fs in (40000,76226.77465,1250000,1600000):
            maximum=radio_tuning_max(fs)
            self.assertLess(maximum+4000,fs/2)
            self.assertGreaterEqual(maximum+1+4000,fs/2)

    def test_dial_scan_and_demod_above_old_six_hundred_limit(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        from monitor.v17.radio_scan import scan_carriers,SCAN_SIZE,SCAN_BLOCKS
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            self.assertEqual(w.radio_frequency_dial.maximum(),795999)
            w.radio_frequency.setValue(750)
            self.assertEqual(w.radio_frequency_dial.value(),750000)
            w.radio_bandwidth.setCurrentIndex(w.radio_bandwidth.findData(6000))
            self.assertEqual(w.radio_frequency_dial.maximum(),796999)
            w._acquisition_confirmed(10,1250000)
            self.assertEqual(w.radio_frequency_dial.maximum(),621999)
            self.assertLessEqual(w.radio_frequency.value()*1000,621999)
        finally:w.close();app.processEvents()
        t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/1600000
        peaks=scan_carriers(np.cos(2*np.pi*750000*t),1600000)
        self.assertTrue(any(abs(p['frequency']-750000)<30 for p in peaks))
        from monitor.v17.radio_am import AMDemodulator,RadioConfig
        demod=AMDemodulator(RadioConfig(1600000,750000))
        audio=demod.process((1+.4*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*750000*t))
        audio=audio[len(audio)//2:]
        frequencies=np.fft.rfftfreq(len(audio),1/demod.output_rate)
        self.assertLess(abs(frequencies[np.argmax(abs(np.fft.rfft(audio)))]-1000),30)
