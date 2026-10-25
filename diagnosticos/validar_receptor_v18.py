"""Bounded physical smoke of V18 child; preserves installed Q programs.
Run only with the Q exclusive. Every session captures and restores its baseline.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from monitor.v18.io.receiver_process import ReceiverProcess
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_switch import Mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--bits', type=int, default=8)
    parser.add_argument('--rate', type=int, default=1600000)
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    owner = ReceiverProcess(args.serial, Mode.SPI, Configuration(args.bits, args.rate))
    report = dict(bits=args.bits, rate=args.rate, samples=0, batches=0, signals=[], terminal=None)
    started = None
    deadline = time.monotonic() + 30 + args.seconds
    owner.start()
    try:
        while time.monotonic() < deadline:
            for event in owner.poll():
                if event['type'] == 'batch':
                    if started is None: started = time.monotonic()
                    report['samples'] += len(event['batch'])
                    report['batches'] += 1
                    owner.release(event['id'])
                elif event['type'] == 'signal':
                    report['signals'].append(event['name'])
                elif event['type'] == 'error':
                    report['error'] = event['text']
            terminal = owner.poll_terminal()
            if terminal is not None:
                report['terminal'] = terminal
                break
            if started is not None and time.monotonic() - started >= args.seconds:
                break
            time.sleep(.001)
    finally:
        owner.close()
        report['terminal'] = report['terminal'] or owner.poll_terminal()
    report['ok'] = bool(report['samples'] and report['terminal'] and report['terminal'].get('ok')
                        and report['terminal'].get('hardware_restored'))
    folder = Path(__file__).resolve().parent / 'resultados_v18'
    folder.mkdir(exist_ok=True)
    path = folder / ('receiver_' + time.strftime('%Y%m%d_%H%M%S') + '.json')
    path.write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps(dict(ok=report['ok'], samples=report['samples'], batches=report['batches'],
                         terminal=report['terminal'], report=str(path)), indent=2, default=str))
    return 0 if report['ok'] else 1

if __name__ == '__main__': raise SystemExit(main())
