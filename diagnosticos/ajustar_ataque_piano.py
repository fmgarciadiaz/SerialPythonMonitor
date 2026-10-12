"""Offline effective modal attack phase identification against licensed notes."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'diagnosticos'))
import ajustar_piano_referencia as fit
from monitor.historico.v15 import piano_calibration as cal
from monitor.historico.v15.virtual_instruments import warmup
OUT=ROOT/'diagnosticos/resultados_piano/ataque'
def refresh():cal._rows.cache_clear();cal.modal_correction.cache_clear()
def coefficients(audio,frequencies):
    t=np.arange(300,1900)/fit.RATE;w=np.hanning(len(t))
    design=np.concatenate((np.cos(2*np.pi*t[:,None]*frequencies),np.sin(2*np.pi*t[:,None]*frequencies)),axis=1)
    c=np.linalg.lstsq(design*w[:,None],audio[300:1900]*w,rcond=1e-5)[0]
    return c[:len(frequencies)]-1j*c[len(frequencies):]
def score(ref,audio):return fit.envelope_error(ref,audio,0,.15)
def main():
    warmup();OUT.mkdir(parents=True,exist_ok=True);data=json.loads(cal.DATA.read_text());report=[]
    for row,(note,velocity,name) in zip(data['profiles'],fit.REFERENCES):
        ref,b,meta=fit.prepare(name,note);before=fit.render(note,velocity,True)
        n=np.arange(1,33);freq=440*2**((note-69)/12)*n*np.sqrt((1+b*n*n)/(1+b));valid=freq<fit.RATE*.4
        delta=np.zeros(32);a=coefficients(ref,freq[valid]);m=coefficients(before,freq[valid]);phase=np.angle(a/(m+1e-20));phase[abs(a)<max(abs(a))*.005]=0;delta[valid]=phase
        best=score(ref,before);chosen=np.zeros(32);audio=before
        for amount in (.25,.5,.75,1.):
            row['phase']=(delta*amount).tolist();cal.DATA.write_text(json.dumps(data,indent=2)+'\n');refresh();candidate=fit.render(note,velocity,True);err=score(ref,candidate)
            if err<best:best=err;chosen=delta*amount;audio=candidate
        row['phase']=chosen.tolist();cal.DATA.write_text(json.dumps(data,indent=2)+'\n');refresh()
        report.append(dict(note=note,velocity=velocity,attack_before_db=score(ref,before),attack_after_db=best,phase_changed=bool(np.any(chosen)),late_before=fit.error(ref,before,note,b),late_after=fit.error(ref,audio,note,b)))
        for suffix,signal in (('referencia',ref),('antes',before),('ajustado',audio)):fit.write_audio(OUT/f'{name}_{suffix}.wav',signal,.025)
        print(report[-1],flush=True)
    (OUT/'resultados.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
