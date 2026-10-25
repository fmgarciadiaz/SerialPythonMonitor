"""Estimated ADC rank skew for the V16 54 MHz sequential acquisition.

This removes acquisition phase, not the response of the measured circuit.
The firmware averages 16 consecutive conversions per rank in ADC16 mode.
"""
import numpy as np


def channel_delay_us(config):
    if config.channels == 1:
        return 0.0
    bits = min(config.bits, 14)
    repeats = 16 if config.bits == 16 else 1
    return repeats * (config.sampling_cycles + bits + 3) / 54


def pair_delay_us(config, pair, filter_source='CH1'):
    origins = {'CH1': 0.0, 'CH2': channel_delay_us(config)}
    origins['FILTER'] = origins[filter_source]
    return origins[pair[1]] - origins[pair[0]]


def correct_phase(data, delay_us):
    result = np.asarray(data, dtype=float).copy()
    result[:, 2] = (result[:, 2] - 360 * result[:, 0] * delay_us / 1e6 + 180) % 360 - 180
    return result
