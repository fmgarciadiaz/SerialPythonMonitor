"""On-demand RF carrier candidates, independent of display FFT settings."""
import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks

SCAN_SIZE = 65536
SCAN_BLOCKS = 3


def scan_carriers(values, rate, snr_db=10, persistence=2):
    values=np.asarray(values,dtype=float)
    if values.shape!=(SCAN_SIZE*SCAN_BLOCKS,) or not np.isfinite(values).all() or not 6<=snr_db<=60 or persistence not in (2,3):
        raise ValueError('Scan requiere tres bloques RF completos')
    blocks=values.reshape(SCAN_BLOCKS,SCAN_SIZE)
    blocks=blocks-blocks.mean(axis=1,keepdims=True)
    window=np.hanning(SCAN_SIZE);window_sum=window.sum()
    power=abs(np.fft.rfft(blocks*window,axis=1))**2
    db=10*np.log10(np.maximum(power,1e-24))
    averaged=10*np.log10(np.maximum(power.mean(axis=0),1e-24))
    baseline=median_filter(averaged,size=201,mode='nearest')
    peaks,properties=find_peaks(averaged,prominence=6,height=baseline+snr_db)
    frequencies=np.fft.rfftfreq(SCAN_SIZE,1/rate)
    candidates=[]
    for i,peak in enumerate(peaks):
        if not 5000<=frequencies[peak]<=600000:continue
        # Estimate nearby noise excluding the carrier's own main lobe.
        radius=max(16,int(10000*SCAN_SIZE/rate))
        guard=max(3,int(100*SCAN_SIZE/rate))
        local=np.r_[np.arange(max(1,peak-radius),max(1,peak-guard)),
                    np.arange(min(len(averaged)-1,peak+guard+1),min(len(averaged)-1,peak+radius+1))]
        noise=float(np.median(averaged[local]))
        excess=float(averaged[peak]-noise)
        repeated=int(np.count_nonzero(db[:,peak]-np.median(db[:,local],axis=1)>=snr_db))
        if excess<snr_db or repeated<persistence:continue
        a,b,c=averaged[peak-1:peak+2]
        denom=a-2*b+c
        offset=np.clip(.5*(a-c)/denom,-.5,.5) if denom<0 else 0
        amplitude=2*np.sqrt(power[:,peak].mean())/window_sum
        candidates.append({'frequency':float((peak+offset)*rate/SCAN_SIZE),
                           'above_noise_db':excess,'persistence':repeated,
                           'amplitude_v':float(amplitude),'dbfs':float(20*np.log10(max(amplitude,1e-12)/1.65)),
                           'power_db':float(averaged[peak])})
    # Keep the strongest carrier per audio-sideband neighborhood.
    accepted=[]
    for candidate in sorted(candidates,key=lambda p:p['power_db'],reverse=True):
        if all(abs(candidate['frequency']-p['frequency'])>4500 for p in accepted):
            accepted.append(candidate)
    return sorted(accepted,key=lambda p:p['frequency'])
