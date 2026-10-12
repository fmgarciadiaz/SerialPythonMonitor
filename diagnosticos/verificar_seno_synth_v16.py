"""Verifica la pureza digital del preset diagnóstico sin conectar el Q."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from diagnosticos.synth_presets_v16 import panel_presets
from monitor.v16.fm_source import FMSource

def measure(rate,vol):
    p=panel_presets(['Seno limpio'],rate)['Seno limpio']
    assert p.waveform=='sine' and p.oscillator_levels==(1.,0.,0.)
    assert p.filter_type=='off' and p.feedback==p.osc2_feedback==p.osc3_feedback==0
    src=FMSource(rate,replace(p,notes=((69,100),),gate=True))
    src.diagnostic_path=Path('/tmp/unused_sound_metrics')
    codes=np.concatenate([src.render_dac_codes(i*480,(i+1)*480,vol,1.65)
                          for i in range((rate*2+479)//480)])
    audio=codes[rate:rate*2].astype(float)*3.3/4095-1.65
    t=np.arange(rate)/rate
    basis=np.column_stack((np.sin(2*np.pi*440*t),np.cos(2*np.pi*440*t),np.ones(rate)))
    fitted=basis@np.linalg.lstsq(basis,audio,rcond=None)[0]
    residual=float(np.sqrt(np.mean((audio-fitted)**2)))
    rms=float(np.sqrt(np.mean((fitted-fitted.mean())**2)))
    return dict(rate=rate,vol=vol,residual_to_tone_db=float(20*np.log10(residual/rms)),
                soft_limited_samples=src.soft_limited_samples,min_gain=src.min_compressor_gain)

if __name__=='__main__':
    rows=[measure(rate,vol) for rate in (20000,40000) for vol in (.5,1.,2.5)]
    output=Path('diagnosticos/resultados_piano/eficiencia_v16/20261010_clean_sine.json')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))
