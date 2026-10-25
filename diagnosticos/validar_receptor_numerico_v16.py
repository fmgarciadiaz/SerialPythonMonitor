"""Sustained native numeric receiver check with one Q reader and exact restore.

Run only after checking that no other monitor owns the Q. This does not flash,
start an app, or alter the generator. CRC, sequence, epoch, frame geometry,
index and timestamp continuity are enforced by the production receiver.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_wav import State


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--profile', action='append', default=[],
                        help='bits:rate; default 8:1221374 and 10:909090')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error('--seconds must be positive')
    profiles = [Configuration(*map(int, value.split(':', 1))) for value in
                (args.profile or ['8:1221374', '10:909090'])]
    output = args.output or ROOT / 'diagnosticos/resultados_v16' / (
        datetime.now().strftime('numeric_sustained_%Y%m%d_%H%M%S.json'))
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'serial': args.serial, 'scope': 'Production V16 numeric receiver, '
              'continuous SPI integrity and status; generator preserved; no analog acceptance',
              'cases': [], 'ok': False, 'restored': False}

    def save():
        output.write_text(json.dumps(report, indent=2) + '\n')

    sample_count = 0

    def collect(batch):
        nonlocal sample_count
        sample_count += len(batch)

    save()
    with Connection(args.serial) as connection:
        receiver = OutputReceiver(connection, collect)
        prior = None
        generator = None
        try:
            # Read first. Never switch an existing UART session to SPI.
            start = time.monotonic()
            while receiver.decoder.mode is None and time.monotonic() - start < 3:
                receiver.pump()
            if receiver.decoder.mode != Mode.SPI:
                raise RuntimeError('Q is not in SPI mode; refusing to change its route')
            receiver.select(Mode.SPI)
            prior = receiver.config
            generator = receiver.generator().active
            receiver.wav_request()
            deadline = time.monotonic() + 3
            while receiver.wav_pending and time.monotonic() < deadline:
                receiver.pump()
            if receiver.wav_pending or receiver.wav_status is None:
                raise RuntimeError('WAV status unavailable')
            report['prior'] = {'configuration': asdict(prior),
                               'generator': asdict(generator),
                               'wav_state': receiver.wav_status.state.name,
                               'mode': 'SPI'}
            save()
            if receiver.wav_status.state != State.IDLE:
                raise RuntimeError('WAV is active; refusing to change ADC configuration')
            receiver.decoder.numeric = True
            for config in profiles:
                receiver.configure(config)
                sample_count = 0
                statuses = 0
                dropped = fatal = queue_peak = 0
                first_status = last_status = None
                case = {'configuration': asdict(config), 'status': 'RUNNING'}
                report['cases'].append(case)
                save()
                start = time.monotonic()
                heartbeat = start
                while time.monotonic() - start < args.seconds:
                    receiver.pump()
                    for status in receiver.decoder.statuses:
                        if 'produced' not in status:
                            continue
                        statuses += 1
                        first_status = first_status or status
                        last_status = status
                        dropped = max(dropped, status['dropped'])
                        fatal = max(fatal, status['fatal'])
                        queue_peak = max(queue_peak, status['queue_peak'])
                    now = time.monotonic()
                    if now - heartbeat >= 10:
                        heartbeat = now
                        case.update(elapsed_s=round(now - start, 3),
                                    samples=sample_count, status_frames=statuses)
                        save()
                        print('PROGRESS', config.bits, config.rate,
                              round(now-start), sample_count, flush=True)
                elapsed = time.monotonic() - start
                case.update(elapsed_s=elapsed, samples=sample_count,
                            host_delivery_rate=sample_count / elapsed,
                            status_frames=statuses, dropped=dropped, fatal=fatal,
                            queue_peak=queue_peak,
                            first_status=first_status, last_status=last_status)
                if not statuses or not sample_count:
                    raise RuntimeError('No numeric samples or native status frames')
                if dropped or fatal:
                    raise RuntimeError('Q reported dropped nodes or fatal DMA errors')
                if sample_count < config.actual_rate * elapsed * .99:
                    raise RuntimeError('Host delivery below 99% of nominal rate')
                case['status'] = 'PASS'
                save()
                print('PASS', config.bits, config.rate, sample_count, flush=True)
            report['ok'] = True
        except Exception as exc:
            report['error'] = str(exc)
            if report['cases'] and report['cases'][-1]['status'] == 'RUNNING':
                report['cases'][-1].update(status='FAIL', error=str(exc))
            save()
            raise
        finally:
            if prior is not None:
                try:
                    if receiver.config != prior:
                        receiver.configure(prior)
                    actual_generator = receiver.generator().active
                    if generator is not None and actual_generator != generator:
                        receiver.generator(generator)
                    report['restored'] = (receiver.config == prior and
                                          receiver.generator().active == generator)
                    if report['restored']:
                        before = sample_count
                        started = time.monotonic()
                        restored_statuses = 0
                        while time.monotonic() - started < 3:
                            receiver.pump()
                            restored_statuses += sum('produced' in status
                                                     for status in receiver.decoder.statuses)
                        report['restoration_integrity'] = {
                            'seconds': time.monotonic() - started,
                            'samples': sample_count - before,
                            'status_frames': restored_statuses,
                            'ok': sample_count > before and restored_statuses > 0}
                except Exception as exc:
                    report['restore_error'] = str(exc)
                    report['restored'] = False
            if not report['restored'] or not report.get('restoration_integrity', {}).get('ok'):
                report['ok'] = False
            save()
            print('REPORT', output, 'RESTORED', report['restored'], flush=True)


if __name__ == '__main__':
    main()
