import os,sys,time,json,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
from tests.v20.test_reduced_square_gaps import display
from monitor.v20.app import SerialMonitorWindow as W
from monitor.v20.history import SampleHistory
tree=ast.parse((ROOT/'monitor/v19/app.py').read_text())
method=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='SerialMonitorWindow'
            for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='_display_trace')
ns={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<V19-display-trace-read-only>','exec'),ns)
rows=[]
for count in (9000,80000):
 h=SampleHistory(count);h.extend(np.where(np.arange(count)%20<10,1.,-1.))
 indices=W._history_window_extrema_indices(h,0,count,400)
 x=indices*25.;y=W._history_values_at(h,0,indices);w=display()
 for label,fn in [('V19',lambda:ns['_display_trace'](w,x,y,0,(count-1)*25.,400)),
                  ('before',lambda:W._display_trace(w,x,y,0,(count-1)*25.,400)),
                  ('after',lambda:W._display_trace(w,x,y,0,(count-1)*25.,400,known_continuous=True))]:
  durations=[]
  for _ in range(30):
   began=time.perf_counter();xp,yp=fn();durations.append((time.perf_counter()-began)*1000)
  rows.append(dict(count=count,pixels=400,mode=label,input_vertices=len(x),
                   false_nan_vertices=int(np.isnan(yp).sum()),output_vertices=len(yp),
                   median_ms=float(np.median(durations)),max_ms=max(durations)))
p=Path(__file__).with_name('report.json');p.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
