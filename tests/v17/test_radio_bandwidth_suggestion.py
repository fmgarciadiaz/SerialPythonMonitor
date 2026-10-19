import unittest
from unittest.mock import patch
import numpy as np
from monitor.v17.radio_scan import scan_carriers, SCAN_SIZE, SCAN_BLOCKS


class BandSuggestionTests(unittest.TestCase):
    def scan(self, tone, neighbor=False):
        rate=200000
        t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/rate
        signal=np.cos(2*np.pi*50000*t)
        if tone:signal*=1+.4*np.cos(2*np.pi*tone*t)
        if neighbor:signal+=np.cos(2*np.pi*60000*t)
        signal+=np.random.default_rng(12).normal(0,.002,len(t))
        peaks=scan_carriers(signal,rate)
        return next(p for p in peaks if abs(p['frequency']-50000)<10)

    def test_modulation_silence_and_neighbor(self):
        self.assertEqual(self.scan(3500)['suggested_bandwidth'],8000)
        self.assertEqual(self.scan(5500)['suggested_bandwidth'],12000)
        self.assertIsNone(self.scan(None)['suggested_bandwidth'])
        # A neighboring carrier prevents a broad-band recommendation.
        self.assertIsNone(self.scan(5500,True)['suggested_bandwidth'])

    def test_suggestion_requires_selection_and_expires_on_retune(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            w.radio_frequency.setValue(550)
            w.radio_candidates=[dict(frequency=550000,suggested_bandwidth=12000)]
            w._update_radio_bandwidth_suggestion()
            self.assertEqual(w.radio_bandwidth.count(),6)
            self.assertEqual(w._processing_settings().radio_bandwidth,8000)
            w.radio_bandwidth.setCurrentIndex(5)
            self.assertEqual(w._processing_settings().radio_bandwidth,12000)
            w.radio_frequency.setValue(600)
            self.assertEqual(w.radio_bandwidth.count(),5)
            self.assertEqual(w._processing_settings().radio_bandwidth,12000)
        finally:w.close();app.processEvents()
