import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PySide6 import QtWidgets
from monitor.v19.locale_axis import LocaleAxis,time_unit
from monitor.v19.app import SerialMonitorWindow
from unittest.mock import Mock


class TimeAndMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_time_axis_scales_ticks_without_changing_coordinates(self):
        axis=LocaleAxis('bottom');axis.set_time_label('Tiempo',1e-6)
        for extent,unit,scale in ((.5,'ns',1000.),(50,'µs',1.),(50000,'ms',.001),(5000000,'s',1e-6)):
            axis.setRange(-extent,extent)
            self.assertEqual(axis.labelUnits,unit)
            self.assertAlmostEqual(axis.scale,scale)
            self.assertEqual(axis.range,[-extent,extent])
        axis.set_time_label('Muestras',None)
        self.assertEqual(axis.scale,1.)
        self.assertFalse(axis.labelUnits)
        self.assertEqual(time_unit(.001),('ms',.001))
        self.assertEqual(time_unit(1),('s',1.))

    def test_all_measurement_values_follow_selected_channel_and_custom_color(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window.meas_channel_combo.setCurrentText('CH2')
            for value in window._measurement_values:
                self.assertIn('color:'+window.channel_colors['CH2'],value.styleSheet())
            window.channel_colors['CH2']='#123456'
            window._on_meas_channel_changed('CH2')
            for value in window._measurement_values:self.assertIn('color:#123456',value.styleSheet())
        finally:window.close()

    def test_real_paint_budget_paces_drawing_and_live_slider_is_coalesced(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window._note_temporal_paint(80)
            self.assertGreaterEqual(window.render_timer.interval(),320)
            window.serial_worker=Mock();window.is_running=True
            window._last_display_frame=([],{},[])
            with patch.object(window,'_draw_display_frame') as draw:
                window.detail_slider.setValue(100)
                draw.assert_not_called()
            self.assertEqual(window.detail_slider.value(),100)
            window.serial_worker=None
            window.spectral.set_mode(1)
            self.assertLessEqual(window.render_timer.interval(),20)
        finally:
            window.serial_worker=None;window.close()
