import os
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.receiver.unoq_acquisition import Configuration
from monitor.v20.temporal_paint import balanced_visual_interval,visual_interval


class BalancedCadenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v20.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.render_timer.stop()
        self.w._temporal_paint_ms=10.;self.w._temporal_prepare_ms=2.

    def tearDown(self):self.w.close();self.qt.processEvents()

    def test_formula_and_legacy_boundary(self):
        self.assertEqual(balanced_visual_interval(10,2),34)
        self.assertEqual(balanced_visual_interval(20,10),50)
        self.assertEqual(balanced_visual_interval(400,100),500)
        self.assertEqual(visual_interval(16,10,2),40)

    def test_already_fast_views_and_analysis_modes_are_not_slowed(self):
        w=self.w;w.applied_configuration=Configuration(14,40000)
        w._temporal_cost_samples=w.h_scale
        w._temporal_paint_ms=2.;w._temporal_prepare_ms=1.
        w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),16)
        w.spectral.set_mode(1)
        self.assertFalse(w._balanced_temporal_eligible())
        w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),16)

    def test_exact_rate_window_and_mode_boundary(self):
        w=self.w
        w.applied_configuration=Configuration(14,40000);w.h_scale=80000
        self.assertTrue(w._balanced_temporal_eligible())
        w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),34)
        w.h_scale=80001
        self.assertFalse(w._balanced_temporal_eligible())
        w._temporal_cost_samples=80001
        w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),40)
        w.h_scale=80000;w.applied_configuration=Configuration(14,50000)
        self.assertFalse(w._balanced_temporal_eligible())

    def test_radio_filter_and_raster_keep_old_policy(self):
        w=self.w
        with patch.object(w.radio_enabled,'isChecked',return_value=True):
            self.assertFalse(w._balanced_temporal_eligible())
        w.filter_config=replace(w.filter_config,source='CH1')
        self.assertFalse(w._balanced_temporal_eligible())
        w.filter_config=replace(w.filter_config,source='OFF')
        w.selected_columns['RADIO']=True
        self.assertFalse(w._balanced_temporal_eligible())
        w.selected_columns['RADIO']=False;w.selected_columns['FILTER']=True
        self.assertFalse(w._balanced_temporal_eligible())
        w.selected_columns['FILTER']=False
        w.temporal_raster=SimpleNamespace(active=True,close=lambda:None)
        self.assertFalse(w._balanced_temporal_eligible())

    def test_trigger_single_cursors_detail_and_two_channels_remain_eligible(self):
        w=self.w
        w.trigger_enabled=True;w.single_shot_armed=True
        w.scope_cursors.states[0].enabled=True
        w.detail_slider.setValue(100)
        w.selected_columns['CH2']=True
        self.assertTrue(w._balanced_temporal_eligible())
        w._temporal_paint_ms=10.;w._temporal_prepare_ms=2.
        w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),34)


if __name__=='__main__':unittest.main()
