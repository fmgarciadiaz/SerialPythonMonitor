"""Isolated, lossless RADIO metadata codec. Not imported by production."""
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np


@dataclass(frozen=True)
class RegularRadioBatch:
    ch1: np.ndarray
    first_index: int
    index_dtype: str
    first_time: float
    time_dtype: str
    dt_us: float
    acquisition: object


def expand(payload):
    if not isinstance(payload, RegularRadioBatch):
        return payload
    count = len(payload.ch1)
    offsets = np.arange(count, dtype=np.uint64)
    indices = ((offsets + payload.first_index) & 0xffffffff).astype(payload.index_dtype)
    times = (np.arange(count, dtype=np.float64)*payload.dt_us + payload.first_time).astype(payload.time_dtype)
    return SimpleNamespace(columns={'CH1': payload.ch1, 'Muestra': indices,
                                    'Tiempo (us)': times}, acquisition=payload.acquisition)


def compact(batch, settings):
    """Compact only when reconstruction is bit-exact; otherwise keep input.

    No continuity state lives here. Original BatchProcessor remains responsible
    for checking discontinuities, including boundaries and generation resets.
    """
    config = batch.acquisition
    if (not settings.radio_enabled or settings.filter.source not in ('OFF', 'RADIO')
            or (config.bits, config.rate) != (8, 1600000)
            or set(batch.columns) != {'CH1', 'Muestra', 'Tiempo (us)'}):
        return batch
    ch1, indices, times = (batch.columns[k] for k in ('CH1', 'Muestra', 'Tiempo (us)'))
    if (any(a.ndim != 1 for a in (ch1, indices, times)) or not len(ch1)
            or len(ch1) != len(indices) or len(ch1) != len(times)
            or indices.dtype.kind not in 'uif' or times.dtype.kind != 'f'
            or not np.isfinite(indices[0]) or not np.isfinite(times[0])
            or not 0 <= indices[0] <= 0xffffffff or indices[0] != int(indices[0])):
        return batch
    candidate = RegularRadioBatch(ch1, int(indices[0]), indices.dtype.str,
                                  float(times[0]), times.dtype.str, config.dt_us, config)
    restored = expand(candidate)
    # Compare bytes, not tolerances: never regularize a corrupt timestamp,
    # fractional index, missing sample or a floating-point rounding difference.
    for key in ('Muestra', 'Tiempo (us)'):
        if batch.columns[key].tobytes() != restored.columns[key].tobytes():
            return batch
    return candidate


def process_compact(payload, settings):
    from monitor.v17.processing import process_owned_result
    return process_owned_result(expand(payload), settings)
