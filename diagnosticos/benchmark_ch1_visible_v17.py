"""Native visible CH1 paint comparison with synthetic timed input; no Q access."""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reference',type=Path,default=ROOT/'diagnosticos/referencias/ch1_render_before_20261015.py')
    parser.add_argument('--before-reducer',type=Path)
    parser.add_argument('--seconds',type=float,default=5)
    parser.add_argument('--samples',type=int,default=140351)
    args=parser.parse_args()
    import numpy as np
    from unittest.mock import patch
    from PyQt6 import QtCore,QtWidgets
    import pyqtgraph as pg
    active={'start':None,'paints':[],'renders':[],'polls':0,'exposed':0}
    tracked=[]
    class PaintPlot(pg.PlotWidget):
        def paintEvent(self,event):
            start=time.perf_counter()
            super().paintEvent(event)
            if self in tracked and active['start'] is not None:
                active['paints'].append((time.perf_counter()-start)*1000)
    pg.PlotWidget=PaintPlot
    from monitor.v17 import app as module
    from monitor.v17.numeric_batch import NumericBatch,SampleClock
    reference=args.before_reducer or args.reference
    namespace=dict(vars(module));exec(reference.read_text(),namespace)
    new=module.SerialMonitorWindow.render_frame
    old=new if args.before_reducer else namespace['render_frame']
    before_reducer=namespace['_reduce_trace_for_display'] if args.before_reducer else None
    after_reducer=module.SerialMonitorWindow._reduce_trace_for_display
    app=QtWidgets.QApplication([])
    with patch('monitor.v17.app.usb_devices',return_value=[]):w=module.SerialMonitorWindow()
    tracked.append(w.plot_widget)
    w.render_timer.stop();w._acquisition_confirmed(8,1403508)
    w.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint,True)
    w.resize(1320,860);w.show();w.raise_();w.activateWindow();app.processEvents()
    c=w.applied_configuration;clock=SampleClock(c.timestamp_hz)
    def feed_count(count):
        if count<=0:return
        i=np.arange(w.sample_counter,w.sample_counter+count,dtype=np.int64)
        raw=np.column_stack(((i*c.period)%2**32,
             127.5+100*np.sin(2*np.pi*5000*i/c.actual_rate),np.zeros(count),i))
        w.handle_batch(NumericBatch(raw,c.maximum,clock,1))
    feed_count(250000)
    for name,action in w.graph_channel_actions.items():action.setChecked(name=='CH1')
    w._calculate_sample_rate();w.trigger_enabled=True;w.trigger_level=1.65
    w.h_scale=args.samples;w.x_axis_time_mode=True
    report={'scope':__doc__+' Synthetic input bypasses transport/decoder; native paintEvent counts, not physical Q acceptance.',
            'qt_platform':app.platformName(),'samples_visible':args.samples,'requested_fs':c.actual_rate,
            'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(inspect.getsource(new).encode()).hexdigest(),'cases':[]}
    report['app_file_sha256']=hashlib.sha256((ROOT/'monitor/v17/app.py').read_bytes()).hexdigest()
    report['comparison']='reducer' if args.before_reducer else 'render'
    sequence=[('before',old),('after',new),('after',new),('before',old)]
    state={'index':-1,'fn':new,'origin_time':0.,'origin_sample':0}
    def render():
        start=time.perf_counter();state['fn'](w)
        if active['start'] is not None:active['renders'].append((time.perf_counter()-start)*1000)
    def feed():
        target=state['origin_sample']+int((time.perf_counter()-state['origin_time'])*c.actual_rate)
        feed_count(target-w.sample_counter)
    def poll():
        if active['start'] is not None:
            active['polls']+=1
            active['exposed']+=int(w.isVisible() and w.windowHandle().isExposed())
    def finish_case():
        elapsed=time.perf_counter()-active['start']
        paints=active['paints'];renders=active['renders']
        report['cases'].append({'variant':sequence[state['index']][0],'seconds':elapsed,
            'paint_fps':len(paints)/elapsed,'render_fps':len(renders)/elapsed,
            'paint_ms_p50':float(np.median(paints)) if paints else None,
            'render_ms_p50':float(np.median(renders)) if renders else None,
            'exposed_fraction':active['exposed']/max(1,active['polls']),
            'painting_valid':bool(paints) and active['exposed']/max(1,active['polls'])>.99,
            'actual_samples_visible':w.h_scale,
            'samples_received':w.sample_counter-active['sample_start'],
            'received_fs':(w.sample_counter-active['sample_start'])/elapsed})
        active['start']=None
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        next_case()
    def measure():
        active.update(start=time.perf_counter(),sample_start=w.sample_counter,
                      paints=[],renders=[],polls=0,exposed=0)
        QtCore.QTimer.singleShot(round(args.seconds*1000),finish_case)
    def next_case():
        state['index']+=1
        if state['index']==len(sequence):
            for timer in (feed_timer,render_timer,poll_timer):timer.stop()
            module.SerialMonitorWindow._reduce_trace_for_display=staticmethod(after_reducer)
            w.close();app.quit();return
        state['fn']=sequence[state['index']][1]
        if args.before_reducer:
            module.SerialMonitorWindow._reduce_trace_for_display=staticmethod(
                before_reducer if sequence[state['index']][0]=='before' else after_reducer)
        state['origin_time']=time.perf_counter();state['origin_sample']=w.sample_counter
        w.h_scale=args.samples;w.raise_();w.activateWindow()
        QtCore.QTimer.singleShot(1000,measure)
    feed_timer=QtCore.QTimer();feed_timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    feed_timer.timeout.connect(feed)
    render_timer=QtCore.QTimer();render_timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    render_timer.timeout.connect(render)
    poll_timer=QtCore.QTimer();poll_timer.timeout.connect(poll)
    next_case();feed_timer.start(20);render_timer.start(16);poll_timer.start(100)
    app.exec()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
