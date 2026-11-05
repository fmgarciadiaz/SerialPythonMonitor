"""Offline V20 mixed-view stage profile; never connects to Scope Q."""
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.history import SampleHistory
from monitor.v20.receiver.unoq_acquisition import Configuration

PYTHON = '/Users/fmgarciadiaz/opt/anaconda3/envs/Python_3_13_DataScience/bin/python'
RF_RATE = 1_860_465
RF_COUNT = 3_720_930
AUDIO_COUNT = 80_000


def history(values, wrapped):
    result = SampleHistory(len(values))
    if wrapped:
        # Full logical window in two ring-backed segments.
        result.extend(np.concatenate((values[-4096:], values[:-4096])))
        result.extend(values[-4096:])
    else:
        result.extend(values)
    return result


def quantile(values, q):
    return float(np.percentile(values, q)) if values else None


def vector_extrema_indices(hist, start, end, pixels):
    """Candidate: keep V19's four picks per block, assemble NumPy arrays."""
    count = end-start
    if count <= pixels*4: return np.arange(count, dtype=np.intp)
    stride = max(1, math.ceil(count/max(1, pixels)))
    picked = []; logical_offset = 0
    for part in hist.window_parts(start, end):
        if not np.isfinite(part).all(): return None
        blocks = len(part)//stride
        if blocks:
            matrix = part[:blocks*stride].reshape(blocks, stride)
            offsets = logical_offset + np.arange(blocks, dtype=np.intp)*stride
            picked.append(np.concatenate((offsets, offsets+stride-1,
                                          offsets+matrix.argmin(axis=1),
                                          offsets+matrix.argmax(axis=1))))
        tail = blocks*stride
        if tail < len(part):
            picked.append(np.asarray((logical_offset+tail, logical_offset+len(part)-1,
                                      logical_offset+tail+int(np.argmin(part[tail:])),
                                      logical_offset+tail+int(np.argmax(part[tail:]))), dtype=np.intp))
        logical_offset += len(part)
    return np.unique(np.concatenate(picked))


def main():
    if sys.executable != PYTHON:
        raise SystemExit(f'Use {PYTHON}; got {sys.executable}')
    qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    out = ROOT/'diagnosticos/resultados_v20/mixed_profile_20261103'
    out.mkdir(parents=True, exist_ok=True)
    rf_times = np.arange(RF_COUNT, dtype=float)*(1e6/RF_RATE)
    # Fast square edges retain the costly crossing work of the real display.
    rf_values = np.where((np.arange(RF_COUNT) % 53) < 26, 2.2, 1.1).astype(float)
    audio_times = np.linspace(rf_times[0], rf_times[-1], AUDIO_COUNT)
    audio_values = 1.65 + .25*np.sin(np.arange(AUDIO_COUNT)*.1)
    rows = []
    with patch('monitor.v20.app.usb_devices', return_value=[]):
        w = SerialMonitorWindow()
    try:
        w.render_timer.stop(); w.resize(1280, 800); w.show(); qt.processEvents()
        w.known_columns = ['CH1', 'RADIO']; w.selected_columns = {'CH1': True, 'RADIO': True}
        w._update_curve_items(['CH1', 'RADIO'])
        w.applied_configuration = Configuration(8, RF_RATE)
        w.current_dt_us = 1e6/RF_RATE; w.current_fs_hz = RF_RATE
        w.sample_counter = RF_COUNT; w.h_scale = RF_COUNT; w.h_pos = 0
        w.x_axis_time_mode = True; w.trigger_enabled = False; w.is_running = True
        w.detail_slider.setValue(50); w.active_meas_channel = 'CH1'
        w.scope_cursors.states[0].enabled = False
        painted = [0]
        w.plot_widget.paint_observer = lambda ms: painted.__setitem__(0, painted[0]+1)

        histories = {}
        for wrapped in (False, True):
            audio = {'Tiempo (us)': history(audio_times, wrapped),
                     'RADIO': history(audio_values, wrapped)}
            histories[wrapped] = (history(rf_times, wrapped), history(rf_values, wrapped),
                                  SimpleNamespace(rate=40000, sample_numbers=history(np.arange(AUDIO_COUNT), wrapped),
                                                  series=audio, counter=AUDIO_COUNT))
        timings = {(candidate, wrapped, due): {'draw': [], 'measure': [], 'extrema': [], 'total': [], 'paint_count': []}
                   for candidate in (False, True) for wrapped in (False, True) for due in (False, True)}
        current = [None]
        originals = {}
        for name, key in (('_draw_display_frame', 'draw'),
                          ('_update_live_measurements', 'measure'),
                          ('_history_window_extrema_indices', 'extrema')):
            original = getattr(w, name); originals[name] = original
            def timed(*args, _fn=original, _key=key, **kwargs):
                start = time.perf_counter()
                try:
                    call = vector_extrema_indices if _key == 'extrema' and current[0][0] else _fn
                    return call(*args, **kwargs)
                finally: timings[current[0]][_key].append((time.perf_counter()-start)*1000)
            setattr(w, name, timed)
        try:
            for repeat in range(7):
                # Alternate baseline/candidate and reverse the four-case order.
                cases = [(False,False),(True,True),(False,True),(True,False)]
                if repeat % 2: cases.reverse()
                variants = (False, True) if repeat % 2 else (True, False)
                for wrapped, due in cases:
                    for candidate in variants:
                        current[0] = (candidate,wrapped,due)
                        w.series['Tiempo (us)'], w.series['CH1'], w.radio_stream = histories[wrapped]
                        w._last_measurement_update = 0 if due else time.perf_counter()
                        before = painted[0]; began = time.perf_counter()
                        w._render_mixed_temporal(['CH1', 'RADIO'], {'RADIO'})
                        elapsed = (time.perf_counter()-began)*1000
                        qt.processEvents()
                        timings[current[0]]['total'].append(elapsed)
                        timings[current[0]]['paint_count'].append(painted[0]-before)
        finally:
            for name, original in originals.items(): setattr(w, name, original)
        for (candidate, wrapped, due), data in timings.items():
            summary = {key: {'median_count' if key=='paint_count' else 'median_ms': statistics.median(vals[1:]),
                             'p95_count' if key=='paint_count' else 'p95_ms': quantile(vals[1:], 95), 'values': vals[1:]}
                       for key, vals in data.items() if len(vals)>1}
            summary['other_median_ms'] = summary['total']['median_ms'] - sum(summary[k]['median_ms'] for k in ('draw','measure','extrema') if k in summary)
            rows.append({'candidate': candidate, 'wrapped': wrapped, 'measurement_due': due,
                         'rf_count': RF_COUNT, 'audio_count': AUDIO_COUNT,
                         'plot_width': w.plot_widget.getViewBox().width(), 'summary': summary})
    finally:
        w.close(); qt.processEvents()
    report = {'scope': 'Offline Qt offscreen; no Q, no physical FPS; six alternated measured repetitions per case', 'python': sys.executable,
              'detail': 50, 'waveform': 'square period 53 RF samples', 'cases': rows}
    path = out/'profile_ab.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(path)
    for row in rows:
        print(row['candidate'], row['wrapped'], row['measurement_due'],
              {k: round(v['median_ms'], 3) for k,v in row['summary'].items() if isinstance(v, dict) and 'median_ms' in v})


if __name__ == '__main__': main()
