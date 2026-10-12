"""Fit a short synthetic contact residual; no sample replay in the engine."""
import sys,json
from pathlib import Path
import numpy as np
from scipy.signal import stft
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'diagnosticos'))
import ajustar_piano_referencia as fit
from ajustar_ataque_piano import refresh
from monitor.historico.v15 import piano_calibration as cal
from monitor.historico.v15.virtual_instruments import attack_texture,warmup
BANDS=((100,400),(400,900),(900,1800),(1800,3500),(3500,6000),(6000,8400))
def residual(x,note,b):
    x=x/max(np.sqrt(np.mean(x*x)),1e-12)
    f,t,z=stft(x[:3000],fit.RATE,nperseg=512,noverlap=384,boundary=None)
    n=np.arange(1,100);partials=440*2**((note-69)/12)*n*np.sqrt((1+b*n*n)/(1+b))
    mask=np.min(abs(f[:,None]-partials),axis=1)>65
    return np.array([np.mean(abs(z[mask&(f>=lo)&(f<hi)])**2) if np.any(mask&(f>=lo)&(f<hi)) else 0 for lo,hi in BANDS])
def main():
    warmup();data=json.loads(cal.DATA.read_text());reports=[]
    for row,(note,v,name) in zip(data['profiles'],fit.REFERENCES):
        ref,b,_=fit.prepare(name,note);before=fit.render(note,v,True)
        target=residual(ref,note,b);current=residual(before,note,b)
        levels=[]
        for j in range(6):
            unit=np.zeros(6);unit[j]=1
            noise=attack_texture(fit.RATE,440*2**((note-69)/12),v/127,.78,tuple(unit))
            # Noise is added before fixed gain and MIDI velocity.
            padded=np.pad(noise,(0,len(before)-len(noise)))*4*v/127
            power=residual(padded,note,b)[j]*np.mean(padded*padded)/max(np.mean(before*before),1e-12)
            levels.append(float(min(.04,np.sqrt(max(0,target[j]-current[j])/max(power,1e-20)))))
        def score(x):return float(np.mean(abs(np.log10(residual(x,note,b)+1e-12)-np.log10(target+1e-12))))+fit.envelope_error(ref,x,0,.15)
        best=score(before);chosen=np.zeros(6);audio=before
        for strength in (.25,.5,1):
            row['noise']=(np.array(levels)*strength).tolist();cal.DATA.write_text(json.dumps(data,indent=2)+'\n');refresh();candidate=fit.render(note,v,True);err=score(candidate)
            if err<best:best=err;chosen=np.array(levels)*strength;audio=candidate
        row['noise']=chosen.tolist();cal.DATA.write_text(json.dumps(data,indent=2)+'\n');refresh()
        reports.append(dict(note=note,velocity=v,levels=chosen.tolist(),score_before=score(before),score_after=best))
        fit.write_audio(ROOT/f'diagnosticos/resultados_piano/ataque/{name}_ajustado.wav',audio,.025)
        print(reports[-1],flush=True)
    (ROOT/'diagnosticos/resultados_piano/ataque/ruido.json').write_text(json.dumps(reports,indent=2)+'\n')
if __name__=='__main__':main()
