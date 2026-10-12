"""NumPy spectral estimators. Voltages in V, densities in V²/Hz; no Qt."""
from dataclasses import dataclass
import numpy as np

WINDOWS = {'Hann': np.hanning, 'Hamming': np.hamming,
           'Blackman': np.blackman, 'Rectangular': np.ones}


@dataclass
class SpectralResult:
    frequencies: np.ndarray
    amplitude: np.ndarray
    phase: np.ndarray
    psd: np.ndarray
    segments: int
    df: float
    enbw: float
    peaks: list


def segments(values, n, overlap=.5, maximum=4):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < n or n < 4 or not np.all(np.isfinite(values)):
        raise ValueError('Bloque incompleto o muestras inválidas')
    hop = max(1, round(n * (1-overlap)))
    starts = list(range(len(values)-n, -1, -hop))[:maximum][::-1]
    return np.stack([values[start:start+n] for start in starts])


def _fft(blocks, fs, window, remove_dc):
    if not np.isfinite(fs) or fs <= 0: raise ValueError('Frecuencia inválida')
    blocks = np.asarray(blocks, dtype=float)
    if blocks.ndim != 2 or not np.all(np.isfinite(blocks)): raise ValueError('Muestras inválidas')
    n = blocks.shape[1]
    w = WINDOWS[window](n)
    if w.sum() <= 0: raise ValueError('Ventana inválida')
    data = blocks-blocks.mean(axis=1, keepdims=True) if remove_dc else blocks
    ft = np.fft.rfft(data*w, axis=1)
    c = np.full(ft.shape[1],2.); c[0] = 1
    if n % 2 == 0: c[-1] = 1
    return ft, w, c


def analyze(values, fs, n=None, window='Hann', remove_dc=True, overlap=.5, maximum=4):
    n = n or len(values)
    blocks = segments(values,n,overlap,maximum)
    ft,w,c = _fft(blocks,fs,window,remove_dc)
    amplitude = np.sqrt(np.mean((np.abs(ft)*c/w.sum())**2,axis=0))
    psd = np.mean(np.abs(ft)**2,axis=0)*c/(fs*np.sum(w*w))
    phase = np.degrees(np.angle(ft[-1]))
    # Hide phase below a relative amplitude threshold. This is instantaneous
    # spectral phase, not a statistical confidence test for noise-only bins.
    support = amplitude > max(float(amplitude.max())*1e-4, 1e-12)
    phase[~support] = np.nan
    frequencies = np.fft.rfftfreq(n,1/fs)
    candidates = np.flatnonzero((amplitude[1:-1] > amplitude[:-2]) & (amplitude[1:-1] >= amplitude[2:]))+1
    if amplitude[-1] > amplitude[-2] and amplitude[-1] > 1e-12:
        candidates = np.append(candidates,len(amplitude)-1)
    if not len(candidates) and np.any(amplitude[1:] > 1e-12): candidates = np.array([1+np.argmax(amplitude[1:])])
    peaks = []
    for index in sorted(candidates,key=lambda i: amplitude[i],reverse=True)[:5]:
        delta = 0.
        if 0 < index < len(amplitude)-1:
            a,b,d = np.log(np.maximum(amplitude[index-1:index+2],1e-300))
            denom = a-2*b+d
            if denom < 0: delta = float(np.clip(.5*(a-d)/denom,-.5,.5))
        peaks.append({'bin':int(index),'frequency':float((index+delta)*fs/n),'amplitude':float(amplitude[index])})
    return SpectralResult(frequencies,amplitude,phase,psd,len(blocks),fs/n,
        fs*np.sum(w*w)/w.sum()**2,peaks)


def band_power(result, low=0, high=None):
    high = result.frequencies[-1] if high is None or high <= 0 else min(high,result.frequencies[-1])
    mask = (result.frequencies >= low) & (result.frequencies <= high)
    if low >= high or not np.any(mask): return np.nan
    return float(np.sum(result.psd[mask])*result.df)


def _ratio_db(numerator, denominator):
    if numerator <= 0 or denominator <= 0: return np.nan
    return float(10*np.log10(numerator/denominator))


