"""Controlled offline mixed-render comparison against the pre-optimization reference."""
import os;os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,inspect,textwrap,time,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from tests.v17.test_radio_ui import RadioTests
from monitor.v17.app import SerialMonitorWindow
import monitor.v17.app as module
source=textwrap.dedent(inspect.getsource(SerialMonitorWindow._render_mixed_temporal))
a=source.index('\n            if len(crosses):')+1;b=source.index('\n        if trigger_time is None',a)+1
source=source[:a]+'''            for i in crosses[::-1]:
                fraction=(level-values[i-1])/(values[i]-values[i-1])
                crossing=times[i-1]+fraction*(times[i]-times[i-1])
                if common_start+pre<=crossing<=common_end-post:
                    prior=values[max(0,i-10):i]
                    if (np.min(prior)<=level-.015 if rising else np.max(prior)>=level+.015):
                        trigger_time=float(crossing);left=trigger_time-pre;right=trigger_time+post;break
'''+source[b:]
a=source.index('    x_values={};');b=source.index('    if self.selection_dirty',a)
source=source[:a]+'''    x_values={};y_values={};measurement=None
    for name,(histories,rate) in domains.items():
        clock=histories.get('Tiempo (us)');history=histories.get(name)
        if clock is None or history is None or len(clock)!=len(history):continue
        count=min(len(clock),int(max(0,float(clock[-1])-left)*rate/1e6)+4)
        times=clock.window(len(clock)-count,len(clock))
        a,b=np.searchsorted(times,(left,right),side='left')
        if b<len(times) and times[b]<=right:b+=1
        values=history.window(len(history)-count+int(a),len(history)-count+int(b))
        selected=times[a:b]
        x_values[name]=(selected-origin)*factor;y_values[name]=values
        if name==self.active_meas_channel:measurement=(values,selected,rate)
'''+source[b:]
namespace=dict(vars(module));exec(source,namespace);old=namespace['_render_mixed_temporal'];new=SerialMonitorWindow._render_mixed_temporal
RadioTests.setUpClass();test=RadioTests();test.setUp();test.mixed_history();w=test.w
report={'reference_sha256':hashlib.sha256(source.encode()).hexdigest(),'source_sha256':hashlib.sha256(inspect.getsource(new).encode()).hexdigest(),'scope':'Same fixed synthetic histories, alternating render calls, offscreen; reconstructed previous mixed renderer only. No physical FPS.','cases':{}}
channels=['CH1','RADIO','FILTER'];audio_names={'RADIO','FILTER'}
for case in ('AM_trigger','old_position','noise_outlier'):
 w.h_pos=0;w.trigger_enabled=case!='old_position';w.trigger_source='RADIO';w.trigger_level=1.65
 if case=='old_position':w.h_pos=-int(w.applied_configuration.actual_rate*.04)
 if case=='noise_outlier':
  h=w.radio_stream.series['RADIO'];h.clear();values=1.65+1e-6*np.sin(np.arange(w.radio_stream.counter));values[10]=1.6;h.extend(values)
 timings={'old':[],'new':[]}
 for j in range(80):
  frames=[]
  for name,fn in (('old',old),('new',new)) if j%2==0 else (('new',new),('old',old)):
   start=time.perf_counter();fn(w,channels,audio_names);timings[name].append((time.perf_counter()-start)*1000)
   frames.append(({k:v.copy() for k,v in w._last_display_frame[0].items()},{k:v.copy() for k,v in w._last_display_frame[1].items()}))
  for domain in (0,1):
   for key in frames[0][domain]:np.testing.assert_array_equal(frames[0][domain][key],frames[1][domain][key])
 report['cases'][case]={k:{'median_ms':float(np.median(v[5:])),'p95_ms':float(np.percentile(v[5:],95))} for k,v in timings.items()}
test.tearDown();(ROOT/'diagnosticos/resultados_v17/mixed_render_controlled_20261014.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
