"""Physical loopback calibration for all supported ADC profiles (monitor disconnected)."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from datetime import date
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
from monitor.v15.app import SerialMonitorWindow, OutputWorker, QtWidgets, QtCore
from monitor.v15.receiver.unoq_acquisition import BITS, RATES, Configuration
from monitor.v15.receiver.unoq_switch import Mode
from monitor.v15.receiver.unoq_usb import adb
from monitor.v15.bode_calibration import instrument_identity, correct_transfer, CALIBRATION_DIR

LIMITS = dict(coverage_min=.9, gain_p95_db=.5, phase_p95_deg=2,
              gain_max_db=1, phase_max_deg=5)


def profiles():
    for bits in BITS:
        for rate in RATES:
            try:
                yield Configuration(bits, rate)
            except ValueError:
                pass


def reference_from(captures, instrument, config, method):
    a, b, check = (np.asarray(c) for c in captures)
    points = []
    for data in (a, b):
        valid = np.isfinite(data).all(axis=1)
        points.append(data[valid])
    if min(map(len, points)) < 3:
        raise ValueError('Referencia insuficiente')
    lo = max(p[0, 0] for p in points); hi = min(p[-1, 0] for p in points)
    frequency = np.geomspace(lo, hi, min(1000, min(map(len, points))))
    gain = []; phase = []
    for data in points:
        gain.append(np.interp(np.log10(frequency), np.log10(data[:, 0]), data[:, 1]))
        unwrapped = np.rad2deg(np.unwrap(np.deg2rad(data[:, 2])))
        phase.append(np.interp(np.log10(frequency), np.log10(data[:, 0]), unwrapped))
    phase[1] -= 360 * round(float(np.median(phase[1] - phase[0])) / 360)
    ref = dict(instrument=instrument, method=method,
               acquisition=dict(bits=config.bits, rate=config.rate),
               points=np.column_stack((frequency, np.mean(gain, axis=0), np.mean(phase, axis=0))).tolist(),
               date=str(date.today()), connection='A0 directly to A2 and A3',
               measurement='First two captures averaged; independent third capture validates correction')
    corrected, mask = correct_transfer(check, ref, config, instrument)
    valid = mask & np.isfinite(corrected).all(axis=1)
    if valid.sum() < 3:
        raise ValueError('Validación insuficiente')
    g = abs(corrected[valid, 1]); p = abs((corrected[valid, 2]+180) % 360-180)
    metrics = dict(coverage_min=min(float(np.isfinite(c[:, 1:]).all(axis=1).mean()) for c in (a,b,check)),
                   gain_error_p95_db=float(np.percentile(g,95)), phase_error_p95_deg=float(np.percentile(p,95)),
                   gain_error_max_db=float(g.max()), phase_error_max_deg=float(p.max()))
    accepted = metrics['coverage_min'] >= LIMITS['coverage_min'] and all(
        metrics[k] <= LIMITS[limit] for k,limit in (
            ('gain_error_p95_db','gain_p95_db'),('phase_error_p95_deg','phase_p95_deg'),
            ('gain_error_max_db','gain_max_db'),('phase_error_max_deg','phase_max_deg')))
    ref['validation'] = dict(accepted=accepted, limits=LIMITS, **metrics)
    return ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--loopback-confirmed', action='store_true', required=True)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--resume-report', type=Path,
                        help='Continue an interrupted report without repeating completed methods')
    parser.add_argument('--bits', type=int, nargs='+', choices=BITS)
    parser.add_argument('--rates', type=int, nargs='+', choices=RATES)
    parser.add_argument('--restore-only', action='store_true',
                        help='Connect, restore ADC14/40 kHz and turn output off, without measuring')
    args = parser.parse_args()
    configs = [c for c in profiles() if (not args.bits or c.bits in args.bits)
               and (not args.rates or c.rate in args.rates)]
    if args.restore_only:configs=[]
    if args.list:
        print(json.dumps([dict(bits=c.bits,rate=c.rate) for c in configs]));return
    if 'ESTAB' in adb('-s', args.serial, 'shell', 'ss -tn sport = :8766'):
        raise RuntimeError('Desconectar el monitor: relay ocupado')
    identity = instrument_identity(args.serial)
    if identity is None:raise RuntimeError('No se pudo identificar el firmware activo')
    stamp = time.strftime('%Y%m%d_%H%M%S')
    output = ROOT / 'diagnosticos/resultados_bode' / f'{stamp}_calibracion_completa.json'
    previous = None
    if args.resume_report:
        previous = json.loads(args.resume_report.read_text())
        if previous['instrument'] != identity:
            raise RuntimeError('El reporte corresponde a otro instrumento/firmware')
        output = args.resume_report
    output.parent.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    with patch('monitor.v15.app.usb_devices',return_value=[]):w = SerialMonitorWindow()
    worker = OutputWorker(args.serial, Mode.SPI, config=Configuration(14,40000),
                          autoload=True, initial_generator=w._generator_config())
    w.serial_worker = worker; errors = []; rows = previous['results'] if previous else []
    completed = {(r['bits'],r['rate'],r['method']) for r in rows}
    worker.acquisition_confirmed.connect(w._acquisition_confirmed)
    worker.instrument_confirmed.connect(w.spectral.bode.set_instrument)
    worker.batch_ready.connect(lambda batch: w.handle_batch(batch))
    worker.generator_confirmed.connect(w._generator_confirmed)
    worker.wav_confirmed.connect(w._wav_confirmed)
    worker.error_occurred.connect(errors.append)
    thread = QtCore.QThread();worker.moveToThread(thread);thread.started.connect(worker.run)
    worker.finished.connect(thread.quit, QtCore.Qt.ConnectionType.DirectConnection);thread.start()
    def wait(test, timeout):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            app.processEvents();time.sleep(.002)
            if errors:raise RuntimeError(str(errors))
            if test():return
        raise TimeoutError('El Q no terminó la operación')
    def save():
        output.write_text(json.dumps(dict(instrument=identity, limits=LIMITS, results=rows),indent=2)+'\n')
    try:
        wait(lambda:w._generator_state_known and w.spectral.bode.instrument==identity,15)
        for config in configs:
            if all((config.bits,config.rate,m) in completed for m in ('tone','sweep','chirp','pulse_h1')):
                continue
            worker.request_output(Mode.SPI,'',config)
            wait(lambda:w.applied_configuration==config,15)
            for method,index in (('tone',0),('sweep',2),('chirp',2),('pulse_h1',1)):
                if (config.bits,config.rate,method) in completed:continue
                row = dict(bits=config.bits,rate=config.rate,method=method,accepted=False)
                if method=='pulse_h1' and config.rate<20000:
                    row['reason']='100 µs ocupa menos de dos muestras; no hay referencia de banda fiable'
                    rows.append(row);save();continue
                w.spectral.select_bode(index);panel = w.spectral.bode.panels[index]
                if index==2:panel.method.setCurrentIndex(int(method=='chirp'))
                panel.start.setValue(20);panel.end.setValue(min(5000,.4*config.rate))
                panel.calibrated.setChecked(False)
                captures = []
                try:
                    for repeat in range(3):
                        wait(lambda:w._generator_requested is None,10)
                        panel.begin()
                        if not panel.active:raise ValueError(panel.status.text())
                        wait(lambda:not panel.active,40)
                        if not panel.result:raise ValueError(panel.status.text())
                        captures.append(np.asarray(panel.result))
                    ref = reference_from(captures,identity,config,method)
                    row.update(ref['validation']);row['band_hz']=[panel.start.value(),panel.end.value()]
                    if row['accepted']:
                        if instrument_identity(args.serial)!=identity:raise RuntimeError('Cambió el firmware')
                        path = CALIBRATION_DIR / f'bode_reference_{stamp}_{args.serial}_{config.bits}bit_{config.rate}_{method}.json'
                        path.write_text(json.dumps(ref,indent=2)+'\n');row['reference']=path.name
                except (ValueError,TimeoutError) as exc:
                    if panel.active:panel.cancel()
                    row['reason']=str(exc)
                rows.append(row);save();print(json.dumps(row),flush=True)
    finally:
        try:
            if not errors:
                for panel in w.spectral.bode.panels:
                    if panel.active:panel.cancel()
                worker.request_output(Mode.SPI,'',Configuration(14,40000))
                wait(lambda:w.applied_configuration==Configuration(14,40000),15)
        finally:
            worker.stop();thread.quit();thread.wait(10000);w.serial_worker=None;w.close();save()
    if args.restore_only:print('Restaurado ADC14/40 kHz; cierre con salida apagada',flush=True)
    print('Reporte:',output,flush=True)

if __name__=='__main__':main()
