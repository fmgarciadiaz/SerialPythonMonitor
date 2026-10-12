"""Identify modal color/losses against CC-BY Salamander references, offline.

Requires ffmpeg only for this diagnostic, not for Synth playback. No board I/O.
The fitted corrections are acoustic, not uniquely identified mechanical data.
"""
import json
import copy
import hashlib
import subprocess
import sys
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft,resample_poly
from scipy.optimize import least_squares
from scipy.ndimage import uniform_filter1d

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.historico.v15.fm_source import FMSource,FMParameters
from monitor.historico.v15.virtual_instruments import warmup
from monitor.historico.v15.piano_profile import piano_profile
from monitor.historico.v15 import piano_calibration as calibration

RATE=20000
SECONDS=4
PARTIALS=32
REFERENCES=((48,60,'C3v8'),(60,60,'C4v8'),(72,60,'C5v8'),
            (60,40,'C4v4'),(60,92,'C4v12'))
FOLDER=ROOT/'diagnosticos/resultados_piano/identificacion'

def recording(name):
    path=ROOT/'diagnosticos/referencias_piano'/(name+'.flac')
    result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),
                           '-ac','1','-ar',str(RATE),'-f','f64le','pipe:1'],
                          capture_output=True,check=True)
    return np.frombuffer(result.stdout,dtype='<f8').copy()

def identify_pitch(audio,nominal):
    segment=audio[round(.1*RATE):round(2.5*RATE)]
    size=2**19
    power=abs(np.fft.rfft(segment*np.hanning(len(segment)),n=size))
    frequencies=np.fft.rfftfreq(size,1/RATE)
    def peak(center,width):
        mask=np.flatnonzero(abs(frequencies-center)<width)
        return frequencies[mask[np.argmax(power[mask])]]
    fundamental=peak(nominal,nominal*.015)
    n=np.arange(1,9,dtype=float)
    peaks=np.array([peak(fundamental*k,min(fundamental*.38,fundamental*k*.025)) for k in n])
    fit=least_squares(lambda x:(x[0]*n*np.sqrt((1+x[1]*n*n)/(1+x[1]))-peaks)/n,
                      [fundamental,.00015],bounds=([fundamental*.99,1e-7],[fundamental*1.01,.01]))
    return float(fit.x[0]),float(fit.x[1])

def prepare(name,note):
    raw=recording(name)
    # Detect actual onset; the distributed recordings contain a lead-in.
    envelope=np.convolve(abs(raw),np.ones(40)/40,mode='same')
    onset=int(np.flatnonzero(envelope>envelope.max()*.01)[0])
    raw=raw[max(0,onset-20):]
    nominal=440*2**((note-69)/12)
    fundamental,b=identify_pitch(raw,nominal)
    ratio=Fraction(fundamental/nominal).limit_denominator(10000)
    audio=resample_poly(raw,ratio.numerator,ratio.denominator)
    audio=np.pad(audio,(0,max(0,RATE*SECONDS-len(audio))))[:RATE*SECONDS]
    return audio,b,dict(onset_seconds=onset/RATE,original_fundamental=fundamental,
                        nominal=nominal,stiffness=b,pitch_normalization=fundamental/nominal)

def features(audio,note,b):
    f,t,z=stft(audio,RATE,nperseg=8192,noverlap=7168,boundary=None)
    fundamental=440*2**((note-69)/12)
    orders=np.arange(1,PARTIALS+1)
    centers=fundamental*orders*np.sqrt((1+b*orders*orders)/(1+b))
    powers=[]
    for center in centers:
        mask=abs(f-center)<min(fundamental*.3,max(12,center*.006))
        powers.append(np.sum(abs(z[mask])**2,axis=0))
    power=np.asarray(powers)
    amplitude=np.sqrt(np.mean(power[:,(t>=.2)&(t<=1.1)],axis=1)+1e-20)
    slopes=[]
    for row in power:
        use=(t>=.35)&(t<=3)&(row>max(row.max()*1e-4,1e-18))
        slope=np.polyfit(t[use],10*np.log10(row[use]),1)[0] if use.sum()>3 else -60
        slopes.append(slope)
    return amplitude,np.asarray(slopes)

