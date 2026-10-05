#!/usr/bin/env python3
"""Captura ADC16 sostenido, valida continuidad y restaura el perfil ADC observado."""
import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from monitor.v12.receiver.unoq_usb import Connection
from monitor.v12.receiver.unoq_config_receiver import OutputReceiver
from monitor.v12.receiver.unoq_acquisition import Configuration


def wait_configuration(receiver, expected=None, timeout=5):
    """Leer hardware real; receiver.config empieza con un valor por defecto."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        receiver.pump()
        observed = receiver.decoder.config
        status = receiver.decoder.status
        if observed is not None and status is not None:
            actual = Configuration(status['bits'], status['rate'])
            if observed == actual and (expected is None or actual == expected):
                return actual
    raise TimeoutError(f'No llegaron muestras del perfil esperado: {expected}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--rate', type=int, choices=(50000, 62500), default=62500)
    parser.add_argument('--serial', default='1060031107')
    args = parser.parse_args(argv)
    if args.seconds <= 0:
        parser.error('--seconds debe ser positivo')
    folder = ROOT / 'capturas/adc16_rate' / ('test_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True, exist_ok=True)
    target = Configuration(16, args.rate)
    report = {'timestamp': datetime.now().isoformat(), 'target': asdict(target),
              'requested_seconds': args.seconds, 'passed': False, 'errors': [],
              'restoration': {'attempted': False, 'verified': False},
              'raw_capture': 'stream.scp'}
    receiver = None
    initial_config = None
    pairs_count = 0
    previous = None
    continuity_errors = 0
    out_of_range = 0
    measuring = False

    def on_samples(batch):
        nonlocal pairs_count, previous, continuity_errors, out_of_range
        if not measuring:
            return
        for timestamp, adc_in, adc_out, index in batch:
            if previous is not None:
                if ((timestamp - previous[0]) & 0xffffffff) != target.period or ((index - previous[1]) & 0xffffffff) != 1:
                    continuity_errors += 1
            previous = timestamp, index
            out_of_range += not (0 <= adc_in <= target.maximum and 0 <= adc_out <= target.maximum)
        pairs_count += len(batch)

    try:
        with Connection(args.serial) as conn, (folder / 'stream.scp').open('wb') as raw:
            conn.socket.settimeout(0.05)
            original_read = conn.read

            def recorded_read():
                data = original_read()
                raw.write(data)
                return data

            conn.read = recorded_read
            receiver = OutputReceiver(conn, on_samples)
            try:
                initial_config = wait_configuration(receiver)
                report['initial_config'] = asdict(initial_config)
                generator = receiver.generator()  # Query only; never SET_GENERATOR.
                report['generator_before'] = asdict(generator.active)
                report['generator_running_before'] = generator.running
                print(f'Perfil observado: {initial_config}; probando {target}', flush=True)
                receiver.configure(target)
                wait_configuration(receiver, target)
                report['target_status'] = dict(receiver.decoder.status)
                measuring = True
                started = time.monotonic()
                while time.monotonic() - started < args.seconds:
                    receiver.pump()
                elapsed = time.monotonic() - started
                measuring = False
                status = dict(receiver.decoder.status)
                report.update(pairs=pairs_count, elapsed_s=elapsed, actual_rate_hz=pairs_count / elapsed,
                              final_status=status, continuity_errors=continuity_errors, out_of_range=out_of_range)
                if pairs_count < args.rate * elapsed * .95:
                    report['errors'].append('Tasa recibida inferior al 95% del objetivo')
                if status.get('dropped', 0) or status.get('fatal', 0):
                    report['errors'].append('Firmware informó dropped/fatal')
                if continuity_errors or out_of_range:
                    report['errors'].append('Continuidad o rango inválidos')
            finally:
                measuring = False
                if initial_config is not None:
                    report['restoration']['attempted'] = True
                    report['restoration']['requested'] = asdict(initial_config)
                    try:
                        receiver.configure(initial_config)
                        restored = wait_configuration(receiver, initial_config)
                        report['restoration'].update(observed=asdict(restored), verified=restored == initial_config,
                                                     status=dict(receiver.decoder.status))
                        after = receiver.generator()  # Observation only; finished pulses stay finished.
                        report['generator_after'] = asdict(after.active)
                        report['generator_running_after'] = after.running
                        report['generator_configuration_unchanged'] = report.get('generator_before') == asdict(after.active)
                    except Exception as exc:
                        report['errors'].append(f'Restauración: {type(exc).__name__}: {exc}')
                receiver.close()
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        report['pairs_observed'] = pairs_count
        report['passed'] = not report['errors'] and report['restoration']['verified'] and 'elapsed_s' in report
        path = folder / 'informe.json'
        path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
        print(f'Informe: {path}', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
