#!/usr/bin/env python3
"""Verifica en el PC las tramas ADC completas recibidas por USB/ADB."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from transport.unoq_usb import Connection, Decoder, usb_devices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial')
    parser.add_argument('--seconds', type=float, default=120)
    args = parser.parse_args()
    if not 0 < args.seconds <= 86400:
        parser.error('Duración inválida')
    serial = args.serial
    if not serial:
        devices = usb_devices()
        if len(devices) != 1:
            parser.error('Seleccionar --serial con un único UNO Q conectado por USB')
        serial = devices[0]
    decoder = Decoder()
    error = None
    started = time.monotonic()
    try:
        with Connection(serial) as connection:
            started = progress = time.monotonic()
            while time.monotonic()-started < args.seconds:
                decoder.feed(connection.read())
                if time.monotonic()-progress > 10:
                    print(f'PC: {decoder.blocks} bloques, {decoder.pairs} pares verificados', flush=True)
                    progress = time.monotonic()
    except Exception as exc:
        error = str(exc)
    elapsed = time.monotonic()-started
    rate = decoder.pairs*8/elapsed
    report = dict(serial=serial, elapsed_s=elapsed, blocks=decoder.blocks, pairs=decoder.pairs,
                  sample_Bps=rate, wire_Bps=decoder.bytes/elapsed, error=error,
                  partial_tail_bytes=len(decoder.buffer), integrity_pass=error is None and decoder.blocks > 0,
                  throughput_pass=rate >= 240000)
    report['pass'] = report['integrity_pass'] and report['throughput_pass']
    folder = ROOT/'diagnosticos/resultados_usb'
    folder.mkdir(exist_ok=True)
    path = folder/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    print(path)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
