"""Isolated exact top-five selector; production spectral code is unchanged."""
import numpy as np


def make_analyze_candidate(original):
    """Fail closed unless the known production assignment occurs exactly once."""
    import inspect
    source = inspect.getsource(original)
    assignment = "strongest = candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]"
    if source.count(assignment) != 1:
        raise RuntimeError('La fuente analyze cambió; revisar el candidato antes de usarlo')
    namespace = dict(original.__globals__,select_strongest=strongest)
    exec(source.replace(assignment,'strongest = select_strongest(candidates, amplitude)'),namespace)
    return namespace['analyze']


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
