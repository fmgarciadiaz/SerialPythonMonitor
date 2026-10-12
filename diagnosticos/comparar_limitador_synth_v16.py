"""Comparación host del compresor anterior y la protección de picos actual."""
import importlib.util,sys,json,argparse
from pathlib import Path
from dataclasses import replace
import numpy as np
from diagnosticos.synth_presets_v16 import panel_presets
from monitor.v16.fm_source import FMSource
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',default='respaldos/synth/20261010_output_limiter/fm_source.py')
parser.add_argument('--output',default='diagnosticos/resultados_piano/eficiencia_v16/20261010_output_limiter_comparison.json')
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('output_baseline',Path(args.baseline))
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
rows=[]
for name,p in panel_presets(['Piano Virtual','Guitarra','Brass','DX Piano']).items():
 for count in (1,4,11):
  notes=tuple((n,127) for n in (36,40,43,48,52,55,60,64,67,72,76)[:count])
  for vol in (1.,2.5,3.3):
   row=dict(preset=name,voices=count,vol=vol)
   for label,cls,params in [('before',m.FMSource,m.FMParameters(**p.__dict__)),('after',FMSource,p)]:
    src=cls(20000,replace(params,notes=notes,gate=True));src.diagnostic_path=Path('/tmp/unused_sound_metrics')
    peak=0
    for i in range(60):
     codes=src.render_dac_codes(i*480,(i+1)*480,vol,1.65)
     peak=max(peak,float(np.max(np.abs(codes.astype(float)*3.3/4095-1.65))))
    row[label]=dict(limited_samples=src.soft_limited_samples,min_gain=src.min_compressor_gain,max_raw_peak=src.max_ac_peak_v,output_peak=peak)
   rows.append(row)
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