def power_metrics(result, low=0, high=None, signal_low=0, signal_high=0):
    high = result.frequencies[-1] if not high else min(high,result.frequencies[-1])
    band = (result.frequencies >= low) & (result.frequencies <= high)
    residual = band.copy(); residual[0] = False
    for peak in result.peaks:
        i = peak['bin']; residual[max(0,i-3):i+4] = False
    floor = float(np.mean(result.psd[residual])) if np.count_nonzero(residual) >= 8 else np.nan
    total = band_power(result,low,high)
    signal = np.nan; noise = np.nan; snr = np.nan
    if signal_high > signal_low:
        signal = band_power(result,max(low,signal_low),min(high,signal_high))
        # Density outside the signal band is noise; include tones elsewhere.
        other = band & ~((result.frequencies >= signal_low)&(result.frequencies <= signal_high))
        if np.any(other): noise = float(np.sum(result.psd[other])*result.df)
    elif result.peaks:
        peak = result.peaks[0]; i = peak['bin']
        if peak['frequency'] >= 3*result.df and np.isfinite(floor) and result.psd[i] > max(floor*10,1e-24):
            tone = band & (np.abs(np.arange(len(band))-i) <= 3)
            signal = float(np.sum(result.psd[tone])*result.df)
            noise = float(np.sum(result.psd[band & ~tone])*result.df)
    if np.isfinite(signal) and np.isfinite(noise): snr = _ratio_db(signal,noise)
    return {'power':total,'rms':np.sqrt(total),'noise_floor':floor,'signal_power':signal,'noise_power':noise,'snd_db':snr,'snr_db':np.nan}


def _design(t, f0, orders):
    columns = [np.ones(len(t))]
    for order in orders:
        angle = 2*np.pi*f0*order*t
        columns.extend((np.cos(angle),np.sin(angle)))
    return np.column_stack(columns)


def distortion(values, fs, n=None, window='Hann', fundamental=0, harmonics=10, low=0, high=None):
    values = np.asarray(values,dtype=float)
    n = n or len(values); values = values[-n:]
    result = analyze(values,fs,n,window,maximum=1)
    invalid = lambda reason: {'valid':False,'reason':reason,'harmonics':[],'fundamental':np.nan,
        'thd':np.nan,'thdn':np.nan,'sinad_db':np.nan,'snr_db':np.nan}
    if not result.peaks: return invalid('Sin fundamental')
    f0 = float(fundamental or result.peaks[0]['frequency'])
    nyquist = fs/2; high = min(high or nyquist,nyquist)
    if not 3*fs/n <= f0 < nyquist-fs/n or not low <= f0 <= high:
        return invalid('Se requieren al menos tres ciclos y fundamental dentro de banda')
    floor = np.median(result.psd[1:])
    index = min(round(f0/result.df),len(result.psd)-1)
    if result.psd[index] < max(10*floor,1e-24): return invalid('Fundamental débil')
    t = np.arange(n)/fs
    # Refine only an automatically located fundamental, using a bounded search.
    if not fundamental:
        center = f0
        fit_orders = [order for order in range(1,min(int(harmonics),10)+1) if order*f0 < nyquist-result.df and low <= order*f0 <= high]
        if not fit_orders or fit_orders[0] != 1: return invalid('Fundamental fuera de banda')
        left = max(3*fs/n,center-result.df*.6); right = min(nyquist-result.df,center+result.df*.6)
        # Variable projection: solve linear amplitudes and a bounded frequency
        # correction. This avoids dozens of full least-squares trial fits.
        for _ in range(10):
            design = _design(t,f0,fit_orders)
            gram = design.T@design
            coeff = np.linalg.solve(gram,design.T@values)
            derivative = np.zeros(n)
            for index,order in enumerate(fit_orders):
                angle = 2*np.pi*f0*order*t
                derivative += 2*np.pi*order*t*(-coeff[2*index+1]*np.sin(angle)+coeff[2*index+2]*np.cos(angle))
            derivative -= design@np.linalg.solve(gram,design.T@derivative)
            denominator = float(derivative@derivative)
            if denominator <= 1e-24: break
            correction = float((values-design@coeff)@derivative/denominator)
            correction = float(np.clip(correction,-result.df*.3,result.df*.3))
            f0 = float(np.clip(f0+correction,left,right))
            if abs(correction) < result.df*1e-10: break
    orders = [order for order in range(1,min(int(harmonics),10)+1) if low <= order*f0 <= high and order*f0 < nyquist]
    if not orders or orders[0] != 1: return invalid('Fundamental fuera de banda')
    design = _design(t,f0,orders)
    coeff,_,rank,singular = np.linalg.lstsq(design,values,rcond=None)
    if rank != design.shape[1] or singular[0]/singular[-1] > 1e8: return invalid('Ajuste mal condicionado')
    powers = (coeff[1::2]**2+coeff[2::2]**2)/2
    residual = values-design@coeff
    noise = band_power(analyze(residual,fs,n,window,maximum=1),low,high)
    p1 = float(powers[0]); harmonic_power = float(powers[1:].sum())
    if p1 <= 1e-24: return invalid('Fundamental débil')
    if _ratio_db(p1,noise) < 6: return invalid('Fundamental no tonal: SNR del ajuste menor que 6 dB')
    return {'valid':True,'reason':'','fundamental':f0,'harmonics':[{'order':order,'frequency':order*f0,
        'power':float(power),'rms':float(np.sqrt(power)),'dbc':_ratio_db(power,p1)} for order,power in zip(orders,powers)],
        'fundamental_power':p1,'harmonic_power':harmonic_power,'noise_power':noise,
        'thd':float(np.sqrt(harmonic_power/p1)),'thdn':float(np.sqrt((harmonic_power+noise)/p1)),
        'sinad_db':_ratio_db(p1,harmonic_power+noise),'snr_db':_ratio_db(p1,noise)}