def render(note,velocity,calibrated):
    parameters=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',
                           carrier=440*2**((note-69)/12),level=velocity/127,
                           envelope=(.001,.01,1,.22),string_position=.12,string_brightness=.78,
                           string_decay=4,body_mix=.45,bridge_coupling=.2)
    context=patch.object(calibration,'modal_correction',return_value=None) if not calibrated else patch.object(calibration,'DATA',calibration.DATA)
    with context:
        source=FMSource(RATE,parameters)
        return np.concatenate([source._render(slice(at,at+480),quantize=False,native=True)
                               for at in range(0,RATE*SECONDS,480)])[:RATE*SECONDS]

def error(reference,model,note,b):
    a,s=features(reference,note,b);m,ms=features(model,note,b)
    active=a>a.max()*.003
    delta=20*np.log10(np.maximum(m,1e-12)/np.maximum(a,1e-12))
    delta-=np.median(delta[active])
    # Spectral shape, independent of gain; compare losses separately.
    return dict(partial_shape_db=float(np.mean(abs(delta[active]))),
                decay_slope_db_s=float(np.mean(abs(ms[active]-s[active]))))

def envelope_error(reference,model,start,stop):
    def envelope(x):
        x=x/max(np.sqrt(np.mean(x*x)),1e-12)
        return 20*np.log10(np.maximum(np.sqrt(uniform_filter1d(x*x,size=200)),1e-5))
    a=envelope(reference);b=envelope(model)
    return float(np.mean(abs(a[round(start*RATE):round(stop*RATE)]-b[round(start*RATE):round(stop*RATE)])))

def write_audio(path,audio,target):
    rms=np.sqrt(np.mean(audio**2))
    result=audio*target/max(rms,1e-12)
    # Same target RMS for A/B; do not hide clipping by independent peak scaling.
    if max(abs(result))>1:raise ValueError('Comparison clips; lower target RMS')
    wavfile.write(path,RATE,np.rint(result*32767).astype('<i2'))

