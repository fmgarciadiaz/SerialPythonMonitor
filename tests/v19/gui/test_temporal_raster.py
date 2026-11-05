import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['PYQTGRAPH_QT_LIB']='PySide6'
import time
import unittest
from unittest.mock import patch
import numpy as np
from PySide6 import QtWidgets,QtGui,QtCore
import pyqtgraph as pg
from monitor.v19.temporal_raster import RasterProcess,RasterItem,paint_traces,prepare_vertices
from monitor.v19.app import SerialMonitorWindow


class RasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_full_geometry_keeps_impulse_steps_and_gaps(self):
        x=np.array([0.,1.,2.,10.,11.]);y=np.array([0.,0.,99.,0.,0.])
        xx,yy=prepare_vertices(x,y,True,True,False,0)
        self.assertTrue(np.isnan(yy).any())
        self.assertEqual(yy[np.isfinite(yy)].max(),99.)
        for a,b in zip(x,y):self.assertTrue(np.any((xx==a)&(yy==b)))
        linear=prepare_vertices(x,y,False,False,False,0)
        np.testing.assert_equal(linear,(x,y))

    def test_process_renders_full_snapshot_without_blocking_gui_and_releases_memory(self):
        worker=RasterProcess()
        try:
            x=np.linspace(0,1,724000);y=np.random.default_rng(1).normal(size=len(x))
            frame=(x.copy(),{'CH1':y.copy()},('CH1',))
            opts=dict(step=False,gap_cut=False,time_mode=False,dt=0,style='Normal')
            self.assertTrue(worker.submit([(x,y,'#ffcc00')],(0,1,-5,5),(1100,600),opts,'token',frame))
            names=[worker.pending[k].name for k in ('inputs','output')]
            self.assertFalse(worker.submit([],(),(1,1),{},None,None))
            x[:]=5;y[:]=8
            gaps=[];result=None;last=time.perf_counter();deadline=last+25
            while result is None and time.perf_counter()<deadline:
                self.qt.processEvents();now=time.perf_counter();gaps.append(now-last);last=now
                result=worker.poll();time.sleep(.005)
            self.assertIsNotNone(result)
            self.assertLess(max(gaps),.5)
            self.assertEqual(result['token'],'token')
            np.testing.assert_equal(result['frame'][1]['CH1'],frame[1]['CH1'])
            self.assertEqual(result['image'].size(),QtCore.QSize(1100,600))
            expected=QtGui.QImage(1100,600,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
            expected.fill(QtCore.Qt.GlobalColor.transparent)
            paint_traces(expected,[(frame[0],frame[1]['CH1'],'#ffcc00')],(0,1,-5,5),opts)
            self.assertEqual(bytes(expected.bits()),bytes(result['image'].bits()))
            from multiprocessing import shared_memory
            for name in names:
                with self.assertRaises(FileNotFoundError):shared_memory.SharedMemory(name=name)
        finally:worker.close()
        self.assertFalse(worker.process.is_alive())

    def test_raster_item_y_orientation_and_scaling_match_vector(self):
        image=QtGui.QImage(200,100,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        opts=dict(step=False,gap_cut=False,time_mode=False,dt=0,style='Normal')
        paint_traces(image,[(np.array([0.,1.]),np.array([.8,.8]),'#ff0000')],(0,1,0,1),opts)
        scene=QtWidgets.QGraphicsScene();item=RasterItem();scene.addItem(item);item.publish(image,(0,1,0,1))
        # Scene Y is down; ViewBox would invert it. The high-Y data line must
        # remain at .8 in scene coordinates, not .2.
        out=QtGui.QImage(200,100,QtGui.QImage.Format.Format_ARGB32_Premultiplied);out.fill(0)
        p=QtGui.QPainter(out);scene.render(p,QtCore.QRectF(0,0,200,100),QtCore.QRectF(0,0,1,1));p.end()
        pixels=np.frombuffer(out.bits(),np.uint8).reshape(100,200,4)
        self.assertGreater(pixels[79:82,:,3].sum(),0)
        self.assertEqual(pixels[18:22,:,3].sum(),0)

    def test_styles_dpr_steps_and_gaps_match_vector_with_small_raster_tolerance(self):
        for dpr in (1,2):
            for style in ('Rápido','Intenso','Suave'):
                for step in (False,True):
                    with self.subTest(dpr=dpr,style=style,step=step):
                        x=np.linspace(0,1,201);y=np.sin(x*16)
                        y[40:44]=np.nan;y[90]=np.inf;y[130]=1.5
                        opts=dict(step=step,gap_cut=True,time_mode=False,dt=0,style=style,dpr=dpr)
                        width,height=400*dpr,180*dpr
                        a=QtGui.QImage(width,height,QtGui.QImage.Format.Format_ARGB32_Premultiplied);a.fill(0)
                        b=a.copy();rect=(0,1,-2,2)
                        paint_traces(a,[(x,y,'#00e5ff')],rect,opts)
                        xx,yy=prepare_vertices(x,y,step,True,False,0)
                        xx=xx*width;yy=(2-yy)*height/4
                        curve=pg.PlotCurveItem(xx,yy,pen=pg.mkPen('#00e5ff',width=(2 if style=='Intenso' else 1)*dpr),
                                               connect='finite',antialias=style=='Suave')
                        painter=QtGui.QPainter(b)
                        curve.paint(painter,QtWidgets.QStyleOptionGraphicsItem(),None);painter.end()
                        self.assertGreater(np.frombuffer(b.bits(),np.uint8).sum(),0)
                        aa=np.frombuffer(a.bits(),np.uint8).astype(float)
                        bb=np.frombuffer(b.bits(),np.uint8).astype(float)
                        # Qt's segmented caps and antialiased joins may differ
                        # by a few pixels; all data geometry remains identical.
                        self.assertLess(np.abs(aa-bb).mean(),2.)

    def test_dense_application_frame_is_actually_published(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window.show();self.qt.processEvents()
            window.detail_slider.setValue(100);window.known_columns=['CH1'];window._update_curve_items(['CH1'])
            window.plot_widget.setXRange(0,1,padding=0)
            x=np.linspace(0,1,724000);y=1.6+.1*np.sin(x*10000)
            window._draw_display_frame(x,{'CH1':y},['CH1']);r=window.temporal_raster
            deadline=time.monotonic()+5
            while not r.published and not r.failed and time.monotonic()<deadline:
                self.qt.processEvents();time.sleep(.005)
            self.assertIsNone(r.error_message)
            self.assertGreater(r.published,0,dict(active=r.active,failed=r.failed,rejected=r.rejected,last_rejection=r.last_rejection,timer=r.timer.isActive(),worker=bool(r.worker),busy=bool(r.worker and r.worker.busy),context=r.context(),pending_token=r.worker.pending['token'] if r.worker and r.worker.pending else None))
            self.assertTrue(r.item.isVisible())
        finally:window.close()

    def test_view_change_discards_pending_frame_and_stop_uses_independent_snapshot(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):window=SerialMonitorWindow()
        try:
            window.detail_slider.setValue(100);window.known_columns=['CH1'];window._update_curve_items(['CH1'])
            window.plot_widget.setXRange(0,1,padding=0)
            x=np.linspace(0,1,100001);y=np.sin(x*100)
            window._draw_display_frame(x,{'CH1':y},['CH1']);raster=window.temporal_raster
            submitted=raster.worker.pending['frame'];y[:]=42
            self.assertLess(np.max(submitted[1]['CH1']),2)
            window.spectral.set_mode(1)
            deadline=time.monotonic()+15
            while raster.active and time.monotonic()<deadline:self.qt.processEvents();time.sleep(.01)
            self.assertFalse(raster.item.isVisible())
            self.assertEqual(raster.published,0)
        finally:window.close()

class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        class Worker:
            def __init__(self):self.pending=None;self.ready=False;self.sent=[]
            @property
            def busy(self):return self.pending is not None
            def submit(self,traces,rect,size,options,token,frame):
                self.pending=dict(token=token,frame=frame,rect=rect);self.sent.append(self.pending);return True
            def poll(self):
                if not self.ready:return None
                p=self.pending;self.pending=None;self.ready=False
                im=QtGui.QImage(4,4,QtGui.QImage.Format.Format_ARGB32_Premultiplied);im.fill(0)
                return dict(**p,image=im,milliseconds=1000.)
            def close(self):self.pending=None
        self.patch=patch('monitor.v19.temporal_raster.RasterProcess',Worker);self.patch.start()
        with patch('monitor.v19.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.detail_slider.setValue(100);self.w.known_columns=['CH1'];self.w._update_curve_items(['CH1'])
        self.x=np.linspace(0,1,100001);self.y=np.ones(len(self.x))
        self.w._last_display_frame=(self.x,{'CH1':self.y},('CH1',))
        self.w._draw_display_frame(*self.w._last_display_frame)
        self.r=self.w.temporal_raster;self.r.timer.stop()
    def tearDown(self):self.w.close();self.patch.stop()
    def complete(self):self.r.worker.ready=True;self.r.poll()
    def test_single_replaces_live_job_with_captured_frame(self):
        self.y[:]=7
        self.w._set_single_state('captured');self.w.is_running=False
        self.y[:]=99
        self.complete()
        self.assertEqual(self.r.published,0)
        self.complete()
        self.assertEqual(self.r.published,1)
        np.testing.assert_equal(self.w._visible_display_frame[1]['CH1'],7.)
    def test_queued_frame_cannot_be_relabelled_after_another_view_change(self):
        self.w.plot_widget.setXRange(0,2,padding=0)
        self.w._draw_display_frame(self.x,{'CH1':np.full(len(self.x),7.)},('CH1',))
        self.assertIsNotNone(self.r.queued)
        self.w.plot_widget.setXRange(0,3,padding=0)
        self.complete()
        self.assertEqual(self.r.published,0)
        # A resize may repaint the original immutable frame, but must never
        # assign a new context to the rejected replacement (value 7).
        self.assertEqual(len(self.r.worker.sent),2)
        np.testing.assert_equal(self.r.worker.sent[-1]['frame'][1]['CH1'],1.)
    def test_clear_rejects_old_job_and_clears_cursor_data(self):
        self.w.clear_data();self.complete()
        self.assertEqual(self.r.published,0)
        self.assertIsNone(self.w._visible_display_frame)
        self.assertIsNone(self.w.scope_cursors.frame)
    def test_stop_zoom_requests_new_image_and_invalidates_old_cursor(self):
        self.complete();self.assertEqual(self.r.published,1)
        self.w.is_running=False
        self.w.scope_cursors.frame=self.w._visible_display_frame
        self.w.plot_widget.setXRange(0,2,padding=0);self.r.poll()
        self.assertIsNone(self.w.scope_cursors.frame)
        self.assertTrue(self.r.worker.busy)
        self.complete();self.assertEqual(self.r.published,2)
    def test_rf_single_explicit_frame_replaces_previous_cached_live_frame(self):
        captured=np.full(len(self.x),13.)
        self.w._set_single_state('captured',(self.x,{'CH1':captured},('CH1',)))
        self.w.is_running=False;captured[:]=22
        self.complete();self.complete()
        np.testing.assert_equal(self.w._visible_display_frame[1]['CH1'],13.)
    def test_stop_then_zoom_while_busy_requests_current_frozen_view(self):
        self.w.is_running=False;self.r.invalidate()
        self.w._draw_display_frame(*self.w._last_display_frame)
        self.w.plot_widget.setXRange(0,2,padding=0)
        self.complete()
        self.assertTrue(self.r.worker.busy)
        self.complete();self.assertEqual(self.r.published,1)
        self.assertTrue(self.r.item.isVisible())
    def test_measured_rate_noise_does_not_invalidate_hardware_job(self):
        self.w.serial_worker=object()
        try:
            before=self.r.context()
            self.w.current_dt_us+=1e-8;self.w.current_fs_hz+=.01
            self.assertEqual(before,self.r.context())
        finally:self.w.serial_worker=None
    def test_trigger_edit_rejects_incompatible_pending_capture(self):
        self.w.trigger_enabled=True;self.w.trigger_level=2.2
        self.complete()
        self.assertEqual(self.r.published,0)
        self.assertIsNone(self.w._visible_display_frame)
        self.w._draw_display_frame(*self.w._last_display_frame)
        self.complete();self.assertEqual(self.r.published,1)

    def test_pending_replacement_coalesces_live_redraws(self):
        self.w.plot_widget.setXRange(0,2,padding=0)
        self.w._draw_display_frame(*self.w._last_display_frame)
        queued=self.r.queued
        self.w._draw_display_frame(*self.w._last_display_frame)
        self.assertIs(self.r.queued,queued)
        self.assertTrue(self.r.skip_live())


if __name__=='__main__':unittest.main()