def transfer(x, y, fs, n=None, window='Hann', remove_dc=True, overlap=.5, maximum=4):
    if len(x) != len(y): raise ValueError('Canales sin muestras alineadas')
    n = n or len(x)
    xb = segments(x,n,overlap,maximum); yb = segments(y,n,overlap,maximum)
    if xb.shape != yb.shape: raise ValueError('Canales sin bloques alineados')
    xf,w,c = _fft(xb,fs,window,remove_dc); yf,_,_ = _fft(yb,fs,window,remove_dc)
    factor = c/(fs*np.sum(w*w))
    pxx = np.mean(np.abs(xf)**2,axis=0)*factor
    pyy = np.mean(np.abs(yf)**2,axis=0)*factor
    pxy = np.mean(np.conj(xf)*yf,axis=0)*factor
    support = pxx > max(float(pxx.max())*1e-8,1e-24)
    h = np.full(len(pxx),complex(np.nan,np.nan)); h[support] = pxy[support]/pxx[support]
    gain = np.full(len(pxx),np.nan); finite = support & (np.abs(h)>0)
    gain[support & (np.abs(h)==0)] = -np.inf
    gain[finite] = 20*np.log10(np.abs(h[finite]))
    coherence = np.full(len(pxx),np.nan)
    if len(xb) >= 2:
        mask = support & (pyy > 1e-24)
        coherence[mask] = np.clip(np.abs(pxy[mask])**2/(pxx[mask]*pyy[mask]),0,1)
    phase = np.full(len(pxx),np.nan); delay = phase.copy()
    phase_support = finite & (pyy > max(float(pyy.max())*1e-8,1e-24))
    phase_support &= (coherence >= .8) if len(xb) >= 2 else True
    frequencies = np.fft.rfftfreq(n,1/fs)
    indices = np.flatnonzero(phase_support)
    for run in np.split(indices,np.flatnonzero(np.diff(indices)>1)+1):
        if not len(run): continue
        radians = np.unwrap(np.angle(h[run])); phase[run] = np.degrees(radians)
        # Coherence cannot be inferred from one segment, nor can group delay.
        if len(xb) < 2 or len(run) < 5: continue
        spacing = 2*np.pi*fs/n
        delay[run[2:-2]] = -np.convolve(radians,np.array([2.,1.,0.,-1.,-2.]),mode='valid')/(10*spacing)
    return {'frequencies':frequencies,'h1':h,'gain_db':gain,'phase_deg':phase,
        'coherence':coherence,'group_delay_s':delay,'segments':len(xb),'pxx':pxx,'pyy':pyy,'pxy':pxy}
