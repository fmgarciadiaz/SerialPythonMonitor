"""Stateful causal measurement filters; never modifies acquired channels."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import butter,bessel,iirfilter,sosfilt,sosfilt_zi,bilinear,tf2sos

@dataclass(frozen=True)
class FilterConfig:
    source: str='CH1'
    mode: str='lowpass'
    design: str='Butterworth'
    cutoff: float=1000.
    upper: float=5000.
    order: int=2

class DigitalFilter:
    def __init__(self):self.reset()
    def reset(self):self.key=None;self.state=None;self.previous_index=None;self.previous_time=None
    def process(self,values,rate,config,indices=None,timestamps=None):
        values=np.asarray(values,dtype=float)
        if not len(values):return values.copy()
        if not np.isfinite(values).all() or not np.isfinite(rate) or rate<=0:raise ValueError('Datos de filtro inválidos')
        if config.mode not in ('bypass','lowpass','highpass','bandpass','bandstop') or config.design not in ('RC','Butterworth','Bessel','Chebyshev I','Chebyshev II','Elliptic') or config.source not in ('CH1','CH2'):raise ValueError('Filtro inválido')
        if config.mode=='bandstop' and config.design=='RC':raise ValueError('Band reject no admite etapas RC; seleccionar otro tipo')
        if not 1<=config.order<=8:raise ValueError('Orden inválido')
        if not np.isfinite(config.cutoff) or not np.isfinite(config.upper):raise ValueError('Frecuencias de filtro inválidas')
        if config.mode=='bandstop' and not 0<config.cutoff<config.upper<rate/2:raise ValueError('Banda de rechazo fuera de Nyquist')
        cutoff=np.clip(config.cutoff,1,rate*.45);upper=np.clip(config.upper,cutoff+1,rate*.49)
        if config.mode=='bandstop':cutoff,upper=config.cutoff,config.upper
        key=(config,float(rate),float(cutoff),float(upper))
        discontinuity=False
        if indices is not None:
            indices=np.asarray(indices,dtype=np.uint64)
            delta=(np.diff(indices.astype(np.int64))&0xffffffff)
            discontinuity=bool(np.any(delta!=1)) or (self.previous_index is not None and ((int(indices[0])-self.previous_index)&0xffffffff)!=1)
        if timestamps is not None:
            timestamps=np.asarray(timestamps,dtype=float)
            delta=np.diff(timestamps)%2**32
            discontinuity|=bool(np.any(abs(delta-1e6/rate)>1.1)) or (self.previous_time is not None and abs((timestamps[0]-self.previous_time)%2**32-1e6/rate)>1.1)
        if discontinuity:raise ValueError('Discontinuidad antes del filtro')
        if key!=self.key:
            if config.mode=='bypass':self.sos=None
            elif config.design=='RC':
                sections=[]
                for mode,frequency in ([('highpass',cutoff),('lowpass',upper)] if config.mode=='bandpass' else [(config.mode,cutoff)]):
                    w=2*rate*np.tan(np.pi*frequency/rate)
                    b,a=bilinear([1,0] if mode=='highpass' else [w],[1,w],fs=rate)
                    for _ in range(config.order):
                        sections.extend(tf2sos(b,a))
                self.sos=np.asarray(sections)
            else:
                edge=[cutoff,upper] if config.mode in ('bandpass','bandstop') else cutoff
                if config.design=='Bessel':self.sos=bessel(config.order,edge,btype=config.mode,fs=rate,output='sos',norm='mag')
                else:
                    family={'Butterworth':'butter','Chebyshev I':'cheby1','Chebyshev II':'cheby2','Elliptic':'ellip'}[config.design]
                    self.sos=iirfilter(config.order,edge,btype=config.mode,ftype=family,rp=1,rs=40,fs=rate,output='sos')
            self.state=sosfilt_zi(self.sos)*values[0] if self.sos is not None else None;self.key=key
        output=values.copy() if self.sos is None else self._filter(values)
        if indices is not None:self.previous_index=int(indices[-1])
        if timestamps is not None:self.previous_time=float(timestamps[-1])
        return output
    def _filter(self,values):
        output,self.state=sosfilt(self.sos,values,zi=self.state);return output
