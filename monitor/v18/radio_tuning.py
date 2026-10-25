"""Shared RF/alias contract. US spans the first two Nyquist zones."""
import math


def tuning_bounds(rate, bandwidth, undersampling=False):
    if not math.isfinite(rate) or not math.isfinite(bandwidth) or rate<=0 or bandwidth<=0:
        raise ValueError('FS o banda RF inválida')
    half=bandwidth/2
    if undersampling:
        return max(5000,math.floor(half)+1), math.ceil(rate-half)-1
    return max(5000,math.floor(half)+1), math.ceil(rate/2-half)-1


def alias_frequency(rate, frequency, bandwidth, undersampling=False):
    low,high=tuning_bounds(rate,bandwidth,undersampling)
    if not math.isfinite(frequency) or not low<=frequency<=high:
        raise ValueError('Sintonía fuera de banda; el canal completo debe quedar dentro de la zona Nyquist')
    alias=abs((frequency+rate/2)%rate-rate/2) if undersampling else frequency
    if not bandwidth/2<alias<rate/2-bandwidth/2:
        raise ValueError('Canal RF cruza Nyquist o DC; elegir otra sintonía')
    return alias


def rf_frequency(rate, alias, undersampling=False):
    return rate-alias if undersampling else alias
