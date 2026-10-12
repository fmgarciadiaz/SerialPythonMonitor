"""Offline A/B and render timing; an explicit previous-model snapshot is optional."""
import argparse
from contextlib import nullcontext
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import numpy as np
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.historico.v15.fm_source import FMSource,FMParameters
import monitor.historico.v15.virtual_instruments as physics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-model',type=Path)
    args=parser.parse_args()
    old=None
    if args.before_model:
        spec=importlib.util.spec_from_file_location('piano_before_model',args.before_model)
        old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        class BeforePiano(old.PianoStrings):
            def __init__(self,rate,frequency,position=.12,velocity=1.,bandlimit=None,calibrated=False):
                super().__init__(rate,frequency,position,velocity,bandlimit)
            def render(self,count,brightness=.75,decay=4.,stiffness=.0003,bridge=.2,damper_t60=0):
                return super().render(count,brightness,decay,stiffness,bridge)
        old.warmup()
    physics.warmup()
    folder=ROOT/'diagnosticos/resultados_piano';folder.mkdir(exist_ok=True)
    params=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                        envelope=(.001,.01,1,.22),string_position=.12,string_brightness=.78,
                        string_decay=4,body_mix=.45,notes=((60,110),))
    result={'hardware':False,'buffer_changed':False,
            'baseline':'Explicit previous model, x4 gain, oversampled route','cases':[]}
    for before in ((True,False) if old else (False,)):
        model=patch.multiple(physics,PianoStrings=BeforePiano,InstrumentBody=old.InstrumentBody) if before else nullcontext()
        route=patch('monitor.historico.v15.fm_source._pure_piano',return_value=False) if before else nullcontext()
        with model,route:
            for rate in (20000,40000):
                for voices in (1,9):
                    source=FMSource(rate,replace(params,notes=tuple((n,100) for n in range(48,48+voices))))
                    times=[];parts=[]
                    for at in range(0,rate*3,480):
                        began=time.perf_counter()
                        codes=source.render_dac_codes(at,at+480,np.full(480,2.5),np.full(480,1.65))
                        times.append((time.perf_counter()-began)*1000);parts.append(codes)
                    row=dict(before=before,rate=rate,voices=voices,total_render_ms=sum(times),
                             first_ms=times[0],steady_p95_ms=float(np.percentile(times[1:],95)),max_ms=max(times))
                    result['cases'].append(row);print(row,flush=True)
                    if rate==20000 and voices==1:
                        audio=np.clip((np.concatenate(parts).astype(float)/4095-.5)*2,-1,1)
                        wavfile.write(folder/('piano_antes.wav' if before else 'piano_nuevo.wav'),
                                      rate,np.rint(audio*32767).astype('int16'))
    (folder/'20261008_motor.json').write_text(json.dumps(result,indent=2)+'\n')
    if old:
        files=[folder/'piano_antes.wav',folder/'piano_nuevo.wav']
        audio=[wavfile.read(path)[1].astype(float)/32768 for path in files]
        rms=[np.sqrt(np.mean(x*x)) for x in audio]
        target=min(rms)
        for path,x,level in zip(files,audio,rms):
            wavfile.write(path.with_stem(path.stem+'_igualado'),20000,
                          np.rint(x*(target/max(level,1e-12))*32767).astype('int16'))


if __name__=='__main__':
    main()
