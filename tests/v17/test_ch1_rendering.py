"""CH1 high-rate display updates preserve trigger and axis interactions."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v17.app import SerialMonitorWindow
from monitor.v17.numeric_batch import NumericBatch,SampleClock


class Ch1RenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.render_timer.stop();self.w._acquisition_confirmed(8,1403508)
        c=self.w.applied_configuration;i=np.arange(30000)
        raw=np.column_stack(((i*c.period)%2**32,
                             127.5+100*np.sin(2*np.pi*5000*i/c.actual_rate),np.zeros(len(i)),i))
        self.w.handle_batch(NumericBatch(raw,c.maximum,SampleClock(c.timestamp_hz),1))
        for name,action in self.w.graph_channel_actions.items():action.setChecked(name=='CH1')
        self.w._calculate_sample_rate();self.w.h_scale=1404
        self.w.trigger_enabled=True;self.w.trigger_level=1.65

    def tearDown(self):self.w.close()

    def test_trigger_frames_reuse_label_and_style_but_update_units_and_edge(self):
        w=self.w;w.x_axis_time_mode=False;w.render_frame()
        with patch.object(w.plot_widget,'setLabel',wraps=w.plot_widget.setLabel) as label, \
             patch.object(w.trigger_status_label,'setStyleSheet',wraps=w.trigger_status_label.setStyleSheet) as style:
            for _ in range(3):w.render_frame()
            label.assert_not_called();style.assert_not_called()
            w.trigger_edge='Descendente';w.render_frame()
            self.assertIn('Descendente',w.trigger_status_label.text())
            label.assert_not_called();style.assert_not_called()
            w.x_axis_time_mode=True;w.render_frame()
            self.assertIn('µs',w.plot_widget.getAxis('bottom').labelText)
            self.assertEqual(label.call_count,1)
            w.render_frame();self.assertEqual(label.call_count,1)
            style.assert_not_called()

    def test_search_normal_and_single_transitions_keep_frame_immutable(self):
        w=self.w;w.render_frame();w.arm_single_shot();w.render_frame()
        self.assertFalse(w.single_shot_armed);self.assertFalse(w.is_running)
        x,ys=w.frozen_frame;before_x=x.copy();before_y=ys['CH1'].copy()
        w.detail_slider.setValue(0)
        np.testing.assert_array_equal(x,before_x);np.testing.assert_array_equal(ys['CH1'],before_y)
        w.is_running=True;w.trigger_enabled=True;w.trigger_mode='Normal'
        w.trigger_level=10.;w.render_frame()
        self.assertIn('Normal',w.trigger_status_label.text())
        with patch.object(w.trigger_status_label,'setStyleSheet') as style:
            w.render_frame();style.assert_not_called()
        w.trigger_mode='Auto';w.frozen_frame=None;w.render_frame()
        self.assertIn('Auto',w.trigger_status_label.text())
        self.assertIn('Buscando Trigger',w.plot_widget.getAxis('bottom').labelText)
        w.trigger_level=1.65;w.render_frame()
        self.assertIn('Disparo',w.trigger_status_label.text())
        self.assertNotIn('Buscando',w.plot_widget.getAxis('bottom').labelText)


class HistoryTriggerTests(unittest.TestCase):
    def search(self, history, start, end, rising):
        from types import SimpleNamespace
        owner=SimpleNamespace(_window_values=SerialMonitorWindow._window_values)
        return SerialMonitorWindow._last_history_trigger(owner,history,start,end,0.,rising,.015)

    def test_recent_search_matches_reference_at_tail_boundaries_and_wrap(self):
        from monitor.v17.history import SampleHistory
        from tests.v17.test_trigger import reference_crossing
        from collections import deque
        size=12000;start=123;end=11000;tail=end-2048
        cases=[np.sin(np.arange(size)*.17),1e-6*np.sin(np.arange(size))]
        for relative in range(-2,13):
            values=np.full(size,.001);values[tail+relative-1]=-.5
            cases.append(values)
            values=values.copy();values[tail+relative-4]=np.nan
            cases.append(values)
        for case,values in enumerate(cases):
            history=SampleHistory(size)
            history.extend(np.zeros(37));history.extend(values[:-37]);history.extend(values[-37:])
            for storage in (history,deque(values)):
                for rising in (False,True):
                    with self.subTest(case=case,storage=type(storage).__name__,rising=rising):
                        i=reference_crossing(values[start:end],0.,rising,.015)
                        result=self.search(storage,start,end,rising)
                        if i is None:self.assertIsNone(result)
                        else:
                            self.assertEqual(result[0],start+i)
                            np.testing.assert_array_equal(result[1:],values[start+i-1:start+i+1])

    def test_recent_hit_reads_only_tail_and_slow_signal_falls_back(self):
        from monitor.v17.history import SampleHistory
        history=SampleHistory(100000);history.extend(np.sin(np.arange(100000)*.17))
        with patch.object(history,'window',wraps=history.window) as read:
            self.assertIsNotNone(self.search(history,1000,90000,True))
            read.assert_called_once_with(90000-2048,90000)
        values=np.full(100000,.001);values[2000]=-.5
        history.clear();history.extend(values)
        with patch.object(history,'window',wraps=history.window) as read:
            self.assertEqual(self.search(history,1000,90000,True)[0],2001)
            self.assertEqual([call.args for call in read.call_args_list],[(87952,90000),(1000,90000)])


if __name__=='__main__':unittest.main()
