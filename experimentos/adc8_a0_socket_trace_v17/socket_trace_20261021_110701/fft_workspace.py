"""Numerically equivalent FFT preparation with one private work array."""
import numpy as np
from monitor.v17.spectral_analysis import _window_factors


def fft_workspace(blocks, fs, window, remove_dc):
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError('Frecuencia inválida')
    blocks = np.asarray(blocks, dtype=float)
    if blocks.ndim != 2 or not np.all(np.isfinite(blocks)):
        raise ValueError('Muestras inválidas')
    w, c, _, _ = _window_factors(blocks.shape[1], window)
    data = np.array(blocks, copy=True)
    if remove_dc:
        data -= blocks.mean(axis=1, keepdims=True)
    data *= w
    return np.fft.rfft(data, axis=1), w, c
