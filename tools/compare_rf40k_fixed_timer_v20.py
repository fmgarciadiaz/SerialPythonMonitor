"""Native Qt, offline V20 adaptive/fixed timer comparison. Never opens Scope Q."""
import argparse
import importlib
import json
import os
import resource
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtCore,QtWidgets


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixed-timer',action='store_true')
    parser.add_argument('--run',type=int,required=True)
    parser.add_argument('--window',type=int,default=9000)
    parser.add_argument('--channels',type=int,choices=(1,2),default=1)
    parser.add_argument('--warmup',type=float,default=3)
    parser.add_argument('--measure',type=float,default=10)
    args=parser.parse_args()
    if os.environ.get('QT_QPA_PLATFORM')=='offscreen':raise SystemExit('Native Qt required')
    if not os.environ.get('PYTHONPYCACHEPREFIX','').startswith('/tmp/'):
        raise SystemExit('Set PYTHONPYCACHEPREFIX under /tmp')
    app=QtWidgets.QApplication([])
    mod=importlib.import_module('monitor.v20.app')
    numeric=importlib.import_module('monitor.v20.numeric_batch')
    config=importlib.import_module('monitor.v20.receiver.unoq_acquisition').Configuration
    with patch.object(mod,'usb_devices',return_value=[]):w=mod.SerialMonitorWindow()
    raw=[];start=time.perf_counter();measuring=[False]
    try:
        w.render_timer.stop();w.resize(1280,800);w.move(100,100)
        w.applied_configuration=config(14,40000)
        w.current_fs_hz=40000;w.current_dt_us=25.
        w.h_scale=args.window;w.h_pos=0;w.x_axis_time_mode=True
        w.detail_slider.setValue(50)
        w.trace_style_combo.setCurrentText('Rápido')
        w.trace_mode_combo.setCurrentText('Escalón (Step)')
        w.plot_widget.showGrid(x=True,y=True)
        w.trigger_enabled=False;w.single_shot_armed=False
        w.scope_cursors.states[0].enabled=False
        w.filter_source.setCurrentText('Ninguno')
        names=['CH1']+(['CH2'] if args.channels==2 else [])
        w.selected_columns={name:name in names for name in w.known_columns}
        w._update_curve_items(names)
        w.is_running=True
        if args.fixed_timer:
            # Private candidate: preserve measurement of paint/prepare cost,
            # but bypass adaptive QTimer changes for this exact case only.
            w._refresh_render_cadence=lambda:None
            w.render_timer.setInterval(16)
        w.show();app.processEvents()
        exposure=lambda: bool(w.windowHandle() and w.windowHandle().isExposed())
        original_paint=w.plot_widget.paint_observer
        original_render=w._render_with_diagnostics
        original_measure=w._update_live_measurements
        w.render_timer.timeout.disconnect(original_render)
        prepared=[None];painted=[None]

        def on_paint(ms):
            original_paint(ms)
            if measuring[0]:
                epoch=prepared[0]
                fresh=epoch is not None and painted[0]!=epoch
                raw.append(dict(kind='paint',t=time.perf_counter()-start,ms=ms,
                                epoch=epoch,fresh=fresh,exposed=exposure(),
                                interval=w.render_timer.interval(),fps=w.current_fps,
                                timer_id=w.render_timer.timerId()))
                painted[0]=epoch

        def on_measure(*a,**k):
            began=time.perf_counter()
            try:return original_measure(*a,**k)
            finally:
                if measuring[0]:raw.append(dict(kind='measure',t=time.perf_counter()-start,
                                                ms=(time.perf_counter()-began)*1000))

        def on_render():
            before=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId())
            began=time.perf_counter();original_render();duration=(time.perf_counter()-began)*1000
            prepared[0]=w.sample_counter
            if measuring[0]:
                paint4=getattr(w,'_temporal_paint_ms',0.)*4
                prep3=getattr(w,'_temporal_prepare_ms',0.)*3
                raw.append(dict(kind='render',t=time.perf_counter()-start,ms=duration,
                                epoch=prepared[0],before=before,
                                after=(w.render_timer.interval(),w.render_timer.remainingTime(),w.render_timer.timerId()),
                                base=16,paint4=paint4,prep3=prep3,
                                dominant=max(((16,'base'),(paint4,'paint4'),(prep3,'prep3')))[1]))

        w.plot_widget.paint_observer=on_paint
        w._update_live_measurements=on_measure
        w.render_timer.timeout.connect(on_render)
        sample=[0];blocks=[0];feed_started=[None];max_backlog=[0]
        measure_start_cpu=[None];measure_start_blocks=[None];measure_start_time=[None]
        feed=QtCore.QTimer();feed.setTimerType(QtCore.Qt.TimerType.PreciseTimer);feed.setInterval(10)
        def deliver():
            now=time.perf_counter()
            expected=max(0,int((now-feed_started[0])/.01))
            backlog=max(0,expected-blocks[0]);max_backlog[0]=max(max_backlog[0],backlog)
            while blocks[0]<expected:
                due_at=feed_started[0]+(blocks[0]+1)*.01
                i=np.arange(sample[0],sample[0]+400,dtype=np.float64)
                # 40 kS/s deterministic CH1/CH2 square wave, fixed 25-us clock.
                data=np.column_stack((i*25.,np.where((i.astype(np.int64)%53)<26,11500,5500),
                                      np.where((i.astype(np.int64)%97)<48,10000,6000),i))
                sample[0]+=400;blocks[0]+=1
                batch=numeric.NumericBatch(data,16383)
                began=time.perf_counter();w.handle_batch(batch)
                if measuring[0]:raw.append(dict(kind='ingest',t=time.perf_counter()-start,
                                                ms=(time.perf_counter()-began)*1000,epoch=w.sample_counter,
                                                callback_delay_ms=max(0,(began-due_at)*1000),
                                                backlog_before=backlog))
        feed.timeout.connect(deliver)
        feed_started[0]=time.perf_counter();w.render_timer.start();feed.start()
        def begin():
            raw.clear();prepared[0]=None;painted[0]=None;measuring[0]=True
            measure_start_time[0]=time.perf_counter()
            measure_start_blocks[0]=blocks[0]
            usage=resource.getrusage(resource.RUSAGE_SELF)
            measure_start_cpu[0]=usage.ru_utime+usage.ru_stime
        QtCore.QTimer.singleShot(round(args.warmup*1000),begin)
        QtCore.QTimer.singleShot(round((args.warmup+args.measure)*1000),app.quit)
        app.exec();feed.stop();w.render_timer.stop();measuring[0]=False
        ended=time.perf_counter();usage=resource.getrusage(resource.RUSAGE_SELF)
        cpu=(usage.ru_utime+usage.ru_stime)-measure_start_cpu[0]
        expected_blocks=int((ended-feed_started[0])/.01)
        expected_measure_blocks=max(0,int((ended-measure_start_time[0])/.01))
        screen=w.screen()
        geom=w.geometry();view=w.plot_widget.getViewBox()
        output=dict(version='v20',fixed_timer=args.fixed_timer,run=args.run,requested=dict(window=args.window,channels=args.channels,
                    warmup_s=args.warmup,measure_s=args.measure,detail=50,style='Rápido',trace='Escalón',grid=True,
                    trigger=False,cursors=False,radio=False,filter=False),
                    geometry=[geom.x(),geom.y(),geom.width(),geom.height()],
                    screen=screen.name() if screen else None,dpr=w.devicePixelRatioF(),
                    exposed_at_end=exposure(),plot_width=view.width(),
                    plotted_points=len(w.line_items['CH1'].getData()[0]),
                    feed=dict(expected_blocks=expected_blocks,delivered_blocks=blocks[0],
                              expected_measure_blocks=expected_measure_blocks,
                              delivered_measure_blocks=blocks[0]-measure_start_blocks[0],
                              expected_samples=expected_blocks*400,delivered_samples=sample[0],
                              max_backlog_blocks=max_backlog[0]),
                    cpu_seconds=cpu,events=raw)
        out=ROOT/'diagnosticos/resultados_v20/rf40k_fixed_timer_20261103'
        out.mkdir(parents=True,exist_ok=True)
        path=out/f'{args.run:02d}_{"fixed" if args.fixed_timer else "adaptive"}_w{args.window}_ch{args.channels}.json'
        path.write_text(json.dumps(output,indent=2)+'\n')
        print(path,flush=True)
        print('events',len(raw),'paint',sum(e['kind']=='paint' for e in raw),
              'new',sum(e['kind']=='paint' and e['fresh'] for e in raw),flush=True)
    finally:w.close();app.processEvents()


if __name__=='__main__':main()
