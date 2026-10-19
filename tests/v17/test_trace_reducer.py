"""Drawing optimizations must return exactly the same points as the baseline."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from types import MethodType,SimpleNamespace
import unittest
import numpy as np
from monitor.v17 import app as module

REFERENCE=Path(__file__).resolve().parents[2]/'diagnosticos/referencias/trace_reducer_before_20261015.py'
namespace=dict(vars(module));exec(REFERENCE.read_text(),namespace)
reference_reducer=namespace['_reduce_trace_for_display']


class TraceReducerTests(unittest.TestCase):
    def assert_same(self,x,y,pixels=75):
        xmin,xmax=0.,max(1.,float(len(x)))
        before=reference_reducer(x,y,xmin,xmax,pixels)
        after=module.SerialMonitorWindow._reduce_trace_for_display(x,y,xmin,xmax,pixels)
        for expected,actual in zip(before,after):
            np.testing.assert_array_equal(actual,expected)

    def test_exact_points_uniform_irregular_gaps_nonfinite_and_extrema(self):
        rng=np.random.default_rng(401)
        for count in (0,1,299,300,301,10000,140351):
            x=np.arange(count,dtype=float);y=rng.normal(size=count)
            for spacing in (.7125,1.,25.):
                with self.subTest(count=count,spacing=spacing):self.assert_same(x*spacing,y)
            if not count:continue
            for kind in ('impulse','flat','gap','duplicate','reverse','nan_x','nan_y','inf_y','offset'):
                xx=x.copy();yy=y.copy()
                if kind=='impulse':yy[:]=0.;yy[count//2]=123.
                if kind=='flat':yy[:]=.5
                if kind=='gap':xx[count//2:]+=50
                if kind=='duplicate':xx=np.floor(x/2)
                if kind=='reverse':xx=-xx
                if kind=='nan_x':xx[count//2]=np.nan
                if kind=='nan_y':yy[count//2]=np.nan
                if kind=='inf_y':yy[count//2]=np.inf
                if kind=='offset':xx+=1e9
                with self.subTest(count=count,kind=kind):self.assert_same(xx,yy)

    def test_uniformity_tolerance_boundaries_match_allclose(self):
        # Include representable values immediately around the existing tolerance.
        for spacing in (.125,1.,25.):
            tolerance=1e-9+1e-9*abs(spacing)
            for sign in (-1,1):
                boundary=spacing+sign*tolerance
                for step in (np.nextafter(boundary,-np.inf),boundary,np.nextafter(boundary,np.inf)):
                    deltas=np.full(10000,spacing);deltas[5000]=step
                    x=np.r_[0.,np.cumsum(deltas)];y=np.sin(np.arange(len(x)))
                    with self.subTest(spacing=spacing,step=step):self.assert_same(x,y)

    def test_every_slider_level_preserves_step_linear_and_gap_vertices(self):
        owner=SimpleNamespace(auto_gap_cut=True,x_axis_time_mode=True,current_dt_us=.7125)
        owner._prepare_trace_data=MethodType(module.SerialMonitorWindow._prepare_trace_data,owner)
        x=np.arange(20000)*.7125;y=np.sin(x);y[8000]=20.
        for detail in range(101):
            owner.detail_slider=SimpleNamespace(value=lambda:detail)
            pixels=module.SerialMonitorWindow._display_pixels(owner,500)
            for mode in ('Escalón','Línea'):
                owner.trace_mode=mode
                for gaps in (False,True):
                    xx=x.copy()
                    if gaps:xx[10000:]+=2000
                    before_x=xx.copy();before_y=y.copy()
                    owner._reduce_trace_for_display=reference_reducer
                    before=module.SerialMonitorWindow._display_trace(owner,xx,y,xx[0],xx[-1],pixels)
                    owner._reduce_trace_for_display=module.SerialMonitorWindow._reduce_trace_for_display
                    after=module.SerialMonitorWindow._display_trace(owner,xx,y,xx[0],xx[-1],pixels)
                    with self.subTest(detail=detail,mode=mode,gaps=gaps):
                        for expected,actual in zip(before,after):
                            np.testing.assert_array_equal(actual,expected)
                        np.testing.assert_array_equal(xx,before_x)
                        np.testing.assert_array_equal(y,before_y)


if __name__=='__main__':unittest.main()
