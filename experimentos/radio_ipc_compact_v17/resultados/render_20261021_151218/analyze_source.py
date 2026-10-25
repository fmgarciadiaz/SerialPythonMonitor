def analyze(values, fs, n=None, window='Hann', remove_dc=True, overlap=.5, maximum=4):
    n = n or len(values)
    blocks = segments(values,n,overlap,maximum)
    ft,w,c = _fft(blocks,fs,window,remove_dc)
    _,_,window_sum,window_power = _window_factors(n,window)
    mean_power = np.mean(np.abs(ft)**2,axis=0)
    amplitude = np.sqrt(mean_power)*c/window_sum
    psd = mean_power*c/(fs*window_power)
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
    strongest = candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]
    for index in strongest:
        delta = 0.
        if 0 < index < len(amplitude)-1:
            a,b,d = np.log(np.maximum(amplitude[index-1:index+2],1e-300))
            denom = a-2*b+d
            if denom < 0: delta = float(np.clip(.5*(a-d)/denom,-.5,.5))
        peaks.append({'bin':int(index),'frequency':float((index+delta)*fs/n),'amplitude':float(amplitude[index])})
    return SpectralResult(frequencies,amplitude,phase,psd,len(blocks),fs/n,
        fs*window_power/window_sum**2,peaks)
