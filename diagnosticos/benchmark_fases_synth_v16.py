"""Comparación ABBA de caché de fases, muestras DAC y tiempos host; sin Q."""
import importlib.util,sys,json
from pathlib import Path
import numpy as np
from monitor.v16 import fm_source
from diagnosticos.synth_presets_v16 import panel_presets
from diagnosticos.benchmark_cache_instrumentos_v16 import render

def main():
    spec=importlib.util.spec_from_file_location('phase_reference',Path('respaldos/synth/20261010_phase_cache/fm_source.py'))
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    rows=[]
    for rate in (20000,40000):
        for name,p in panel_presets(['DX Piano','Guitarra','Brass','Piano Virtual'],rate).items():
            reference=None;times={'before':[],'after':[]}
            for variant in ('before','after','after','before'):
                module=old if variant=='before' else fm_source
                render(module,p,rate,2);codes,metrics=render(module,p,rate,300)
                if reference is None:reference=codes
                else:np.testing.assert_array_equal(codes,reference)
                times[variant].append(metrics)
            rows.append(dict(preset=name,rate=rate,samples=len(reference),exact=True,timings=times))
    output=Path('diagnosticos/resultados_piano/eficiencia_v16/20261010_phase_cache_abba.json')
    output.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
