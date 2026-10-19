import unittest
from unittest.mock import patch
import numpy as np
from monitor.v17.radio_autogain import target_gain


class AutoGainTests(unittest.TestCase):
    def test_headroom_silence_finite_and_limits(self):
        self.assertEqual(target_gain([.65,2.65],10,1.65),11.5)
        self.assertEqual(target_gain([-.35,3.65],10,1.65),5.7)
        self.assertIsNone(target_gain([1.65]*20,2,1.65))
        self.assertIsNone(target_gain([np.nan],2,1.65))
        self.assertIsNone(target_gain([.1,.2],2,0))
        self.assertEqual(target_gain([1.64,1.66],2,1.65),3.)

    def test_auto_gain_reaches_eighty_and_stops(self):
        self.assertEqual(target_gain([1.57,1.73],40,1.65),60.)
        self.assertEqual(target_gain([1.53,1.77],60,1.65),80.)
        self.assertIsNone(target_gain([1.49,1.81],80,1.65))

    def test_gui_throttle_manual_override_and_generation(self):
        from PyQt6 import QtWidgets
        from monitor.v17.app import SerialMonitorWindow
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.radio_enabled.setChecked(True);w.radio_auto_gain.setChecked(True)
            def result():
                settings=w._processing_settings()
                return dict(settings=settings,generation=settings.generation,audio=np.array([1.64,1.66]))
            w._update_radio_auto_gain(result(),100)
            self.assertEqual(w.radio_gain.value(),3.)
            self.assertTrue(w.radio_auto_gain.isChecked())
            self.assertEqual(w.radio_gain_dial.value(),30)
            w._update_radio_auto_gain(result(),100.5)
            self.assertEqual(w.radio_gain.value(),3.)
            old=result();w._reset_processing_settings()
            w._update_radio_auto_gain(old,102)
            self.assertEqual(w.radio_gain.value(),3.)
            w.radio_gain_dial.setValue(120)
            self.assertEqual(w.radio_gain.value(),12.)
            self.assertFalse(w.radio_auto_gain.isChecked())
            w.radio_auto_gain.setChecked(True)
            delivery=result()
            delivery['audio']=np.array([1.61,1.69])
            delivery.update(radio_status=None,radio_key=(1600000,550000,40000,9000),audio_filter=None)
            from monitor.v17.radio_stream import RadioTimeline
            timeline=RadioTimeline(40000)
            timeline.append(np.array([1.6,1.7]),None)
            w.radio_stream=timeline;w.radio_key=delivery['radio_key']
            with patch.object(w.spectral,'reset') as reset,patch('monitor.v17.app.time.monotonic',return_value=200):
                w._accept_processed_radio(delivery)
                reset.assert_not_called()
            self.assertIs(w.radio_stream,timeline)
            self.assertEqual(timeline.counter,4)
            self.assertEqual(w.radio_gain.value(),18.)
            self.assertTrue(w.radio_auto_gain.isChecked())
        finally:w.close();app.processEvents()
