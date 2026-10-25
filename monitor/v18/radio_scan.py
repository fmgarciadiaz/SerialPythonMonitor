"""On-demand RF carrier candidates, independent of display FFT settings."""
import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks
from monitor.v18.radio_am import radio_tuning_max
from monitor.v18.radio_tuning import tuning_bounds

SCAN_SIZE = 65536
SCAN_BLOCKS = 3


def scan_carriers(values, rate, snr_db=10, persistence=2, bandwidth=8000.):
    values=np.asarray(values,dtype=float)
    if values.shape!=(SCAN_SIZE*SCAN_BLOCKS,) or not np.isfinite(values).all() or not np.isfinite(rate) or rate<=0 or not 5<=snr_db<=60 or persistence not in (2,3):
        raise ValueError('Scan requiere tres bloques RF completos')
    minimum,maximum=tuning_bounds(rate,bandwidth)
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
    levels=np.vstack((averaged,db))
    radius=max(16,int(10000*SCAN_SIZE/rate))
    guard=max(3,int(100*SCAN_SIZE/rate))
    # Same stable power order as final grouping. Only an already validated,
    # stronger candidate may exclude a neighbor before its costly noise checks.
    peaks=peaks[np.argsort(-averaged[peaks],kind='stable')]
    for peak in peaks:
        if not minimum<=frequencies[peak]<=maximum:continue
        a,b,c=averaged[peak-1:peak+2]
        denom=a-2*b+c
        offset=np.clip(.5*(a-c)/denom,-.5,.5) if denom<0 else 0
        frequency=float((peak+offset)*rate/SCAN_SIZE)
        if not minimum<=frequency<=maximum:continue
        if any(abs(frequency-p['frequency'])<=4500 for p in candidates):continue
        # Estimate nearby noise excluding the carrier's own main lobe.
        local=np.r_[np.arange(max(1,peak-radius),max(1,peak-guard)),
                    np.arange(min(len(averaged)-1,peak+guard+1),min(len(averaged)-1,peak+radius+1))]
        local_noise=np.median(levels[:,local],axis=1)
        noise=float(local_noise[0])
        excess=float(averaged[peak]-noise)
        repeated=int(np.count_nonzero(db[:,peak]-local_noise[1:]>=snr_db))
        if excess<snr_db or repeated<persistence:continue
        amplitude=2*np.sqrt(power[:,peak].mean())/window_sum
        candidates.append({'frequency':frequency,
                           'above_noise_db':excess,'persistence':repeated,
                           'amplitude_v':float(amplitude),'dbfs':float(20*np.log10(max(amplitude,1e-12)/1.65)),
                           'power_db':float(averaged[peak])})
    for candidate in candidates:
        neighbors=[]
        for other in candidates:
            mirror=2*candidate['frequency']-other['frequency']
            # Symmetric weaker peaks may be this carrier's AM sidebands.
            sideband=(other['power_db']<candidate['power_db']-6 and any(
                abs(p['frequency']-mirror)<2*rate/SCAN_SIZE and
                abs(p['power_db']-other['power_db'])<3 for p in candidates))
            if not sideband:neighbors.append(other['frequency'])
        candidate['suggested_bandwidth'] = estimate_bandwidth(
            power, rate, candidate['frequency'], neighbors)
    return sorted(candidates,key=lambda p:p['frequency'])


def estimate_bandwidth(power, rate, carrier, carriers=()):
    """Conservative occupied-band estimate, not a transmitter bandwidth detector.

    Require persistent energy on both sides; silence and clipped observation
    windows return no suggestion. Nearby carriers bound the observable region.
    """
    spacing=rate/SCAN_SIZE
    frequencies=np.fft.rfftfreq(SCAN_SIZE,1/rate)
    offsets=np.arange(max(250,4*spacing),10001,spacing)
    limit=min(carrier,rate/2-carrier,10000)
    for other in carriers:
        if abs(other-carrier)>spacing:
            limit=min(limit,abs(other-carrier)/2-3*spacing)
    if limit<1000:return None
    offsets=offsets[offsets<limit]
    if not len(offsets):return None
    left=np.rint((carrier-offsets)/spacing).astype(int)
    right=np.rint((carrier+offsets)/spacing).astype(int)
    # Local median ignores isolated tones and carrier leakage.
    noise=np.median(power[:,np.r_[left,right]],axis=1)
    threshold=np.maximum(noise*10, np.max(power,axis=1)*1e-7)
    paired=(power[:,left]>threshold[:,None]) & (power[:,right]>threshold[:,None])
    persistent=np.count_nonzero(paired,axis=0)>=2
    if not persistent.any():return None
    edge=float(offsets[np.flatnonzero(persistent)[-1]])
    # Energy reaching a neighbor/Nyquist boundary is ambiguous.
    if edge+max(250,3*spacing)>=limit:return None
    needed=2*(edge+max(250,3*spacing))
    return next((width for width in (6000,8000,10000,12000,20000) if width>=needed),None)
