"""Offline real-QTimer mixed-view A/B; changes only a window-local paint observer."""
import argparse
import gc
import json
import os
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtCore,QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.history import SampleHistory
from monitor.v20.receiver.unoq_acquisition import Configuration

RF_RATE=1_860_465; N=3_720_930; AN=80_000
PYTHON='/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python'


def make_history(values,wrapped,headroom):
    cap=len(values) if wrapped else len(values)+headroom
    h=SampleHistory(cap)
    if wrapped:
        h.extend(np.concatenate((values[-4096:],values[:-4096])))
        h.extend(values[-4096:])
    else:h.extend(values)
    return h


def percentile(xs,p):return float(np.percentile(xs,p)) if len(xs) else None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=float,default=5.)
    parser.add_argument('--pairs',type=int,default=6)
    args=parser.parse_args()
    if sys.executable!=PYTHON:raise SystemExit('Use '+PYTHON)
    qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    out=ROOT/'diagnosticos/resultados_v20/mixed_timer_20261103';out.mkdir(parents=True,exist_ok=True)
    x=np.arange(N,dtype=float)*(1e6/RF_RATE)
    y=np.where(np.arange(N)%53<26,2.2,1.1).astype(float)
    ax=np.arange(AN,dtype=float)*25.
    ay=1.65+.25*np.sin(np.arange(AN)*.1)
    with patch('monitor.v20.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
    try:
        w.resize(1280,800);w.show();qt.processEvents()
        w.render_timer.stop()
        w.known_columns=['CH1','RADIO'];w.selected_columns={'CH1':True,'RADIO':True}
        w._update_curve_items(['CH1','RADIO'])
        w.applied_configuration=Configuration(8,RF_RATE)
        w.current_dt_us=1e6/RF_RATE;w.current_fs_hz=RF_RATE
        w.h_scale=N;w.h_pos=0;w.x_axis_time_mode=True;w.trigger_enabled=False
        w.is_running=True;w.detail_slider.setValue(50);w.active_meas_channel='CH1'
        w.scope_cursors.states[0].enabled=False
        original_paint=w._note_temporal_paint
        original_render=w._render_with_diagnostics
        w.render_timer.timeout.disconnect(original_render)
        state={'row':None,'last_painted':None,'prepared_epoch':None}

        def on_paint(ms):
            row=state['row']
            if row is None:return original_paint(ms)
            before=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId())
            if row['candidate']:
                w._temporal_paint_ms=max(ms,getattr(w,'_temporal_paint_ms',0.)*.85)
                w._temporal_paint_max_ms=max(ms,getattr(w,'_temporal_paint_max_ms',0.))
            else:original_paint(ms)
            after=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId())
            epoch=state['prepared_epoch']
            fresh=epoch is not None and state['last_painted']!=epoch
            row['paint'].append(dict(t=time.perf_counter()-row['start'],ms=ms,epoch=epoch,
                                     fresh=fresh,before=before,after=after))
            state['last_painted']=epoch

        def on_render():
            row=state['row']
            if row is None:return original_render()
            before=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId())
            old_measure=w._last_measurement_update
            began=time.perf_counter();original_render();duration=(time.perf_counter()-began)*1000
            after=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId())
            row['render'].append(dict(t=time.perf_counter()-row['start'],ms=duration,
                                      epoch=w.sample_counter,before=before,after=after,
                                      measured=w._last_measurement_update!=old_measure))
            state['prepared_epoch']=w.sample_counter

        w.plot_widget.paint_observer=on_paint
        w.render_timer.timeout.connect(on_render)

        tick=QtCore.QTimer();tick.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        tick.setInterval(40)
        sequence=[(wrapped,candidate) for wrapped in (False,True)
                  for pair in range(args.pairs+1)
                  for candidate in ((True,False) if pair%2==0 else (False,True))]
        rows=[];previous_tick=None
        for case,(wrapped,candidate) in enumerate(sequence):
            w.render_timer.stop();tick.stop()
            w.series['Tiempo (us)']=make_history(x,wrapped,300_000)
            w.series['CH1']=make_history(y,wrapped,300_000)
            audio={'Tiempo (us)':make_history(ax,wrapped,10_000),
                   'RADIO':make_history(ay,wrapped,10_000)}
            w.radio_stream=SimpleNamespace(rate=40000,sample_numbers=make_history(np.arange(AN,dtype=float),wrapped,10_000),
                                           series=audio,counter=AN)
            w.sample_counter=N;w._last_measurement_update=0
            w._temporal_paint_ms=w._temporal_prepare_ms=0.
            w._refresh_render_cadence()
            row=dict(case=case,wrapped=wrapped,candidate=candidate,warmup=(case//2)% (args.pairs+1)==0,
                     start=time.perf_counter(),render=[],paint=[],ticks=[])
            state['row']=row;state['last_painted']=None;state['prepared_epoch']=None
            rf_index=[N];audio_index=[AN]
            def advance():
                rf_index[0]+=2000;audio_index[0]+=43
                ri=np.arange(rf_index[0]-2000,rf_index[0],dtype=float)
                ai=np.arange(audio_index[0]-43,audio_index[0],dtype=float)
                w.series['Tiempo (us)'].extend(ri*(1e6/RF_RATE))
                w.series['CH1'].extend(np.where(ri.astype(np.int64)%53<26,2.2,1.1))
                audio['Tiempo (us)'].extend(ai*25.)
                audio['RADIO'].extend(1.65+.25*np.sin(ai*.1))
                w.radio_stream.sample_numbers.extend(ai)
                w.radio_stream.counter=audio_index[0]
                w.sample_counter=rf_index[0]
                row['ticks'].append((time.perf_counter()-row['start'],rf_index[0]))
            if previous_tick is not None:tick.timeout.disconnect(previous_tick)
            tick.timeout.connect(advance)
            previous_tick=advance
            w.render_timer.start();tick.start()
            loop=QtCore.QEventLoop()
            QtCore.QTimer.singleShot(round(args.seconds*1000),loop.quit)
            loop.exec()
            tick.stop();w.render_timer.stop();state['row']=None
            rows.append(row)
            print('case',case,'wrapped',wrapped,'candidate',candidate,'render',len(row['render']),
                  'fresh',sum(p['fresh'] for p in row['paint']),flush=True)
            gc.collect()
        report={'scope':'Offline Qt event loop; no Q; advancing synthetic RF/audio every 40 ms',
                'seconds':args.seconds,'pairs':args.pairs,'rows':rows}
        (out/'timer_ab_raw.json').write_text(json.dumps(report,indent=2)+'\n')
        summaries=[]
        for r in rows:
            if r['warmup']:continue
            fresh=[e['t'] for e in r['paint'] if e['fresh']]
            intervals=np.diff(fresh)*1000
            costs=[e['ms'] for e in r['render']]+[e['ms'] for e in r['paint']]
            summaries.append(dict(case=r['case'],wrapped=r['wrapped'],candidate=r['candidate'],
                                  new_frames=len(fresh),repaints=len(r['paint'])-len(fresh),
                                  median_interval_ms=float(np.median(intervals)) if len(intervals) else None,
                                  p95_interval_ms=percentile(intervals,95),
                                  gui_cost_total_ms=sum(costs),
                                  measurements=sum(e['measured'] for e in r['render']),
                                  peak_render_ms=max([e['ms'] for e in r['render']],default=None)))
        (out/'timer_ab_summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
        print(out/'timer_ab_summary.json')
    finally:w.close();qt.processEvents()


if __name__=='__main__':main()
