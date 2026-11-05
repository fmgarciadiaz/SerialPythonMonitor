import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from types import SimpleNamespace as NS
import numpy as np
from unittest.mock import patch
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow as W
from monitor.v20.history import SampleHistory
from monitor.v20.temporal_raster import prepare_vertices


def display():
    return NS(detail_slider=NS(value=lambda:50),current_dt_us=25.,
        x_axis_time_mode=True,auto_gap_cut=True,
        _display_has_time_gaps=W._display_has_time_gaps,
        _reduce_trace_for_display=W._reduce_trace_for_display,
        _prepare_trace_data=lambda x,y,detect_gaps=True:
            prepare_vertices(x,y,True,True,True,25.,detect_gaps))


class ReducedSquareTests(unittest.TestCase):
    def test_live_draw_preserves_continuity_but_actual_clock_gap_is_cut(self):
        qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v20.app.usb_devices',return_value=[]):w=W()
        try:
            w.render_timer.stop();n=80000;clock=np.arange(n)*25.
            values=np.where(np.arange(n)%20<10,1.,-1.)
            w.sample_counter=n;w.sample_numbers.extend(np.arange(n))
            w.series['Tiempo (us)'].extend(clock);w.series['CH1'].extend(values)
            w.current_dt_us=25.;w.h_scale=n;w.h_pos=0;w.trigger_enabled=False;w.is_running=True
            w.selected_columns={name:name=='CH1' for name in w.known_columns}
            with patch.object(w,'_display_pixels',return_value=400),patch.object(w,'_update_live_measurements'):
                w.render_frame()
                self.assertIs(w._continuous_reduced_frame,w._last_display_frame)
                self.assertTrue(np.isfinite(w.line_items['CH1'].getData()[1]).all())
                clock[40000:]+=10000
                w.series['Tiempo (us)'].clear();w.series['Tiempo (us)'].extend(clock)
                w._time_gap_sample_indices.append(40000)
                w.h_scale=n;w._roll_position=None
                w.render_frame()
                self.assertIsNone(w._continuous_reduced_frame)
                self.assertTrue(np.isnan(w.line_items['CH1'].getData()[1]).any())
        finally:w.close();qt.processEvents()

    def test_phase_and_ring_wrap_do_not_create_false_gaps(self):
        w=display()
        for count in (9000,80000):
            for phase in range(20):
                raw=np.where((np.arange(count+137)+phase)%20<10,1.,-1.)
                history=SampleHistory(count);history.extend(raw[:count]);history.extend(raw[count:])
                indices=W._history_window_extrema_indices(history,0,count,400)
                x=indices*25.;y=W._history_values_at(history,0,indices)
                xp,yp=W._display_trace(w,x,y,0,(count-1)*25.,400,known_continuous=True)
                self.assertTrue(np.isfinite(yp).all())
                self.assertEqual((yp.min(),yp.max()),(-1.,1.))
                self.assertTrue(np.all(np.diff(xp)>=0))
    def test_actual_gap_and_nan_still_separate_traces(self):
        x=np.arange(9000)*25.;y=np.where(np.arange(9000)%20<10,1.,-1.)
        x[4500:]+=10000;y[2000]=np.nan
        xp,yp=W._display_trace(display(),x,y,0,x[-1],400)
        self.assertTrue(np.isnan(yp).any())
        # No finite adjacent segment can bridge the actual timestamp gap.
        crosses=(xp[:-1]<x[4500])&(xp[1:]>=x[4500])
        self.assertFalse(np.any(crosses & np.isfinite(yp[:-1]) & np.isfinite(yp[1:])))


if __name__=='__main__':unittest.main()
