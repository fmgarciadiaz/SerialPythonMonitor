"""Offline release-resonance identification from pinned CC-BY piano samples.

No board I/O or sample playback in Synth. Reports are written locally;
--apply updates only the small V16 parameter JSON. Requires ffmpeg.
"""
import argparse
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.signal import stft

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v16 import piano_calibration as calibration
from monitor.v16.fm_source import FMSource,FMParameters
from monitor.v16.virtual_instruments import warmup

SAMPLES=ROOT/'diagnosticos/referencias_piano/liberacion'
RATE=20000

def recording(path):
    result=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-ac','1',
        '-ar',str(RATE),'-f','f64le','pipe:1'],capture_output=True,check=True)
    return np.frombuffer(result.stdout,dtype='<f8')

def identify(note,octave):
    fits=[]
    for layer in ('harmL','harmS','harmV3'):
        name=f'{layer}C{octave}.flac'
        f,t,z=stft(recording(SAMPLES/name),RATE,nperseg=2048,noverlap=1792,boundary=None)
        for order in (1,2):
            frequency=440*2**((note-69)/12)*order
            power=np.sum(abs(z[abs(f-frequency)<25])**2,axis=0)
            db=10*np.log10(power+1e-20);peak=int(np.argmax(power))
            floor=np.median(db[-max(5,len(db)//8):])
            use=(np.arange(len(t))>peak)&(t<t[peak]+.8)&(db>floor+8)&(db>db[peak]-35)
            if use.sum()<6:continue
            slope,intercept=np.polyfit(t[use],db[use],1)
            prediction=slope*t[use]+intercept
            r2=1-np.sum((db[use]-prediction)**2)/max(np.sum((db[use]-db[use].mean())**2),1e-12)
            if slope<-3 and r2>.55:
                fits.append(dict(file=name,order=order,t60=float(-60/slope),r2=float(r2),points=int(use.sum())))
    if not fits:raise ValueError(f'No usable decay fits for MIDI {note}')
    return dict(note=note,fits=fits,t60_seconds=float(np.clip(np.median([f['t60'] for f in fits]),.3,2.5)))

def level(note,octave,t60):
    velocity=60/127;rt=8 if note==48 else 9
    long=recording(SAMPLES/f'harmLC{octave}.flac')[:4000]
    extra=recording(SAMPLES/f'harmV3C{octave}.flac')[:4000]
    held=recording(SAMPLES.parent/f'C{octave}v8.flac')[8000:10000]
    target=long*10**(-4/20)*velocity**.9*10**(-rt*.5/20)+extra*velocity**.96*10**(-2*.5/20)
    rms=lambda x:np.sqrt(np.mean(x*x))
    ratio=rms(target)/rms(held)
    parameters=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
        carrier=440*2**((note-69)/12),level=velocity,envelope=(.001,.01,1,.55),
        string_position=.12,string_brightness=.78,string_decay=4,body_mix=.45,bridge_coupling=.2)
    original=calibration.modal_correction
    def render(mix):
        def correction(f,v):
            c=dict(original(f,v));c['release_t60']=t60;c['release_tail_mix']=mix
            return c
        with patch.object(calibration,'modal_correction',side_effect=correction):
            source=FMSource(RATE,parameters)
            before=source._render(slice(0,10000),quantize=False)
            source.update(replace(parameters,gate=False))
            return before,source._render(slice(10000,14000),quantize=False)
    before,old=render(0);_,new=render(.65)
    modelratio=rms(new-old)/rms(before[8000:10000])
    return dict(note=note,reference_release_to_held_rms=float(ratio),
        model_release_to_held_rms_before=float(modelratio),
        release_tail_mix=float(np.clip(.65*ratio/max(modelratio,1e-12),.1,32)))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();warmup()
    decays=[identify(n,o) for n,o in ((48,3),(60,4),(72,5))]
    levels=[level(row['note'],row['note']//12-1,row['t60_seconds']) for row in decays]
    for name,rows in (('ajuste_modal',decays),('ajuste_nivel',levels)):
        (SAMPLES/(name+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
    if args.apply:
        data=json.loads(calibration.DATA.read_text())
        for row in data['profiles']:
            row['release_t60']=next(r['t60_seconds'] for r in decays if r['note']==row['note'])
            row['release_tail_mix']=next(r['release_tail_mix'] for r in levels if r['note']==row['note'])
        calibration.DATA.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(decays=decays,levels=levels),indent=2))

if __name__=='__main__':main()
