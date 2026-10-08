"""Measured loopback reference; never extrapolate or cross ADC profiles."""
import json
from pathlib import Path
import numpy as np

CALIBRATION_PATH = Path(__file__).resolve().parent / 'calibraciones' / 'bode_v10.json'
CALIBRATION_DIR = CALIBRATION_PATH.parent


def instrument_identity(serial):
    """Identify the active App Lab deployment; fail closed if ambiguous."""
    from monitor.v15.receiver.unoq_usb import adb
    import re
    import shlex
    from subprocess import TimeoutExpired
    try:
        names = adb('-s', serial, 'shell', 'docker', 'ps', '--format', '{{.Names}}').splitlines()
        apps = [n for n in names if n in ('scope-pulse-us-v13-main-1', 'scope-wav-v12-audio-main-1')]
        if len(apps) != 1: return None
        app = apps[0]
        template = '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
        root = adb('-s', serial, 'shell', 'docker inspect ' + shlex.quote(app)
                   + ' --format ' + shlex.quote(template))
        if not root.startswith('/home/arduino/ArduinoApps/') or not root.endswith('/.cache'): return None
        digest = adb('-s', serial, 'shell', 'sha256sum ' + shlex.quote(root+'/sketch/sketch.ino.bin')).split()[0]
        if not re.fullmatch('[0-9a-f]{64}', digest): return None
        return {'board_serial': serial, 'app': app, 'firmware_sha256': digest}
    except (RuntimeError, OSError, IndexError, TimeoutExpired):
        return None


def find_reference(instrument, config, method):
    for path in sorted(CALIBRATION_DIR.glob('bode_reference_*.json'), reverse=True):
        reference = load_reference(path, instrument)
        if (reference and reference.get('validation', {}).get('accepted') is True
                and reference.get('method') == method
                and reference['acquisition'] == {'bits': config.bits, 'rate': config.rate}):
            return reference
    return None


def load_reference(path=CALIBRATION_PATH, instrument=None):
    try:
        reference = json.loads(Path(path).read_text())
        points = np.asarray(reference['points'], dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2:
            return None
        if not np.all(np.isfinite(points)) or np.any(points[:,0] <= 0) or np.any(np.diff(points[:,0]) <= 0):
            return None
        if set(reference['acquisition']) != {'bits', 'rate'}:
            return None
        # Bits/rate alone do not identify the ADC clock or inter-channel delay.
        # No reference is trusted until the connected instrument is identified.
        if instrument is None or reference.get('instrument') != instrument:
            return None
        return reference
    except (OSError, ValueError, KeyError, TypeError):
        return None


def correct_transfer(data, reference, config, instrument=None):
    result = np.asarray(data, dtype=float).copy()
    mask = np.zeros(len(result), dtype=bool)
    if (reference is None or instrument is None or reference.get('instrument') != instrument
            or reference['acquisition'] != {'bits':config.bits, 'rate':config.rate}):
        return result, mask
    points = np.asarray(reference['points'], dtype=float)
    mask = (result[:,0] >= points[0,0]) & (result[:,0] <= points[-1,0])
    x = np.log10(points[:,0]); frequency = np.log10(result[mask,0])
    result[mask,1] -= np.interp(frequency,x,points[:,1])
    phase = np.rad2deg(np.unwrap(np.deg2rad(points[:,2])))
    result[mask,2] -= np.interp(frequency,x,phase)
    return result, mask
