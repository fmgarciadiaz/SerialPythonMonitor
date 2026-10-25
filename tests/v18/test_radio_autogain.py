import unittest
from unittest.mock import patch
import numpy as np
from monitor.v18.radio_autogain import target_gain


class AutoGainTests(unittest.TestCase):
    def test_normal_increase_and_decrease_are_small(self):
        raised=target_gain([1.64,1.66],10,1.65,elapsed=.1)
        lowered=target_gain([.35,2.95],10,1.65,elapsed=.1)
        self.assertEqual(raised,10.1)
        self.assertEqual(lowered,9.8)
        self.assertGreater(lowered,1.15/1.3*10)
        self.assertIsNone(target_gain([.35,2.95],10,1.65,allow_normal=False))

    def test_severe_clipping_bypasses_cadence_and_attacks_immediately(self):
        audio=np.array([-.35,3.65])
        value=target_gain(audio,10,1.65,elapsed=.001,allow_normal=False)
        self.assertEqual(value,5.7)
        corrected=(audio-1.65)*value/10+1.65
        self.assertGreaterEqual(float(corrected.min()),.5)
        self.assertLessEqual(float(corrected.max()),2.8)

    def test_silence_invalid_input_deadband_limits_and_long_pause(self):
        self.assertIsNone(target_gain([1.65]*20,2,1.65))
        self.assertIsNone(target_gain([np.nan],2,1.65))
        self.assertIsNone(target_gain([1.6,1.7],np.nan,1.65))
        self.assertIsNone(target_gain([.1,.2],2,0))
        self.assertIsNone(target_gain([1.49,1.81],80,1.65))
        self.assertIsNone(target_gain([.5,2.8],10,1.65))
        self.assertEqual(target_gain([1.64,1.66],10,1.65,elapsed=50),
                         target_gain([1.64,1.66],10,1.65,elapsed=.5))


class GuiAutoGainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6 import QtWidgets
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_substeps_accumulate_emergency_bypasses_timer_and_manual_still_wins(self):
        from monitor.v18.app import SerialMonitorWindow
        with patch('monitor.v18.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window.radio_gain.setValue(2)
            window.radio_enabled.setChecked(True);window.radio_auto_gain.setChecked(True)
            def result(amplitude=.01):
                settings=window._processing_settings()
                return dict(settings=settings,generation=settings.generation,
                            audio=np.array([1.65-amplitude,1.65+amplitude]))
            for i in range(11):window._update_radio_auto_gain(result(),100+i*.1)
            self.assertGreater(window.radio_gain.value(),2)
            self.assertLess(window.radio_gain.value(),2.6)
            self.assertTrue(window.radio_auto_gain.isChecked())
            gain=window.radio_gain.value()
            stale=result(2.);stale['generation']-=1
            window._update_radio_auto_gain(stale,101.01)
            self.assertEqual(window.radio_gain.value(),gain)
            window._update_radio_auto_gain(result(2.),101.02)
            self.assertLess(window.radio_gain.value(),gain*.7)
            self.assertTrue(window.radio_auto_gain.isChecked())
            window.radio_gain_dial.setValue(120)
            self.assertEqual(window.radio_gain.value(),12)
            self.assertFalse(window.radio_auto_gain.isChecked())
        finally:window.close();self.app.processEvents()