def main():
    FOLDER.mkdir(parents=True,exist_ok=True)
    warmup()
    profiles=[];references={};before={};metadata={}
    for note,velocity,name in REFERENCES:
        audio,b,info=prepare(name,note)
        references[name]=audio;metadata[name]=info
        before[name]=render(note,velocity,False)
        profiles.append(dict(note=note,velocity=velocity/127,gain=[1.]*PARTIALS,
                             decay=[1.]*PARTIALS,
                             stiffness_scale=b/piano_profile(info['nominal'])['stiffness']))
    dataset=dict(schema=1,source='Alexander Holm, Salamander Grand Piano V3, CC BY 3.0',
                 license_url='https://creativecommons.org/licenses/by/3.0/',
                 source_repository='https://github.com/sfzinstruments/SalamanderGrandPiano',
                 source_commit=json.loads((ROOT/'diagnosticos/referencias_piano/procedencia.json').read_text())['commit'],
                 settings=dict(rate=RATE,seconds=SECONDS,partials=PARTIALS,
                               brightness=.78,decay_seconds=4,body_mix=.45,bridge=.2),
                 profiles=profiles)
    iterations=[];best={}
    # Identify one strike position per register, shared across velocities.
    position_trials=[]
    for note in sorted(set(row['note'] for row in profiles)):
        choices=[]
        for position in (.095,.105,.115,.125,.135,.145):
            for row in profiles:
                if row['note']==note:row['position_scale']=position/piano_profile(440*2**((note-69)/12))['position']
            calibration.DATA.write_text(json.dumps(dataset,indent=2)+'\n')
            calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
            score=[]
            for n,v,name in REFERENCES:
                if n==note:score.append(error(references[name],render(n,v,True),n,metadata[name]['stiffness'])['partial_shape_db'])
            choices.append((float(np.mean(score)),position))
        score,position=min(choices)
        for row in profiles:
            if row['note']==note:row['position_scale']=position/piano_profile(440*2**((note-69)/12))['position']
        position_trials.append(dict(note=note,candidates=choices,selected=position))
    def save():
        calibration.DATA.write_text(json.dumps(dataset,indent=2)+'\n')
        calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
    for iteration in range(20):
        if iteration in (8,14):
            # Fit temporal build-up and beating after identifying losses.
            # These scalar searches are offline; no optimizer in playback.
            for note in sorted(set(row['note'] for row in profiles)):
                for key,candidates,start,stop in (
                    ('tail_mix',(.03,.08,.15,.22,.35),.05,4.),
                    ('polar_detune_scale',(.01,.25,.5,1.),.35,4.),
                    ('unison_scale',(.1,.25,.5,.75,1.,1.25),.35,4.),
                    ('rise_seconds',(.001,.003,.006,.009,.012,.016,.022),0.,.15)):
                    choices=[]
                    for value in candidates:
                        for row in profiles:
                            if row['note']==note:row[key]=value
                        save()
                        scores=[envelope_error(references[name],render(n,v,True),start,stop)
                                for n,v,name in REFERENCES if n==note]
                        choices.append((float(np.mean(scores)),value))
                    score,value=min(choices)
                    for row in profiles:
                        if row['note']==note:row[key]=value
                    position_trials.append(dict(note=note,parameter=key,candidates=choices,selected=value))
        calibration.DATA.write_text(json.dumps(dataset,indent=2)+'\n')
        calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
        rows=[]
        for row,(note,velocity,name) in zip(profiles,REFERENCES):
            reference=references[name];audio=render(note,velocity,True)
            b=metadata[name]['stiffness']
            target,slope=features(reference,note,b);actual,model_slope=features(audio,note,b)
            measured=error(reference,audio,note,b)
            attack=envelope_error(reference,audio,0,.15)
            evolution=envelope_error(reference,audio,.35,4)
            score=measured['partial_shape_db']+.5*measured['decay_slope_db_s']+attack+evolution
            if name not in best or score<best[name]['score']:
                best[name]=dict(score=score,iteration=iteration,profile=copy.deepcopy(row))
            active=(target>target.max()*.003)&(actual>actual.max()*1e-5)
            ratio=np.log(np.maximum(target,1e-12)/np.maximum(actual,1e-12))
            ratio-=np.median(ratio[active])
            gain=np.array(row['gain']);gain[active]*=np.exp(.6*np.clip(ratio[active],-1,1))
            row['gain']=np.clip(gain,.015,24).tolist()
            valid=active&(slope<-.3)&(model_slope<-.3)
            scale=np.array(row['decay']);scale[valid]*=np.clip(model_slope[valid]/slope[valid],.7,1.5)**.45
            row['decay']=np.clip(scale,.15,8).tolist()
            rows.append(dict(name=name,**measured,attack=attack,evolution=evolution,diagnostic_score=score))
        iterations.append(rows)
        print(iteration,rows,flush=True)
    # Keep the best measured checkpoint, not automatically the last one.
    profiles[:]=[copy.deepcopy(best[name]['profile']) for _,_,name in REFERENCES]
    calibration.DATA.write_text(json.dumps(dataset,indent=2)+'\n');calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
    # Preserve the existing patch's RMS/headroom; a spectral fit must not
    # quietly turn into a volume reduction. This scalar is gain, not a new
    # dynamic compressor, and does not depend on currently held voice count.
    for row,(note,velocity,name) in zip(profiles,REFERENCES):
        audio=render(note,velocity,True)
        scale=np.linalg.norm(before[name])/max(np.linalg.norm(audio),1e-12)
        row['gain']=(np.asarray(row['gain'])*scale).tolist()
    calibration.DATA.write_text(json.dumps(dataset,indent=2)+'\n');calibration._rows.cache_clear();calibration.modal_correction.cache_clear()
    results=[]
    for note,velocity,name in REFERENCES:
        reference=references[name];audio=render(note,velocity,True);old=before[name]
        b=metadata[name]['stiffness']
        target=min(.025,*[np.sqrt(np.mean(x*x))*.8 for x in (reference,old,audio)])
        for label,x in (('referencia',reference),('antes',old),('ajustado',audio)):
            write_audio(FOLDER/(name+'_'+label+'.wav'),x,target)
        results.append(dict(name=name,note=note,velocity=velocity,
                            before=error(reference,old,note,b),after=error(reference,audio,note,b),
                            attack_envelope_db_before=envelope_error(reference,old,0,.15),
                            attack_envelope_db_after=envelope_error(reference,audio,0,.15),
                            envelope_db_before=envelope_error(reference,old,.35,4),
                            envelope_db_after=envelope_error(reference,audio,.35,4),
                            selected_iteration=best[name]['iteration'],
                            identification=metadata[name]))
    report=dict(hardware=False,rate=RATE,seconds=SECONDS,iterations=iterations,positions=position_trials,results=results,
                profile_sha256=hashlib.sha256(calibration.DATA.read_bytes()).hexdigest())
    (FOLDER/'resultados.json').write_text(json.dumps(report,indent=2)+'\n')
    print('RESULTADOS',json.dumps(results,indent=2))

if __name__=='__main__':main()
