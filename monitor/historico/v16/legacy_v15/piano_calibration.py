"""Small offline-identified modal corrections; no samples in the audio loop."""
import json
from pathlib import Path
from functools import lru_cache
import numpy as np

DATA=Path(__file__).with_name('piano_identificado.json')
SCALAR_DEFAULTS=dict(stiffness_scale=1.,position_scale=1.,unison_scale=1.,
                     rise_seconds=.001,tail_mix=.22,polar_detune_scale=1.)

@lru_cache(maxsize=1)
def _rows():
    if not DATA.exists():return ()
    return tuple(json.loads(DATA.read_text())['profiles'])

@lru_cache(maxsize=256)
def modal_correction(frequency,velocity):
    rows=_rows()
    if not rows:return None
    note=69+12*np.log2(max(frequency,1)/440)
    anchors=sorted(set(row['note'] for row in rows))
    def at_note(anchor):
        selected=sorted((r for r in rows if r['note']==anchor),key=lambda r:r['velocity'])
        v=[r['velocity'] for r in selected]
        right=min(len(v)-1,int(np.searchsorted(v,velocity)))
        left=max(0,right-1)
        weight=np.clip((velocity-v[left])/max(v[right]-v[left],1e-12),0,1)
        curves={key:np.asarray(selected[left][key])*(1-weight)+np.asarray(selected[right][key])*weight
                for key in ('gain','decay')}
        for key in ('phase','noise'):
            low=np.asarray(selected[left].get(key,[0.]*32 if key=='phase' else [0.]*6))
            high=np.asarray(selected[right].get(key,[0.]*32 if key=='phase' else [0.]*6))
            curves[key]=np.angle((1-weight)*np.exp(1j*low)+weight*np.exp(1j*high)) if key=='phase' else low*(1-weight)+high*weight
        scalars={key:selected[left].get(key,default)*(1-weight)+
                     selected[right].get(key,default)*weight
                 for key,default in SCALAR_DEFAULTS.items()}
        return curves,scalars
    right=min(len(anchors)-1,int(np.searchsorted(anchors,note)))
    left=max(0,right-1)
    weight=np.clip((note-anchors[left])/max(anchors[right]-anchors[left],1e-12),0,1)
    low=at_note(anchors[left]);high=at_note(anchors[right])
    result={key:np.exp(np.log(low[0][key])*(1-weight)+np.log(high[0][key])*weight)
            for key in ('gain','decay')}
    result['phase']=np.angle((1-weight)*np.exp(1j*low[0]['phase'])+weight*np.exp(1j*high[0]['phase']))
    result['noise']=low[0]['noise']*(1-weight)+high[0]['noise']*weight
    for key in SCALAR_DEFAULTS:
        result[key]=float(np.exp(np.log(low[1][key])*(1-weight)+np.log(high[1][key])*weight))
    for key in ('gain','decay','phase','noise'):result[key].setflags(write=False)
    return result
