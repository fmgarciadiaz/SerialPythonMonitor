"""Measured loopback reference; never extrapolate or cross ADC profiles."""
import json
from pathlib import Path
import numpy as np

CALIBRATION_PATH = Path(__file__).resolve().parents[2] / 'calibraciones' / 'bode_v10.json'


def load_reference(path=CALIBRATION_PATH):
    try:
        reference = json.loads(Path(path).read_text())
        points = np.asarray(reference['points'], dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2:
            return None
        if not np.all(np.isfinite(points)) or np.any(points[:,0] <= 0) or np.any(np.diff(points[:,0]) <= 0):
            return None
        if set(reference['acquisition']) != {'bits', 'rate'}:
            return None
        return reference
    except (OSError, ValueError, KeyError, TypeError):
        return None


def correct_transfer(data, reference, config):
    result = np.asarray(data, dtype=float).copy()
    mask = np.zeros(len(result), dtype=bool)
    if reference is None or reference['acquisition'] != {'bits':config.bits, 'rate':config.rate}:
        return result, mask
    points = np.asarray(reference['points'], dtype=float)
    mask = (result[:,0] >= points[0,0]) & (result[:,0] <= points[-1,0])
    x = np.log10(points[:,0]); frequency = np.log10(result[mask,0])
    result[mask,1] -= np.interp(frequency,x,points[:,1])
    phase = np.rad2deg(np.unwrap(np.deg2rad(points[:,2])))
    result[mask,2] -= np.interp(frequency,x,phase)
    return result, mask
