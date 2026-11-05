import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['PYQTGRAPH_QT_LIB']='PySide6'
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets,QtTest
import pyqtgraph as pg
from monitor.v20.locale_axis import LocaleAxis
from monitor.v20.radio_led_spectrum import RadioLedSpectrum
from monitor.v20.radio_output_panel import RadioOutputPanel


class FluencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def pixels(self,widget):
        image=widget.grab().toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        return np.frombuffer(image.constBits(),dtype=np.uint8,count=image.sizeInBytes()).copy()

    def test_axis_cache_preserves_pixels_and_invalidates_on_zoom_and_resize(self):
        w=pg.PlotWidget(axisItems={'bottom':LocaleAxis('bottom'),'left':LocaleAxis('left')})
        w.resize(500,320);w.showGrid(x=True,y=True);w.plot(np.arange(50),np.sin(np.arange(50)))
        w.show();self.qt.processEvents()
        try:
            for axis in ('bottom','left'):w.getAxis(axis).cache_static_paint=False
            for _ in range(3):self.pixels(w)
            baseline=self.pixels(w)
            for axis in ('bottom','left'):w.getAxis(axis).cache_static_paint=True
            for _ in range(3):self.pixels(w)
            self.assertTrue(np.array_equal(baseline,self.pixels(w)))
            old=w.getAxis('bottom')._static_axis_cache
            w.setXRange(10,30,padding=0);self.qt.processEvents();self.pixels(w)
            self.assertIsNot(old,w.getAxis('bottom')._static_axis_cache)
            self.assertEqual(w.getAxis('bottom').range,[10.,30.])
            w.resize(600,400);self.qt.processEvents();self.pixels(w)
            self.assertNotEqual(old[1],w.getAxis('bottom')._static_axis_cache[1])
        finally:w.close()

    def test_time_label_does_not_invalidate_an_unchanged_axis(self):
        axis=LocaleAxis('bottom');axis.setRange(0,5000);axis.set_time_label('Tiempo',1e-6)
        sentinel=QtGui.QPicture();axis.picture=sentinel
        axis.set_time_label('Tiempo',1e-6)
        self.assertIs(axis.picture,sentinel)
        self.assertEqual(axis.labelUnits,'ms')

    def test_large_reduced_view_uses_measured_cost_full_detail_keeps_floor(self):
        from monitor.v20.app import SerialMonitorWindow
        with patch('monitor.v20.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.render_timer.stop();w.h_scale=4_000_000;w._temporal_cost_samples=w.h_scale
            w.detail_slider.setValue(50)
            w._temporal_paint_ms=0.;w._temporal_prepare_ms=0.
            w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),100)
            w._temporal_paint_ms=2.;w._temporal_prepare_ms=2.
            w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),16)
            w.detail_slider.setValue(100)
            w._temporal_cost_samples=w.h_scale;w._temporal_paint_ms=2.;w._temporal_prepare_ms=2.
            w._refresh_render_cadence();self.assertEqual(w.render_timer.interval(),100)
        finally:w.close();self.qt.processEvents()

    def test_spectrum_holds_target_between_audio_batches_and_reuses_background(self):
        spectrum=RadioLedSpectrum();spectrum.resize(230,92)
        spectrum.feed(1.65+np.sin(np.arange(2048)*2*np.pi*1000/40000),'tone',40000,1.65)
        spectrum.refresh(0.,True,1.);target=spectrum._target.copy()
        self.assertGreater(target.max(),.1)
        spectrum.refresh(.1,True,1.);self.assertTrue(np.array_equal(target,spectrum._target))
        self.pixels(spectrum);background=spectrum._background
        spectrum.levels[:]=.5;self.pixels(spectrum);self.assertIs(spectrum._background,background)
        spectrum.resize(300,92);self.pixels(spectrum);self.assertIsNot(spectrum._background,background)
        spectrum.refresh(.2,False,1.);self.assertTrue(np.all(spectrum._target==0))
        spectrum.close()

    def test_radio_animation_is_independent_of_the_trace_timer_and_stops_hidden(self):
        owner=SimpleNamespace(radio_enabled=QtWidgets.QCheckBox())
        owner.radio_enabled.setChecked(True)
        panel=RadioOutputPanel(owner);panel.resize(230,320)
        times=[];original=panel.refresh_meter
        def refresh(now):times.append(now);original(now)
        panel.refresh_meter=refresh
        try:
            panel.show();self.qt.processEvents()
            settings=SimpleNamespace(radio_offset=1.65,audio_rate=40000)
            panel.observe_audio(dict(settings=settings,radio_key='tone',audio=1.65+np.sin(np.arange(2048)*.1)))
            QtTest.QTest.qWait(210)
            self.assertTrue(panel.animation_timer.isActive());self.assertGreaterEqual(len(times),4)
            self.assertGreater(panel.audio_spectrum.levels.max(),0.)
            panel.hide();self.assertFalse(panel.animation_timer.isActive())
            panel.show();self.qt.processEvents();owner.radio_enabled.setChecked(False)
            QtTest.QTest.qWait(50);self.assertFalse(panel.animation_timer.isActive())
            self.assertEqual(panel.volume.audio_meter_level,0.)
        finally:panel.close()

    def test_radio_ring_holds_between_batches_but_follows_volume_and_stale_input(self):
        owner=SimpleNamespace(radio_enabled=QtWidgets.QCheckBox())
        owner.radio_enabled.setChecked(True);panel=RadioOutputPanel(owner)
        try:
            panel._meter_audio_at=10.;panel._meter_peak=1.
            panel.refresh_meter(10.);first=panel._meter_target
            self.assertGreater(first,0.)
            panel.refresh_meter(10.1);self.assertEqual(panel._meter_target,first)
            panel.volume.setValue(30);panel.refresh_meter(10.2)
            self.assertAlmostEqual(panel._meter_target,first/2)
            panel.refresh_meter(10.4);self.assertEqual(panel._meter_target,0.)
        finally:panel.close()


if __name__=='__main__':unittest.main()
