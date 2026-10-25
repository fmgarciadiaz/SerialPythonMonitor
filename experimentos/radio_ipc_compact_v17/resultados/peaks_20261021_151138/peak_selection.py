"""Isolated exact top-five selector; production spectral code is unchanged."""
import numpy as np


def strongest(candidates, amplitude):
    if len(candidates) <= 5:
        return candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]
    values = amplitude[candidates]
    if np.isnan(values).any():
        return candidates[np.argsort(-values,kind='stable')[:5]]
    threshold = np.partition(values,len(values)-5)[-5]
    above = candidates[values > threshold]
    tied = candidates[values == threshold][:5-len(above)]
    selected = np.concatenate((above,tied))
    return selected[np.argsort(-amplitude[selected],kind='stable')]
