"""Comparación ABBA de la radiación de guitarra; no accede al Q."""
import importlib.util,sys,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from monitor.historico.v16 import fm_source,virtual_instruments as vi
from diagnosticos.synth_presets_v16 import panel_presets
from diagnosticos.benchmark_cache_instrumentos_v16 import render
spec=importlib.util.spec_from_file_location('old_radiation',Path('respaldos/synth/20261010_guitar_radiation/virtual_instruments.py'))
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
vi.warmup();rows=[]
for rate in (20000,40000):
 p=panel_presets(['Guitarra'],rate)['Guitarra'];reference=None;times={'before':[],'after':[]}
 for variant in ('before','after','after','before'):
  cls=old.GuitarStrings if variant=='before' else vi.GuitarStrings
  with patch.object(vi,'GuitarStrings',cls):
   render(fm_source,p,rate,2);codes,metrics=render(fm_source,p,rate,600)
  if reference is None:reference=codes
  else:np.testing.assert_array_equal(codes,reference)
  times[variant].append(metrics)
 rows.append(dict(rate=rate,samples=len(reference),exact=True,timings=times))
print(json.dumps(rows,indent=2))
Path('diagnosticos/resultados_piano/eficiencia_v16/20261010_guitar_radiation.json').write_text(json.dumps(rows,indent=2))
