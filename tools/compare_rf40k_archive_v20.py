"""Read-only native PyQt6 V17/V18 RF reference; one version per process."""
import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PyQt6 import QtCore,QtWidgets


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',choices=('v17','v18'),required=True)
    parser.add_argument('--warmup',type=float,default=3)
    parser.add_argument('--measure',type=float,default=10)
    args=parser.parse_args()
    if os.environ.get('QT_QPA_PLATFORM')=='offscreen':raise SystemExit('Native Qt required')
    if not os.environ.get('PYTHONPYCACHEPREFIX','').startswith('/tmp/'):
        raise SystemExit('Set PYTHONPYCACHEPREFIX under /tmp')
    app=QtWidgets.QApplication([])
    mod=importlib.import_module(f'monitor.{args.version}.app')
    numeric=importlib.import_module(f'monitor.{args.version}.numeric_batch')
    config=importlib.import_module(f'monitor.{args.version}.receiver.unoq_acquisition').Configuration
    with patch.object(mod,'usb_devices',return_value=[]):w=mod.SerialMonitorWindow()
    events=[];start=time.perf_counter();measuring=[False];prepared=[None];painted=[None]
    try:
        w.render_timer.stop();w.resize(1280,800);w.move(100,100)
        w.applied_configuration=config(14,40000)
        w.current_fs_hz=40000;w.current_dt_us=25.
        w.h_scale=9000;w.h_pos=0;w.x_axis_time_mode=True
        w.detail_slider.setValue(50)
        w.trace_style_combo.setCurrentText('Rápido')
        w.trace_mode_combo.setCurrentText('Escalón (Step)')
        w.plot_widget.showGrid(x=True,y=True)
        w.trigger_enabled=False;w.single_shot_armed=False
        if hasattr(w,'scope_cursors'):w.scope_cursors.states[0].enabled=False
        w.filter_source.setCurrentText('Ninguno')
        w.selected_columns={name:name=='CH1' for name in w.known_columns}
        w._update_curve_items(['CH1'])
        w.is_running=True;w.show();app.processEvents()
        original_render=w._render_with_diagnostics
        original_measure=w._update_live_measurements
        w.render_timer.timeout.disconnect(original_render)

        class PaintFilter(QtCore.QObject):
            def eventFilter(self,obj,event):
                if event.type()==QtCore.QEvent.Type.Paint and measuring[0]:
                    epoch=prepared[0];fresh=epoch is not None and painted[0]!=epoch
                    exposed=bool(w.windowHandle() and w.windowHandle().isExposed())
                    events.append(dict(kind='paint_event',t=time.perf_counter()-start,
                                       epoch=epoch,fresh=fresh,exposed=exposed,
                                       fps=getattr(w,'current_fps',None)))
                    painted[0]=epoch
                return False
        observer=PaintFilter(w.plot_widget.viewport())
        w.plot_widget.viewport().installEventFilter(observer)

        def on_measure(*a,**k):
            began=time.perf_counter()
            try:return original_measure(*a,**k)
            finally:
                if measuring[0]:events.append(dict(kind='measure',t=time.perf_counter()-start,
                                                   ms=(time.perf_counter()-began)*1000))

        def on_render():
            before=w.render_timer.interval();began=time.perf_counter()
            original_render();duration=(time.perf_counter()-began)*1000
            prepared[0]=w.sample_counter
            if measuring[0]:events.append(dict(kind='render',t=time.perf_counter()-start,
                                               ms=duration,epoch=prepared[0],
                                               interval_before=before,interval_after=w.render_timer.interval()))
        w._update_live_measurements=on_measure
        w.render_timer.timeout.connect(on_render)
        sample=[0]
        feed=QtCore.QTimer();feed.setTimerType(QtCore.Qt.TimerType.PreciseTimer);feed.setInterval(10)
        def deliver():
            i=np.arange(sample[0],sample[0]+400,dtype=np.float64)
            data=np.column_stack((i*25.,np.where((i.astype(np.int64)%53)<26,11500,5500),
                                  np.where((i.astype(np.int64)%97)<48,10000,6000),i))
            sample[0]+=400
            batch=numeric.NumericBatch(data,16383)
            began=time.perf_counter();w.handle_batch(batch)
            if measuring[0]:events.append(dict(kind='ingest',t=time.perf_counter()-start,
                                               ms=(time.perf_counter()-began)*1000))
        feed.timeout.connect(deliver)
        w.render_timer.start();feed.start()
        def begin():
            events.clear();prepared[0]=None;painted[0]=None;measuring[0]=True
        QtCore.QTimer.singleShot(round(args.warmup*1000),begin)
        QtCore.QTimer.singleShot(round((args.warmup+args.measure)*1000),app.quit)
        app.exec();feed.stop();w.render_timer.stop();measuring[0]=False
        geom=w.geometry();view=w.plot_widget.getViewBox();screen=w.screen()
        result=dict(version=args.version,qt='PyQt6',warmup_s=args.warmup,measure_s=args.measure,
                    requested=dict(rate=40000,window=9000,channels=['CH1'],detail=50,
                                   style='Rápido',trace='Escalón',grid=True,
                                   trigger=False,cursors=False,radio=False,filter=False),
                    geometry=[geom.x(),geom.y(),geom.width(),geom.height()],
                    screen=screen.name() if screen else None,dpr=w.devicePixelRatioF(),
                    exposed_at_end=bool(w.windowHandle() and w.windowHandle().isExposed()),
                    plot_width=view.width(),plotted_points=len(w.line_items['CH1'].getData()[0]),
                    events=events)
        out=ROOT/'diagnosticos/resultados_v20/rf40k_comparison_20261103'
        out.mkdir(parents=True,exist_ok=True)
        path=out/f'archive_{args.version}_w9000_ch1.json'
        path.write_text(json.dumps(result,indent=2)+'\n')
        print(path,flush=True)
        print('paint_events',sum(e['kind']=='paint_event' for e in events),
              'fresh',sum(e['kind']=='paint_event' and e['fresh'] for e in events),flush=True)
    finally:w.close();app.processEvents()


if __name__=='__main__':main()
