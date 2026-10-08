#!/usr/bin/env python3
"""Comparación ADC16 50/62.5 kHz con A0 conectado directamente a A2/A3 y masa común."""
import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnosticos.verificar_adc16_62k5 import wait_configuration
from monitor.historico.v12.receiver.unoq_acquisition import Configuration
from monitor.historico.v12.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v12.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v12.receiver.unoq_usb import Connection

DTYPE = np.dtype([('timestamp_us', '<u4'), ('adc_in', '<u2'), ('adc_out', '<u2'), ('index', '<u4')])


def fit_tone(records, rate, frequency):
    t = ((records['timestamp_us'].astype(np.int64) - int(records['timestamp_us'][0])) & 0xffffffff) * 1e-6
    values = np.column_stack((records['adc_in'], records['adc_out'])) / 65535 * 3.3
    def basis(f):
        return np.column_stack((np.cos(2*np.pi*f*t), np.sin(2*np.pi*f*t), np.ones(len(t))))
    def loss(f):
        b = basis(f)
        fitted = np.linalg.lstsq(b, values[:, 0], rcond=None)[0]
        return float(np.mean((values[:, 0] - b @ fitted)**2))
    frequencies = np.fft.rfftfreq(len(t), 1/rate)
    energy = abs(np.fft.rfft((values[:, 0]-values[:, 0].mean()) * np.hanning(len(t))))
    chosen = np.flatnonzero((frequencies > frequency*.9) & (frequencies < frequency*1.1))
    peak = frequencies[chosen[np.argmax(energy[chosen])]]
    width = rate/len(t)
    left, right = max(1, peak-width), peak+width
    golden = (5**.5-1)/2
    for _ in range(28):
        f1, f2 = right-golden*(right-left), left+golden*(right-left)
        if loss(f1) < loss(f2):
            right = f2
        else:
            left = f1
    actual = (left+right)/2
    b = basis(actual)
    channels = []
    for y in values.T:
        fitted = np.linalg.lstsq(b, y, rcond=None)[0]
        channels.append(dict(amplitude_peak_v=float(np.hypot(*fitted[:2])), offset_v=float(fitted[2]),
                             phase_deg=float(np.degrees(np.arctan2(-fitted[1], fitted[0]))),
                             residual_rms_v=float(np.std(y-b@fitted))))
    return dict(fitted_frequency_hz=actual, channels=channels,
                amplitude_ratio_a3_a2=channels[1]['amplitude_peak_v']/max(channels[0]['amplitude_peak_v'], 1e-12),
                phase_a3_a2_deg=(channels[1]['phase_deg']-channels[0]['phase_deg']+180)%360-180)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--frequencies', type=int, nargs='+', default=[2000, 10000, 20000])
    parser.add_argument('--serial', default='1060031107')
    args = parser.parse_args(argv)
    if args.seconds <= 0 or any(f < 1 or f > 20000 for f in args.frequencies):
        parser.error('Duración positiva y frecuencias entre 1 y 20000 Hz')
    folder = ROOT/'capturas/adc16_rate'/('analog_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True)
    report = dict(passed=False, errors=[], profiles=[], comparisons=[], restoration={},
                  direct_wiring_confirmed=True, note='DAC12 no valida ENOB16; amplitud/residuo comparativos sin umbral artificial de 1%.')
    before = previous_generator = None
    modified_generator = False
    analyses = []
    try:
        with Connection(args.serial) as conn, (folder/'stream.scp').open('wb') as raw:
            conn.socket.settimeout(.02)
            read = conn.read
            def recorded():
                data = read()
                raw.write(data)
                return data
            conn.read = recorded
            receiver = OutputReceiver(conn, lambda samples: None)
            try:
                before = wait_configuration(receiver)
                reply = receiver.generator()
                previous_generator = reply.active
                report['before'] = dict(acquisition=asdict(before), generator=asdict(previous_generator), running=reply.running)
                # Reapplying enabled completed pulses/sweeps would retrigger them.
                # Refuse before changing anything unless continuous state can be restored exactly.
                if previous_generator.wave == 4 or previous_generator.mode != 0 or reply.running != bool(previous_generator.enabled):
                    raise RuntimeError('Perfil transitorio del generador: no se modifica para evitar retrigger o perder su progreso')
                for frequency in args.frequencies:
                    modified_generator = True  # An ACK failure still requires an attempted restore.
                    receiver.generator(GeneratorConfig(1, 1, 0, frequency*1000, frequency*1000, 500, 3500, 1000))
                    for rate in (50000, 62500):
                        config = Configuration(16, rate)
                        receiver.configure(config)
                        wait_configuration(receiver, config)
                        row = dict(bits=16, rate=rate, frequency_hz=frequency, binary=f'{frequency}Hz_{rate}Hz.bin')
                        report['profiles'].append(row)
                        count = 0
                        with (folder/row['binary']).open('wb') as capture:
                            def consume(samples):
                                nonlocal count
                                output = np.empty(len(samples), dtype=DTYPE)
                                for column, name in enumerate(DTYPE.names):
                                    output[name] = [sample[column] for sample in samples]
                                capture.write(output.tobytes())
                                count += len(samples)
                            receiver.on_samples = consume
                            started = time.monotonic()
                            while time.monotonic()-started < args.seconds:
                                receiver.pump()
                            elapsed = time.monotonic()-started
                            receiver.on_samples = lambda samples: None
                        row.update(pairs=count, elapsed_s=elapsed, actual_rate_hz=count/elapsed, status=dict(receiver.decoder.status))
                        row['passed'] = count >= rate*elapsed*.95 and not row['status']['dropped'] and not row['status']['fatal']
                        analyses.append(row)
                        print(json.dumps(row), flush=True)
                        if not row['passed']:
                            raise RuntimeError('Caudal o estado de adquisición inválidos')
            finally:
                receiver.on_samples = lambda samples: None
                try:
                    if before is not None:
                        receiver.configure(before)
                        wait_configuration(receiver, before)
                    if previous_generator is not None and modified_generator:
                        receiver.generator(previous_generator)
                    after = receiver.generator()
                    report['after'] = dict(acquisition=asdict(receiver.decoder.config), generator=asdict(after.active), running=after.running)
                    report['restoration']['verified'] = report.get('before') == report['after']
                    if not report['restoration']['verified']:
                        report['errors'].append('Estado restaurado distinto del observado inicialmente')
                except Exception as exc:
                    report['errors'].append(f'Restauración: {exc}')
                receiver.close()
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    # All fitting and continuity checks happen offline, avoiding GUI/transport backpressure.
    try:
        for row in analyses:
            records = np.fromfile(folder/row['binary'], dtype=DTYPE)
            gaps = np.count_nonzero((np.diff(records['timestamp_us']) & 0xffffffff) != 1000000//row['rate'])
            gaps += np.count_nonzero((np.diff(records['index']) & 0xffffffff) != 1)
            row['continuity_errors'] = int(gaps)
            row.update(fit_tone(records[-16384:], row['rate'], row['frequency_hz']))
            if gaps:
                report['errors'].append(f"Discontinuidad en {row['binary']}")
        for frequency in args.frequencies:
            rows = [r for r in analyses if r['frequency_hz'] == frequency]
            if len(rows) != 2:
                continue
            comparison = dict(frequency_hz=frequency, channels=[])
            for baseline, candidate in zip(rows[0]['channels'], rows[1]['channels']):
                comparison['channels'].append(dict(
                    amplitude_change_percent=100*(candidate['amplitude_peak_v']/baseline['amplitude_peak_v']-1),
                    offset_change_mv=1000*(candidate['offset_v']-baseline['offset_v']),
                    residual_ratio=candidate['residual_rms_v']/max(baseline['residual_rms_v'], 1e-12)))
            report['comparisons'].append(comparison)
    except Exception as exc:
        report['errors'].append(f'Análisis: {type(exc).__name__}: {exc}')
    report['passed'] = not report['errors'] and len(analyses) == 2*len(args.frequencies) and report['restoration'].get('verified', False)
    path = folder/'informe.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    print(path, flush=True)
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
