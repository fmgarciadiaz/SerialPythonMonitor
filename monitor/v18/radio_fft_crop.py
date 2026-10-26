"""Display-only RF windows: equal columns, preserving actual station frequencies."""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class RadioColumn:
    carrier: float
    bandwidth: float
    alias: float
    direction: int
    index: int
    @property
    def left(self):return self.index*1.08
    @property
    def center(self):return self.left+.5
    def frequency(self,x):return self.carrier+(x-self.center)*self.bandwidth


def columns(candidates,rate,bandwidth,undersampling=False):
    result=[];seen=set()
    if not math.isfinite(rate) or rate<=0:return ()
    for candidate in sorted(candidates,key=lambda p:p.get('frequency',float('inf'))):
        carrier=float(candidate.get('frequency',float('nan')))
        width=float(candidate.get('suggested_bandwidth') or bandwidth)
        if not math.isfinite(carrier) or not math.isfinite(width) or width<=0 or carrier in seen:continue
        if not 0<carrier<(rate if undersampling else rate/2):continue
        alias=abs((carrier+rate/2)%rate-rate/2)
        if alias-width/2<=0 or alias+width/2>=rate/2:continue
        result.append(RadioColumn(carrier,width,alias,-1 if carrier>rate/2 else 1,len(result)))
        seen.add(carrier)
    return tuple(result)


def frequency_at(layout,x):
    for column in layout:
        if column.left<=x<=column.left+1:return column.frequency(x)
    return None


def crop_arrays(frequency,values,layout):
    """Keep full FFT bins per band, reverse aliased upper-zone sidebands."""
    xs=[];ys=[]
    for column in layout:
        low,high=column.alias-column.bandwidth/2,column.alias+column.bandwidth/2
        first=np.searchsorted(frequency,low,'left');last=np.searchsorted(frequency,high,'right')
        f=frequency[first:last];y=values[first:last]
        if column.direction<0:f=f[::-1];y=y[::-1]
        x=column.center+(f-column.alias)*column.direction/column.bandwidth
        # Finite X and NaN Y prevent lines/fills joining across omitted RF gaps.
        xs.extend((np.array([column.left]),x,np.array([column.left+1])))
        ys.extend((np.array([np.nan]),y,np.array([np.nan])))
    return (np.concatenate(xs),np.concatenate(ys)) if xs else (np.array([]),np.array([]))
