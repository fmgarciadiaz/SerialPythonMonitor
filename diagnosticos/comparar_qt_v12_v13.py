"""Compare deterministic rendering in separate Qt5/Qt6 processes; no hardware."""
import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=('v12', 'v13'), required=True)
    parser.add_argument('--frames', type=int, default=100)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5' if args.version == 'v12' else 'PyQt6'
    import numpy as np
    app_module = importlib.import_module('monitor.' + args.version + '.app')
    qt, pg = app_module.QtCore, app_module.pg
    if args.version == 'v13':
        app_module.prepare_platform_plugins()
    app = app_module.QtWidgets.QApplication([])
    # Equal style prevents comparing Fusion to a platform default.
    app.setStyle('Fusion')
    with patch.object(app_module, 'usb_devices', return_value=[]):
        window = app_module.SerialMonitorWindow()
    for dial in window.findChildren(app_module.QtWidgets.QDial):
        dial.setNotchesVisible(False)
    window.resize(1700, 1000)
    window.show()
    window.render_timer.stop()
    app.processEvents()
    results = []
    for rate in (125000, 62500):
        indices = np.arange(250000)
        vin = 1.65 + np.sin(indices * 2*np.pi * 2000 / rate)
        window.sample_numbers.clear()
        window.sample_numbers.extend(indices + 1)
        for name, series in window.series.items():
            series.clear()
            series.extend(indices*1e6/rate if name == 'Tiempo (us)' else vin)
        window.sample_counter = len(indices)
        window.current_fs_hz = rate
        window.current_dt_us = 1e6 / rate
        window.trigger_enabled = False
        window.is_running = True
        for mode, size in ((0, 9000), (0, 50000), (0, 250000), (1, 8192), (2, 8192)):
            window.h_scale = size
            window.spectral.size.setCurrentText('8192')
            window.spectral.set_mode(mode)
            render_ms, paint_ms = [], []
            for frame in range(args.frames + 10):
                # Advance complete deterministic history for each frame.
                start = window.sample_counter
                overlap = (0, .5, .75)[window.spectral.overlap.currentIndex()]
                hop = max(int(8192*(1-overlap)), int(np.ceil(rate*window.spectral.seconds.value()/512)), int(np.ceil(rate/30)))
                sample = np.arange(start, start + (hop if mode == 2 else 1024))
                values = 1.65 + np.sin(sample * 2*np.pi * 2000/rate)
                window.sample_numbers.extend(sample + 1)
                for name, history in window.series.items():
                    history.extend(sample*1e6/rate if name == 'Tiempo (us)' else values)
                window.sample_counter += len(sample)
                window.spectral.last_fast_render = 0
                previous_end = window.spectral.last_end
                before = time.perf_counter()
                window.render_frame() if mode == 0 else window.spectral.render()
                after = time.perf_counter()
                if mode and window.spectral.last_end == previous_end:
                    raise RuntimeError("Benchmark spectral frame did not advance")
                window.repaint()
                app.processEvents()
                painted = time.perf_counter()
                if frame >= 10:
                    render_ms.append((after-before)*1000)
                    paint_ms.append((painted-after)*1000)
            def stats(values):
                return {'median_ms': float(np.median(values)), 'p95_ms': float(np.percentile(values, 95))}
            results.append({'rate': rate, 'mode': ('V(t)', 'FFT', 'heatmap')[mode], 'samples': size,
                            'frames': len(render_ms), 'render': stats(render_ms), 'paint_events': stats(paint_ms)})
    report = {'version': args.version, 'binding': pg.Qt.QT_LIB, 'pyqt': qt.PYQT_VERSION_STR,
              'qt': qt.qVersion(), 'qt_headers': qt.QT_VERSION_STR, 'numpy': np.__version__, 'pyqtgraph': pg.__version__,
              'python': sys.version, 'platform': platform.platform(), 'qpa': app.platformName(),
              'size': [window.width(), window.height()], 'dpr': window.devicePixelRatioF(),
              'style': app.style().objectName(), 'results': results,
              'limitation': 'Synthetic offscreen measurement; excludes acquisition/USB queue and visible display FPS.'}
    window.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(args.output)

if __name__ == '__main__':
    main()
