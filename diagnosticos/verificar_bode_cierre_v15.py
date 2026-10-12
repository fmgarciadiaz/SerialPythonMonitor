"""Ensayo físico Bode con GUI Qt offscreen; conserva calibraciones existentes."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import json
import os
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from monitor.historico.v15.app import SerialMonitorWindow, OutputWorker, QtWidgets, QtCore
from monitor.historico.v15.receiver.unoq_acquisition import Configuration
from monitor.historico.v15.receiver.unoq_switch import Mode
from monitor.historico.v15.receiver.unoq_usb import adb
from monitor.historico.v15.bode_calibration import instrument_identity


def main():
    serial = '1060031107'
    if 'ESTAB' in adb('-s', serial, 'shell', 'ss -tn sport = :8766'):
        raise RuntimeError('Relay ocupado: no ejecutar con otro dueño del Q')
    identity = instrument_identity(serial)
    app = QtWidgets.QApplication([])
    with patch('monitor.historico.v15.app.usb_devices', return_value=[]):
        window = SerialMonitorWindow()
    window.show()
    worker = OutputWorker(serial, Mode.SPI, config=Configuration(14, 40000),
                          autoload=True, initial_generator=window._generator_config())
    window.serial_worker = worker
    errors = []
    worker.acquisition_confirmed.connect(window._acquisition_confirmed)
    worker.instrument_confirmed.connect(window.spectral.bode.set_instrument)
    worker.batch_ready.connect(lambda batch: window.handle_batch(batch))
    worker.generator_confirmed.connect(window._generator_confirmed)
    worker.wav_confirmed.connect(window._wav_confirmed)
    worker.error_occurred.connect(errors.append)
    shutdown = []
    worker.shutdown_confirmed.connect(lambda ok, message: shutdown.append(dict(ok=ok, message=message)))
    thread = QtCore.QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit, QtCore.Qt.ConnectionType.DirectConnection)
    thread.start()
    report = dict(instrument=identity, adc=dict(bits=14,rate=40000),
                  gui='Qt offscreen', cases=[], ok=False)
    path = ROOT / 'diagnosticos/resultados_cierre' / (datetime.now().strftime('%Y%m%d_%H%M%S')+'_bode_v15.json')
    def wait(predicate, timeout):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            app.processEvents()
            if errors:
                raise RuntimeError(str(errors))
            if predicate():
                return
            time.sleep(.002)
        raise TimeoutError('Operación Bode sin finalizar')
    try:
        wait(lambda: window._generator_state_known and window.spectral.bode.instrument==identity,20)
        for method, index in (('tone',0),('pulse_h1',1),('sweep',2),('chirp',2)):
            window.spectral.select_bode(index)
            panel = window.spectral.bode.panels[index]
            if index == 2:
                panel.method.setCurrentIndex(int(method=='chirp'))
            panel.start.setValue(20)
            panel.end.setValue(5000)
            panel.calibrated.setChecked(False)
            wait(lambda: window._generator_requested is None,10)
            started = time.monotonic()
            panel.begin()
            if not panel.active:
                raise RuntimeError(panel.status.text())
            wait(lambda: not panel.active,60)
            data = np.asarray(panel.result)
            if data.ndim != 2 or len(data) < 3:
                raise RuntimeError(method+': '+panel.status.text())
            valid = np.isfinite(data).all(axis=1)
            if valid.sum() < 3:
                raise RuntimeError(method+': sin puntos válidos')
            entry = dict(method=method, elapsed=time.monotonic()-started,
                         points=len(data), valid=int(valid.sum()),
                         gain_abs_p95_db=float(np.percentile(abs(data[valid,1]),95)),
                         phase_abs_p95_deg=float(np.percentile(abs((data[valid,2]+180)%360-180),95)),
                         status=panel.status.text(),
                         curve_preview=data[::max(1,len(data)//500)].tolist())
            report['cases'].append(entry)
            path.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({k:v for k,v in entry.items() if k!='curve_preview'}),flush=True)
        report['ok'] = True
        report['precision_accepted'] = False
        report['precision_note'] = 'Ensayo funcional; confirmar cableado antes de aceptar precisión de transferencia.'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        for panel in window.spectral.bode.panels:
            if panel.active:
                panel.cancel()
        worker.stop()
        deadline = time.monotonic()+20
        while thread.isRunning() and time.monotonic()<deadline:
            app.processEvents()
            time.sleep(.01)
        report['worker_finished'] = not thread.isRunning()
        report['shutdown'] = shutdown
        if thread.isRunning():
            # Retain thread ownership until it finishes; never destroy a live QThread.
            while thread.isRunning():
                app.processEvents()
                time.sleep(.1)
        app.processEvents()
        window.serial_worker = None
        window.close()
        path.write_text(json.dumps(report,indent=2)+'\n')
        print('Reporte: '+str(path),flush=True)


if __name__ == '__main__':
    main()
