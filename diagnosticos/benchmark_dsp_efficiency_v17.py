"""Interleaved offline DSP costs against explicitly supplied source snapshots.

No Qt, board access or physical acceptance. The source snapshots and hashes
identify the comparison; timing excludes construction and the warm-up blocks.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import scipy
from monitor.v17 import radio_stream, spectral_analysis
from monitor.v17.radio_am import RadioConfig


def load_snapshot(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def summarize(values):
    return {'mean_ms':float(np.mean(values)), 'p50_ms':float(np.median(values)),
            'p95_ms':float(np.percentile(values,95)), 'max_ms':float(np.max(values))}


def compare(functions,blocks):
    costs = {name:[] for name in functions}
    outputs = {name:[] for name in functions}
    for index,block in enumerate(blocks):
        order = list(functions) if index%2 else list(reversed(functions))
        for name in order:
            start = time.perf_counter()
            result = functions[name](block)
            elapsed = (time.perf_counter()-start)*1000
            outputs[name].append(result)
            if index>=10: costs[name].append(elapsed)
    return {name:summarize(values) for name,values in costs.items()}, outputs


def allocation_peak(function,values):
    tracemalloc.start()
    function(values)
    _,peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-radio',type=Path,required=True)
    parser.add_argument('--before-spectral',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    before_radio = load_snapshot('v17_benchmark_before_radio',args.before_radio)
    before_spectral = load_snapshot('v17_benchmark_before_spectral',args.before_spectral)
    source_paths = [args.before_radio,args.before_spectral,Path(radio_stream.__file__),Path(spectral_analysis.__file__)]
    report = {'scope':'Offline interleaved DSP timing; no ADC/transport/visible FPS or physical margin acceptance',
              'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
              'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
              'resampler':{},'radio_plus_resampler':{},'fft':{}}
    rng = np.random.default_rng(814)
    rate = 160000000/114
    for output_rate in (20000,40000,48000):
        for count in (108,877):
            blocks = [rng.normal(size=count) for _ in range(210)]
            objects = {'before':before_radio.AudioResampler(rate/32,output_rate),
                       'after':radio_stream.AudioResampler(rate/32,output_rate)}
            timing,outputs = compare({name:obj.process for name,obj in objects.items()},blocks)
            timing['block_duration_ms'] = 1000*count/(rate/32)
            timing['max_output_difference'] = float(np.max(abs(np.concatenate(outputs['before'])-np.concatenate(outputs['after']))))
            timing['peak_allocation_bytes'] = {name:allocation_peak(obj.process,blocks[-1]) for name,obj in objects.items()}
            report['resampler'][f'{output_rate}Hz_{count}samples'] = timing
        count = round(rate*.02)
        indices = np.arange(count)
        blocks = []
        for index in range(110):
            t = (indices+index*count)/rate
            blocks.append(1.65+(.5+.25*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*20525*t))
        objects = {'before':before_radio.RadioStream(RadioConfig(rate,20525),output_rate),
                   'after':radio_stream.RadioStream(RadioConfig(rate,20525),output_rate)}
        timing,outputs = compare({name:obj.process for name,obj in objects.items()},blocks)
        timing['max_output_difference'] = float(np.max(abs(np.concatenate(outputs['before'])-np.concatenate(outputs['after']))))
        report['radio_plus_resampler'][str(output_rate)] = timing
    for n in (1024,8192,65536):
        for kind in ('noise','tone'):
            count = n+3*(n//2)
            values = rng.normal(size=count) if kind=='noise' else np.sin(2*np.pi*1025*np.arange(count)/40000)
            functions = {name:(lambda x,module=module:module.analyze(x,40000,n,maximum=4))
                         for name,module in [('before',before_spectral),('after',spectral_analysis)]}
            timing,outputs = compare(functions,[values]*70)
            before,after = outputs['before'][-1],outputs['after'][-1]
            timing['amplitude_max_error'] = float(np.max(abs(before.amplitude-after.amplitude)))
            timing['psd_max_error'] = float(np.max(abs(before.psd-after.psd)))
            timing['peak_bins_equal'] = [p['bin'] for p in before.peaks]==[p['bin'] for p in after.peaks]
            timing['peak_allocation_bytes'] = {name:allocation_peak(fn,values) for name,fn in functions.items()}
            report['fft'][f'{n}_{kind}'] = timing
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
