"""Regression for avoiding hidden RF-history copies during FFT redraws."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from monitor.v19.app import SerialMonitorWindow
from monitor.v19.history import SampleHistory


class SpectralMeasurementCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6 import QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_fft_refresh_does_not_copy_long_temporal_windows(self):
        window = SerialMonitorWindow()
        try:
            count = 4096
            window.sample_numbers.extend(range(1, count + 1))
            for name, history in window.series.items():
                history.extend(range(count))
            window.sample_counter = count
            window.h_scale = count
            window.is_running = True
            window.spectral.set_mode(1)
            window._last_measurement_update = 0

            def forbidden_window_copy(*_args, **_kwargs):
                raise AssertionError('FFT measurement refresh copied a temporal window')

            window._window_values = forbidden_window_copy
            window.render_frame()
            self.assertGreater(window._last_measurement_update, 0)
        finally:
            window.close()
            self.app.processEvents()

    def test_bode_plot_redraw_accepts_a_live_synthetic_curve(self):
        window = SerialMonitorWindow()
        try:
            window.spectral.set_mode(3)
            bode = window.spectral.bode.panels[window.spectral.bode.tabs.currentIndex()]
            bode.result = [(20.0 * 10 ** (i / 48), -i / 20, -i / 5)
                           for i in range(384)]
            bode.draw()
            self.app.processEvents()
            self.assertEqual(len(bode.result), 384)
            self.assertTrue(any(curve.getData()[0] is not None and len(curve.getData()[0])
                                for curve in bode.curve_sets[0]))
        finally:
            window.close()
            self.app.processEvents()

    def test_live_history_view_avoids_copy_when_contiguous_and_keeps_wrap_order(self):
        history = SampleHistory(8)
        history.extend(range(6))
        view = history.window_view(1, 5)
        self.assertTrue(__import__('numpy').shares_memory(view, history.data))
        self.assertEqual(view.tolist(), [1, 2, 3, 4])
        history.extend([6, 7, 8, 9])
        wrapped = history.window_view(0, len(history))
        self.assertEqual(wrapped.tolist(), [2, 3, 4, 5, 6, 7, 8, 9])

    def test_uniform_long_trace_keeps_each_bucket_extrema_and_gaps_are_checked_in_chunks(self):
        import numpy as np
        x=np.arange(20000,dtype=float)*.5
        y=np.sin(np.arange(20000)*.03)
        y[1234]=9.;y[15001]=-8.
        xr,yr=SerialMonitorWindow._reduce_trace_for_display(x,y,x[0],x[-1],80,uniform_hint=True)
        self.assertLess(len(xr),len(x)//20)
        self.assertEqual(float(yr.max()),float(y.max()))
        self.assertEqual(float(yr.min()),float(y.min()))
        self.assertFalse(SerialMonitorWindow._display_has_time_gaps(x,1.0,chunk_size=127))
        x[128]+=(2.0)
        self.assertTrue(SerialMonitorWindow._display_has_time_gaps(x,1.0,chunk_size=127))

    def test_wrapped_long_history_builds_extrema_without_flattening_the_ring(self):
        import numpy as np
        history=SampleHistory(1000)
        history.extend(np.sin(np.arange(900,dtype=float)*.1))
        history.extend(np.cos(np.arange(200,dtype=float)*.07))
        parts=history.window_parts(0,len(history))
        self.assertEqual(len(parts),2)
        indices=SerialMonitorWindow._history_window_extrema_indices(history,0,len(history),100)
        reduced=SerialMonitorWindow._history_values_at(history,0,indices)
        full=history.window(0,len(history))
        self.assertAlmostEqual(float(reduced.min()),float(full.min()))
        self.assertAlmostEqual(float(reduced.max()),float(full.max()))

    def test_time_gap_offsets_are_recorded_once_as_batches_arrive(self):
        import numpy as np
        self.assertEqual(SerialMonitorWindow._time_gap_offsets(
            np.array([10., 10.5, 11., 11.5]), 9.5, 1.0), ())
        self.assertEqual(SerialMonitorWindow._time_gap_offsets(
            np.array([12., 12.5, 20., 20.5]), 11.5, 1.0), (2,))
        self.assertEqual(SerialMonitorWindow._time_gap_offsets(
            np.array([15., 15.5]), 10., 1.0), (0,))
        self.assertEqual(SerialMonitorWindow._time_gap_offsets(
            np.array([10., np.nan, 11.]), 9.5, 1.0), (1,))

    def test_long_window_gap_lookup_uses_recorded_absolute_indices(self):
        from collections import deque
        history=SampleHistory(50);history.extend(range(50))
        window=SerialMonitorWindow()
        try:
            window.sample_counter=100
            window._time_gap_sample_indices=deque([55,88])
            self.assertTrue(window._history_window_has_gaps(history,0,20))
            self.assertTrue(window._history_window_has_gaps(history,20,40))
            self.assertFalse(window._history_window_has_gaps(history,0,5))
        finally:
            window.close();self.app.processEvents()

    def test_live_vt_axis_fills_edges_without_artificial_padding(self):
        import numpy as np
        window=SerialMonitorWindow()
        try:
            count=100
            window.sample_numbers.extend(np.arange(1,count+1,dtype=float))
            window.series['CH1'].extend(np.sin(np.arange(count,dtype=float)))
            window.series['Tiempo (us)'].extend(np.arange(count,dtype=float)*2.5)
            window.sample_counter=count;window.h_scale=count;window.is_running=True
            window.x_axis_time_mode=True;window.current_dt_us=2.5;window.current_fs_hz=400000.
            window.trigger_enabled=False;window.selected_columns={'CH1':True,'CH2':False,'FILTER':False,'RADIO':False}
            window.render_frame()
            x_range=window.plot_widget.getViewBox().viewRange()[0]
            self.assertAlmostEqual(x_range[0],0.,places=6)
            self.assertAlmostEqual(x_range[1],247.5,places=4)
        finally:
            window.close();self.app.processEvents()

    def test_high_rate_frequency_measurement_expands_for_slow_tones(self):
        import numpy as np
        from monitor.v19.app import _estimate_frequency_hz
        rate=1_860_465
        count=4*rate
        t=np.arange(count,dtype=float)/rate
        signal=np.sin(2*np.pi*1.0*t)
        mean=float(np.mean(signal))
        recent=signal[-min(count,max(131072,min(524288,int(rate*.25)))):]
        self.assertLess(len(np.flatnonzero((recent[:-1]<mean)&(recent[1:]>=mean))),2)
        self.assertAlmostEqual(_estimate_frequency_hz(signal,None,rate,mean),1.0,places=3)
        times=t*1_000_000
        self.assertAlmostEqual(_estimate_frequency_hz(signal,times,rate,mean),1.0,places=3)
        for hz in (2,5,50):
            wave=np.sin(2*np.pi*hz*t)
            self.assertAlmostEqual(_estimate_frequency_hz(wave,None,rate,float(np.mean(wave))),hz,places=2)
        short=np.sin(2*np.pi*t[:int(rate*.1)])
        self.assertIsNone(_estimate_frequency_hz(short,None,rate,float(np.mean(short))))
        self.assertIsNone(_estimate_frequency_hz(np.zeros(1000),None,rate,0.))

    def test_stop_freezes_full_vt_frame_before_history_ring_is_reused(self):
        import numpy as np
        window=SerialMonitorWindow()
        try:
            count=20000
            x=np.arange(count,dtype=float)*2.5
            y=np.sin(np.arange(count,dtype=float)*.013)
            window.sample_numbers.extend(np.arange(1,count+1,dtype=float))
            window.series['CH1'].extend(y)
            window.series['Tiempo (us)'].extend(x)
            window.sample_counter=count;window.h_scale=count
            window.current_dt_us=2.5;window.current_fs_hz=400000.
            window.x_axis_time_mode=True;window.trigger_enabled=False
            window.selected_columns={'CH1':True,'CH2':False,'FILTER':False,'RADIO':False}
            window.detail_slider.setValue(50)
            window.is_running=True
            window.render_frame()
            live=window._last_display_frame[1]['CH1']
            self.assertLess(len(live),count)  # long live windows may use the envelope

            window.run_stop_btn.setChecked(False)
            window.toggle_run_stop()
            frozen_x,frozen_y,_=window._last_display_frame
            self.assertEqual(len(frozen_y['CH1']),count)
            self.assertFalse(np.shares_memory(frozen_y['CH1'],window.series['CH1'].data))
            self.assertFalse(np.shares_memory(frozen_x,window.series['Tiempo (us)'].data))
            expected=frozen_y['CH1'].copy()

            window.series['CH1'].data[:]=12345.
            window.detail_slider.setValue(100)
            self.assertEqual(len(window._last_display_frame[1]['CH1']),count)
            np.testing.assert_array_equal(window._last_display_frame[1]['CH1'],expected)
            window.scope_cursors.buttons[0].setChecked(True)
            window.scope_cursors.place(0,x[10000],0.)
            self.assertEqual(window.scope_cursors.read(0),(x[10000],expected[10000]))
        finally:
            window.close();self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
