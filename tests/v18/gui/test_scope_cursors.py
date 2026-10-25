import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtCore,QtWidgets,QtTest
from monitor.v18.app import SerialMonitorWindow

class ScopeCursorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v18.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.show();self.app.processEvents();self.c=self.w.scope_cursors
        self.w.current_fs_hz=100000;self.w.x_axis_time_mode=True
        self.x=np.arange(1001,dtype=float)
        self.y={'CH1':self.x/1000,'CH2':2-self.x/500}
        self.w._last_display_frame=(self.x,self.y,('CH1','CH2'))
        self.w.plot_widget.setXRange(0,1000,padding=0);self.w.plot_widget.setYRange(0,3,padding=0)
        self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True)
        self.w.render_timer.stop();self.app.processEvents()
    def tearDown(self):self.w.close();self.app.processEvents()
    def test_channels_snap_to_full_resolution_and_delta(self):
        self.c.place(0,100.1,9);self.c.place(1,600.1,9)
        self.assertEqual(self.c.states[0].x,100)
        self.assertAlmostEqual(self.c.states[0].y,.1)
        self.assertAlmostEqual(self.c.states[1].y,.8)
        self.assertIn('Δt 500',self.c.delta.text());self.assertIn('ΔV 0.7',self.c.delta.text());self.assertIn('2000 Hz',self.c.delta.text())
    def test_gap_and_unavailable_channel_never_make_fake_voltage(self):
        self.y['CH1'][500]=np.nan;self.c.place(0,500,0)
        self.assertFalse(self.c.states[0].valid)
        self.c.channels[0].setCurrentText('RADIO');self.c.place(0,400,0)
        self.assertFalse(self.c.states[0].valid);self.assertEqual(self.c.measurements[0][1][2].text(),'—')
    def test_free_voltage_and_linked_motion(self):
        self.c.modes[0].setCurrentIndex(1);self.c.modes[1].setCurrentIndex(1);self.c.place(0,100,.2);self.c.place(1,500,.7)
        self.c.link.setChecked(True);self.c.place(0,200,.4)
        self.assertEqual(self.c.states[1].x,600);self.assertEqual(self.c.states[1].y,.7)
        self.c.place(0,self.c.states[0].x,.9);self.assertAlmostEqual(self.c.states[0].y,.9)
    def test_mouse_preview_click_fix_and_reselect(self):
        self.c.arm(0)
        view=self.w.plot_widget.getViewBox();viewport=self.w.plot_widget.viewport()
        def pos(x,y):return self.w.plot_widget.mapFromScene(view.mapViewToScene(QtCore.QPointF(x,y)))
        QtTest.QTest.mouseMove(viewport,pos(300,.5));self.app.processEvents()
        self.assertAlmostEqual(self.c.states[0].x,300,delta=3)
        QtTest.QTest.mouseClick(viewport,QtCore.Qt.MouseButton.LeftButton,pos=pos(300,.5));self.assertIsNone(self.c.active)
        fixed=self.c.states[0].x;QtTest.QTest.mouseMove(viewport,pos(700,.5));self.assertEqual(self.c.states[0].x,fixed)
        QtTest.QTest.mouseClick(viewport,QtCore.Qt.MouseButton.LeftButton,pos=pos(fixed,.5));self.assertEqual(self.c.active,0)
    def test_stop_frame_and_time_sample_axis_keep_physical_time(self):
        self.c.place(0,200,0);self.w.is_running=False
        self.w.x_axis_time_mode=False
        self.c.update_frame(self.x/10,self.y,('CH1','CH2'))
        self.assertEqual(self.c.states[0].x,20);self.assertEqual(self.c.read(0)[0],200)
        self.c.invalidate();self.assertFalse(self.c.states[0].valid)
    def test_modes_hide_overlay_and_tabs_have_icons(self):
        for i in range(4):self.assertFalse(self.w.trigger_filter_tabs.tabIcon(i).isNull())
        self.assertEqual(self.w.trigger_filter_tabs.tabText(1),'Cursor')
        self.w.spectral.set_mode(1);self.assertIs(self.c.plots[0],self.w.spectral.plots[0])
        self.w.spectral.set_mode(0);self.assertTrue(self.c.items[0][0].isVisible())

    def test_fft_reads_full_cached_spectrum_with_log_frequency(self):
        s=self.w.spectral;s.channels[0].setCurrentText('CH1');s.channels[1].setCurrentText('CH2')
        s.set_mode(1);s.log_frequency.setChecked(True)
        s._fft_trace_cache={0:(self.w,np.array([0,100,1000,10000]),np.array([-80,-20,-3,-40]),{}),1:(self.w,np.array([0,100,1000,10000]),np.array([-90,-30,-6,-50]),{})}
        self.c.analysis_changed();self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True);self.c.place(0,3,0);self.c.place(1,4,0)
        self.assertEqual(self.c.read(0),(1000,-3));self.assertEqual(self.c.read(1),(10000,-50))
        self.assertIn('Δf 9000 Hz',self.c.delta.text())
        self.c.buttons[0].setChecked(False);self.assertFalse(self.c.items[0][0].isVisible());self.assertTrue(self.c.items[1][0].isVisible())
    def test_heatmap_reports_time_frequency_and_cell_level(self):
        s=self.w.spectral;s.channels[0].setCurrentText('CH1');s.channels[1].setCurrentText('CH2');s.set_mode(2)
        for image in s.images:
            image.setImage(np.full((10,20),-24.));image.setRect(QtCore.QRectF(-2,0,2,10000))
        self.c.analysis_changed();self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True);self.c.place(0,-1,2500);self.c.place(1,-.5,3500)
        self.assertEqual(self.c.read(0),(-1,2500));self.assertEqual(self.c.levels[0],-24)
        self.assertIn('-24',self.c.measurements[0][2][2].text());self.assertIn('Δt 0.5 s',self.c.delta.text())
        s.log_frequency.setChecked(True)
        for image in s.images:
            image.setImage(np.full((10,20),-24.));image.setRect(QtCore.QRectF(-2,2,2,3))
        self.c.place(0,-1,3);self.assertEqual(self.c.read(0),(-1,1000))
    def test_bode_gain_and_phase_keep_correct_units(self):
        s=self.w.spectral;s.set_mode(3);s.bode.result=[(100,1,10),(1000,2,20)]
        self.c.analysis_changed();self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True);self.c.place(0,3,0);self.c.place(1,3,0)
        self.assertEqual(self.c.channels[0].currentText(),'Ganancia');self.assertEqual(self.c.channels[1].currentText(),'Fase')
        self.assertEqual(self.c.read(0),(1000,2));self.assertEqual(self.c.read(1),(1000,20))
        self.assertIn('unidades distintas',self.c.delta.text())

    def test_demo_runs_through_scope_fft_and_heatmap_with_cursors(self):
        self.c.clear();self.w.start_demo();self.w.demo_timer.stop();self.w.render_timer.stop()
        self.w.trigger_checkbox.setChecked(False)
        for _ in range(50):self.w._generate_demo_samples()
        self.w.render_frame()
        self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True);self.c.center()
        self.assertTrue(all(s.valid for s in self.c.states))
        self.assertAlmostEqual(self.c.us_per_x,1.)
        s=self.w.spectral;s.size.setCurrentText('256')
        s.channels[0].setCurrentText('CH1');s.channels[1].setCurrentText('CH2')
        s.set_mode(1);s.last_fast_render=0;s.render();self.c.analysis_changed()
        self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True)
        self.c.place(0,100,0);self.c.place(1,100,0)
        self.assertTrue(all(state.valid for state in self.c.states))
        s.set_mode(2);s.last_fast_render=0;s.render();self.c.analysis_changed()
        self.c.buttons[0].setChecked(True);self.c.buttons[1].setChecked(True)
        for i in range(2):
            image=s.images[i];self.assertIsNotNone(image.image)
            rect=image.mapRectToParent(image.boundingRect())
            col=image.image.shape[1]-1
            x=rect.left()+(col+.5)*rect.width()/image.image.shape[1]
            y=rect.top()+2.5*rect.height()/image.image.shape[0]
            self.c.place(i,x,y)
        self.assertTrue(all(state.valid for state in self.c.states))
        self.c.clear();self.assertTrue(all(not item.isVisible() for group in self.c.items for item in group))

    def test_follow_and_free_are_independent_per_cursor(self):
        self.c.modes[0].setCurrentIndex(1)
        self.c.place(0,100,.77);self.c.place(1,600,.99)
        self.assertAlmostEqual(self.c.states[0].y,.77)
        self.assertAlmostEqual(self.c.states[1].y,.8)
        self.assertEqual(self.c.modes[0].height(),self.w.btn_xaxis_toggle.height())

    def test_analysis_banks_restore_position_source_modes_and_enable_state(self):
        self.c.modes[0].setCurrentIndex(1);self.c.place(0,220,.42)
        self.c.buttons[1].setChecked(False);self.c.link.setChecked(True)
        s=self.w.spectral;s.set_mode(1)
        self.c.modes[0].setCurrentIndex(1);self.c.modes[1].setCurrentIndex(1)
        self.c.place(0,123,.9);self.c.buttons[1].setChecked(True);self.c.link.setChecked(False)
        s.set_mode(0)
        self.assertEqual((self.c.states[0].x,self.c.states[0].y),(220,.42))
        self.assertFalse(self.c.buttons[1].isChecked());self.assertTrue(self.c.link.isChecked())
        s.set_mode(1)
        self.assertEqual((self.c.states[0].x,self.c.states[0].y),(123,.9))
        self.assertTrue(self.c.buttons[1].isChecked());self.assertFalse(self.c.link.isChecked())
        s.set_mode(2);self.c.place(0,-1,1000)
        s.set_mode(1)
        self.assertEqual((self.c.states[0].x,self.c.states[0].y),(123,.9))

    def test_new_analysis_starts_off_and_keeps_its_own_enabled_state(self):
        s=self.w.spectral
        for mode in (1,2,3):
            s.set_mode(mode)
            self.assertTrue(all(not button.isChecked() for button in self.c.buttons))
            self.assertTrue(all(not item.isVisible() for group in self.c.items for item in group))
        s.set_mode(0);self.assertTrue(all(button.isChecked() for button in self.c.buttons))
        s.set_mode(1);self.c.buttons[1].setChecked(True)
        s.set_mode(0);s.set_mode(1)
        self.assertFalse(self.c.buttons[0].isChecked());self.assertTrue(self.c.buttons[1].isChecked())

    def test_only_tags_on_graph_and_readouts_in_cursor_tab_b_minus_a(self):
        self.c.place(0,100,0);self.c.place(1,600,0)
        for i,name in enumerate(('A','B')):
            self.assertEqual(self.c.items[i][3].toPlainText(),name)
            self.assertAlmostEqual(self.c.items[i][3].pos().x(),self.c.states[i].x)
        self.assertEqual(self.c.measurements[0][0][2].text(),'100 µs')
        self.assertEqual(self.c.measurements[0][1][2].text(),'100 mV')
        self.assertEqual(self.c.measurements[1][0][2].text(),'600 µs')
        self.assertEqual(self.c.differences[0][2].text(),'500 µs')
        self.assertEqual(self.c.differences[1][2].text(),'700 mV')

class CursorFormatTests(unittest.TestCase):
    def test_decimal_comma_compact_precision_and_automatic_units(self):
        from monitor.v18.scope_cursors import reading
        for value,unit,expected in ((12345,'µs','12,3 ms'),(.00045,'s','450 µs'),(1500000,'µs','1,5 s'),(.01234,'V','12,3 mV'),(-.5,'V','-500 mV'),(1.234,'V','1,23 V'),(2500,'Hz','2,5 kHz'),(0,'V','0 V')):
            self.assertEqual(reading(value,unit),expected)
