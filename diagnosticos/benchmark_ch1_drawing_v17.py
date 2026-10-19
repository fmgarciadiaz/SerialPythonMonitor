"""Controlled CH1 temporal drawing comparison; synthetic data, no Q access."""
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
    args=parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    import numpy as np
    from unittest.mock import patch
    from PyQt6 import QtWidgets
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
    w.render_timer.stop();w._acquisition_confirmed(8,1403508)
    w.resize(1320,860);w.show();app.processEvents();c=w.applied_configuration
    n=250000;i=np.arange(n)
    raw=np.column_stack(((i*c.period)%2**32,
        127.5+100*np.sin(2*np.pi*5000*i/c.actual_rate),np.zeros(n),i))
    w.handle_batch(NumericBatch(raw,c.maximum,SampleClock(c.timestamp_hz),1))
    for name,action in w.graph_channel_actions.items():action.setChecked(name=='CH1')
    w._calculate_sample_rate();w.trigger_level=1.65
    report={'scope':'Fixed synthetic CH1 ADC8/1.4035MHz. Alternating paired render + QWidget.grab; includes grab overhead, not live or visible FPS.',
            'qt_platform':app.platformName(),'pairs':40,'warmup_pairs':5,
            'warmup_render_per_sample':1,
            'comparison':'reducer' if args.before_reducer else 'render',
            'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(inspect.getsource(new).encode()).hexdigest(),
            'app_file_sha256':hashlib.sha256((ROOT/'monitor/v17/app.py').read_bytes()).hexdigest(),
            'cases':[]}
    try:
        for triggered in (False,True):
            for scale in (1404,14035,140351):
                times={key:[] for key in ('before_prepare','after_prepare','before_raster','after_raster')}
                w.trigger_enabled=triggered
                # Fixed old position removes roll-clock motion from the comparison.
                for pair in range(40):
                    frames=[]
                    order=(('before',old),('after',new))
                    for name,fn in order if pair%2==0 else reversed(order):
                        if args.before_reducer:
                            module.SerialMonitorWindow._reduce_trace_for_display=staticmethod(
                                before_reducer if name=='before' else after_reducer)
                        w.h_scale=scale;w.h_pos=-100;w.x_axis_time_mode=True
                        # Warm each implementation's layout/cache after switching.
                        # The old renderer reinstalls style/label every call.
                        fn(w);w.plot_widget.grab()
                        w.h_scale=scale
                        start=time.perf_counter_ns();fn(w)
                        times[name+'_prepare'].append((time.perf_counter_ns()-start)/1e6)
                        frame=w._last_display_frame
                        frames.append((frame[0].copy(),{k:v.copy() for k,v in frame[1].items()}))
                        start=time.perf_counter_ns();w.plot_widget.grab()
                        times[name+'_raster'].append((time.perf_counter_ns()-start)/1e6)
                    np.testing.assert_array_equal(frames[0][0],frames[1][0])
                    for channel in frames[0][1]:
                        np.testing.assert_array_equal(frames[0][1][channel],frames[1][1][channel])
                report['cases'].append({'trigger':triggered,'samples':scale,
                    'detail':w.detail_slider.value(),
                    'times':{key:{'median_ms':float(np.median(values[5:])),
                                  'p95_ms':float(np.percentile(values[5:],95))}
                             for key,values in times.items()}})
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        module.SerialMonitorWindow._reduce_trace_for_display=staticmethod(after_reducer)
        w.close()


if __name__=='__main__':main()
