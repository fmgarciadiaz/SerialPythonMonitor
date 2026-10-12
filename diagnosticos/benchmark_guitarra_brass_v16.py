"""ABBA complete DAC comparison; supply saved pre-change source/string files."""
import sys,json,argparse,importlib.util
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from monitor.v16 import fm_source,virtual_string
from diagnosticos.synth_presets_v16 import panel_presets
from diagnosticos.benchmark_cache_instrumentos_v16 import render

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('string',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    old=load('guitar_brass_reference',args.source);old_string=load('string_reference',args.string);cases=[]
    for rate in (20000,40000):
        for name,p in panel_presets(('Guitarra','Brass','Lead','Bass Punch','Warm Pad'),rate).items():
            timings={'before':[],'after':[]};expected=None
            for variant in ('before','after','after','before'):
                module=old if variant=='before' else fm_source
                string=old_string.PluckedString if variant=='before' else virtual_string.PluckedString
                with patch.object(virtual_string,'PluckedString',string):
                    render(module,p,rate,2);codes,metrics=render(module,p,rate,240)
                if expected is None:expected=codes
                else:np.testing.assert_array_equal(codes,expected)
                timings[variant].append(metrics)
            cases.append(dict(preset=name,rate=rate,samples=len(expected),exact=True,**{key:dict(median_ms=float(np.median([v['median_ms'] for v in values])),p95_ms=float(np.median([v['p95_ms'] for v in values]))) for key,values in timings.items()}))
    args.output.write_text(json.dumps(dict(scope='Host warmed ABBA; exact DAC, not acoustic/GUI latency',cases=cases),indent=2)+'\n');print(args.output)
if __name__=='__main__':main()
