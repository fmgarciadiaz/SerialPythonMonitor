import unittest
from unittest.mock import patch
import numpy as np
from monitor.v17.radio_tuning import alias_frequency,tuning_bounds
from monitor.v17.radio_am import AMDemodulator,RadioConfig

class UndersamplingTests(unittest.TestCase):
    def test_bounds_and_alias(self):
        self.assertEqual(tuning_bounds(1600000,10000,True),(5001,1594999))
        self.assertEqual(alias_frequency(1600000,1000000,10000,True),600000)
        for f in (800000,805000,1595000,1600000):
            with self.assertRaises(ValueError):alias_frequency(1600000,f,10000,True)
        for width in (10000,12000,20000):
            with self.assertRaises(ValueError):alias_frequency(1600000,width/2,width)

    def test_am_alias_equivalence(self):
        rate=1600000;t=np.arange(320000)/rate
        envelope=1+.3*np.cos(2*np.pi*1300*t)
        a=AMDemodulator(RadioConfig(rate,600000)).process(envelope*np.cos(2*np.pi*600000*t))
        b=AMDemodulator(RadioConfig(rate,alias_frequency(rate,1000000,10000,True))).process(envelope*np.cos(2*np.pi*1000000*t))
        np.testing.assert_allclose(a,b,atol=1e-10)

    def test_ui_us_limits_processing_and_overlay(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            w.radio_us.setChecked(True)
            self.assertEqual(w.radio_frequency_dial.minimum(),5000)
            self.assertEqual(w.radio_frequency_dial.maximum(),1595999)
            w.radio_frequency.setValue(1000)
            self.assertTrue(w._processing_settings().radio_undersampling)
            w.spectral.set_mode(4)
            self.assertEqual(w.spectral.radio_overlay_items[-1][1].value(),600000)
            w.radio_us.setChecked(False)
            self.assertEqual(w.radio_frequency_dial.maximum(),795999)
        finally:w.close();app.processEvents()
