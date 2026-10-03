#!/usr/bin/env python3
"""Prueba continuidad de 16 bits sin modificar firmware; conserva resumen y cola."""
import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from transport.unoq_acquisition import Configuration
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_switch import Mode
from transport.unoq_usb import Connection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--rate', type=int, default=31250)
    args = parser.parse_args()
    config = Configuration(16, args.rate)
    if args.seconds <= 0:
        parser.error('--seconds debe ser positivo')
    report = {'bits': 16, 'rate': args.rate, 'seconds_requested': args.seconds,
              'pairs': 0, 'passed': False, 'error': None}
    tail = deque(maxlen=128)
    def receive(records):
        report['pairs'] += len(records)
        tail.extend(records)
    started = None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        with Connection('1060031107') as connection:
            connection.socket.settimeout(.01)
            receiver = OutputReceiver(connection, receive)
            try:
                receiver.configure(config)
                receiver.select(Mode.SPI)
                report['generator'] = repr(receiver.generator().active)
                report['pairs'] = 0
                started = time.monotonic()
                progress = started + 10
                while time.monotonic() - started < args.seconds:
                    receiver.pump()
                    if time.monotonic() >= progress:
                        print(f"{time.monotonic()-started:.1f} s: {report['pairs']} pares válidos", flush=True)
                        progress += 10
                report['passed'] = report['pairs'] > 0
            finally:
                try:
                    receiver.configure(Configuration())
                    report['restored_default'] = True
                except Exception as exc:
                    report['restore_error'] = repr(exc)
                receiver.close()
    except Exception as exc:
        report['error'] = repr(exc)
    finally:
        report['seconds_measured'] = time.monotonic()-started if started else 0
        report['tail'] = list(tail)
        output = ROOT/'diagnosticos/resultados_usb'/f'{stamp}_estabilidad_16bits.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2)+'\n')
        print(output, flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
