"""Mezcla digital de C3/G3: mide residuo respecto a dos senoides sin conectar el Q."""
from dataclasses import replace
import numpy as np
from diagnosticos.synth_presets_v16 import panel_presets
from monitor.historico.v16.fm_source import FMSource
p=panel_presets(['Seno limpio'])['Seno limpio']
for vol in (.5,.97,2.5):
 s=FMSource(20000,replace(p,notes=((48,90),(55,94)),gate=True))
 blocks=[];g=[]
 for i in range(250):
  blocks.append(s.render_dac_codes(i*480,(i+1)*480,vol,1.65));g.append(s.compressor_gain)
 a=np.concatenate(blocks)[40000:].astype(float)*3.3/4095-1.65
 t=np.arange(len(a))/20000
 basis=np.column_stack([func(2*np.pi*440*2**((n-69)/12)*t) for n in (48,55) for func in (np.sin,np.cos)]+[np.ones(len(t))])
 fit=basis@np.linalg.lstsq(basis,a,rcond=None)[0]
 print(vol,'gain',min(g),max(g[100:]),'residual',20*np.log10(np.std(a-fit)/np.std(fit)))
