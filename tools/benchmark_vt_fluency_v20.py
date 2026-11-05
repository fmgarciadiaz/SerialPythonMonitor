"""Native Qt A/B for temporal rendering only; synthetic histories, never opens Q."""
import ast,json,resource,sys,time,types
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtCore,QtWidgets
from monitor.v20 import app as mod
from monitor.v20.history import SampleHistory
from monitor.v20.receiver.unoq_acquisition import Configuration


def main():
    qt=QtWidgets.QApplication([])
    with patch.object(mod,'usb_devices',return_value=[]):w=mod.SerialMonitorWindow()
    w.render_timer.stop();w.resize(1280,800);w.setWindowTitle('Prueba local FPS · sin conexión al Q')
    w.show();qt.processEvents()
    source=ROOT/'respaldos/host/v20_before_vt_fluency_20261104/app.py'
    tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SerialMonitorWindow')
    old=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_refresh_render_cadence')
    namespace=dict(mod.__dict__);exec(compile(ast.Module(body=[old],type_ignores=[]),str(source),'exec'),namespace)
    from monitor.v20.temporal_paint import visual_interval
    namespace['balanced_visual_interval']=lambda paint,prepare:min(500,max(34,__import__('math').ceil((paint+prepare)/.60)))
    old_policy=namespace['_refresh_render_cadence'];new_policy=mod.SerialMonitorWindow._refresh_render_cadence
    original_paint=w.plot_widget.paint_observer;original_render=w._render_with_diagnostics
    w.render_timer.timeout.disconnect(original_render)
    state={'row':None,'prepared':None,'painted':None,'epoch':0,'last_feed':0.}
    rows=[]
    def paint(ms):
        original_paint(ms);r=state['row']
        if r is None:return
        r['paint_ms'].append(ms)
        if state['prepared'] is not None and state['prepared']!=state['painted']:
            r['fresh_frames']+=1;state['painted']=state['prepared']
        r['exposure'].append(bool(w.windowHandle().isExposed()))
    def render():
        if state['row'] is not None:state['row']['exposure'].append(bool(w.windowHandle().isExposed()))
        t=time.perf_counter();original_render()
        if state['row'] is not None:state['row']['render_ms'].append((time.perf_counter()-t)*1000)
        state['prepared']=w.sample_counter
    w.plot_widget.paint_observer=paint;w.render_timer.timeout.connect(render)
    feed=QtCore.QTimer();feed.setInterval(10);feed.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    rate=40000
    def advance():
        now=time.perf_counter();count=max(0,int((now-state['last_feed'])*rate))
        state['last_feed']+=count/rate
        if not count:return
        indices=np.arange(state['epoch'],state['epoch']+count,dtype=float)
        state['epoch']+=count;w.sample_counter=state['epoch']
        w.sample_numbers.extend(indices);w.series['Tiempo (us)'].extend(indices*(1e6/rate))
        w.series['CH1'].extend(1.65+.7*np.sin(indices*(2*np.pi*2000/rate)))
        if rate==40000:w.series['CH2'].extend(1.65+.5*np.sin(indices*.1))
    feed.timeout.connect(advance)
    try:
        cases=(((2000000,4000000),) if '--high-only' in sys.argv else
               ((40000,80000),) if '--low80k-only' in sys.argv else
               ((40000,9000),(40000,80000),(2000000,9000),(2000000,4000000)))
        for rate,n in cases:
            for candidate in (False,True,True,False):
                w.render_timer.stop();feed.stop();state['row']=None
                w._refresh_render_cadence=types.MethodType(new_policy if candidate else old_policy,w)
                for name in ('bottom','left'):
                    axis=w.plot_widget.getAxis(name);axis.cache_static_paint=candidate;axis._static_axis_cache=None
                w.applied_configuration=Configuration(14 if rate==40000 else 8,rate)
                w.current_dt_us=1e6/rate;w.current_fs_hz=rate
                w.h_scale=n;w.h_pos=0;w._h_time_ms=n/rate*1000;w._horizontal_display_dt=round(1e6/rate,6)
                w.x_axis_time_mode=True
                w.selected_columns={k:k in ('CH1','CH2') if rate==40000 else k=='CH1' for k in w.known_columns}
                w.selection_dirty=True;w.trigger_enabled=False;w.is_running=True;w.detail_slider.setValue(50)
                w.sample_numbers=SampleHistory(n);w.sample_numbers.extend(np.arange(n));w.sample_counter=n
                for key,v in [('Tiempo (us)',np.arange(n)*(1e6/rate)),('CH1',1.65+.7*np.sin(np.arange(n)*(2*np.pi*2000/rate))),('CH2',np.ones(n)*1.65)]:
                    w.series[key]=SampleHistory(n);w.series[key].extend(v)
                state.update(epoch=n,last_feed=time.perf_counter(),prepared=None,painted=None)
                w.raise_();w.activateWindow();qt.processEvents()
                w._temporal_paint_ms=w._temporal_prepare_ms=0.;w._refresh_render_cadence()
                w.render_timer.start();feed.start()
                warm=QtCore.QEventLoop();QtCore.QTimer.singleShot(700,warm.quit);warm.exec()
                r=dict(rate=rate,window=n,candidate=candidate,fresh_frames=0,paint_ms=[],render_ms=[],exposure=[])
                state.update(row=r,prepared=None,painted=None)
                start=time.perf_counter();usage=resource.getrusage(resource.RUSAGE_SELF);cpu=usage.ru_utime+usage.ru_stime
                loop=QtCore.QEventLoop();QtCore.QTimer.singleShot(3000,loop.quit);loop.exec()
                elapsed=time.perf_counter()-start;usage=resource.getrusage(resource.RUSAGE_SELF)
                state['row']=None;feed.stop();w.render_timer.stop()
                r.update(seconds=elapsed,fps=r['fresh_frames']/elapsed,cpu_seconds=usage.ru_utime+usage.ru_stime-cpu,
                         interval_ms=w.render_timer.interval(),actual_window=w.h_scale,
                         paint_median_ms=float(np.median(r['paint_ms'])),render_median_ms=float(np.median(r['render_ms'])))
                rows.append(r);print(json.dumps({k:v for k,v in r.items() if k not in ('paint_ms','render_ms','exposure')}),flush=True)
        filename=('native_ab_high.json' if '--high-only' in sys.argv else
                  'native_ab_low80k.json' if '--low80k-only' in sys.argv else 'native_ab.json')
        out=ROOT/'diagnosticos/resultados_v20/vt_fluency_20261104'/filename
        out.write_text(json.dumps(dict(scope='Native Qt; synthetic continuous histories fed at nominal rate, no Q/decoder/DSP transport',rows=rows),indent=2))
    finally:feed.stop();w.close();qt.processEvents()


if __name__=='__main__':main()
