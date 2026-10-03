#!/usr/bin/env python3
"""Physical V7 test: SPI -> UART -> SPI with Q control always connected."""
import argparse
import json
from pathlib import Path
import struct
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from transport.unoq_usb import Connection
from transport.unoq_dual import DualSession
from transport.unoq_switch import Mode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--r4-port', required=True)
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error('seconds debe ser positivo')
    import serial
    uart_samples, spi_samples, errors = [], [], []
    stopping = threading.Event()
    def reader(port):
        buffer = bytearray()
        locked = False
        while not stopping.is_set():
            buffer.extend(port.read(port.in_waiting or 1))
            while len(buffer) >= 7:
                if buffer[:4] != b'DATA' or struct.unpack_from('<BH', buffer, 4) != (1, 512):
                    if locked:
                        errors.append('R4 perdió sincronización'); return
                    del buffer[0]; continue
                if len(buffer) < 4103: break
                locked = True
                uart_samples.extend(struct.iter_unpack('<IHH', buffer[7:4103]))
                del buffer[:4103]
    with serial.Serial(args.r4_port, 3000000, timeout=0.05) as port:
        time.sleep(3)  # R4 may reset when its USB port opens.
        port.reset_input_buffer()
        worker = threading.Thread(target=reader, args=(port,), daemon=True)
        worker.start()
        try:
            with Connection(args.serial) as connection:
                started = time.monotonic()
                session = DualSession(connection, spi_samples.extend)
                def drain(seconds):
                    end = time.monotonic()+seconds
                    while time.monotonic() < end:
                        session.read()
                drain(args.seconds)
                to_uart = session.select(Mode.UART)
                print('UART APPLIED:', to_uart, flush=True)
                uart_status = session.query()
                print('Control Q en UART:', uart_status, flush=True)
                drain(args.seconds)
                split = len(spi_samples)
                to_spi = session.select(Mode.SPI)
                print('SPI APPLIED:', to_spi, flush=True)
                drain(args.seconds)
                spi_status = session.query()
                elapsed = time.monotonic()-started
        finally:
            stopping.set(); worker.join(timeout=1)
    before = spi_samples[:split]
    after = spi_samples[split:]
    if not before or not uart_samples or not after:
        raise RuntimeError('Faltan muestras de una de las tres etapas')
    combined = [(s[0], s[1], s[2]) for s in before]+uart_samples+[(s[0], s[1], s[2]) for s in after]
    gaps = sum(((b[0]-a[0])&0xffffffff) != 32 for a,b in zip(combined,combined[1:]))
    bad_adc = sum(a>16383 or b>16383 for _,a,b in combined)
    expected_uart = (before[-1][3]+1)&0xffffffff
    expected_spi = (expected_uart+len(uart_samples))&0xffffffff
    boundaries = (to_uart.boundary == expected_uart and to_spi.boundary == expected_spi
                  and after[0][3] == to_spi.boundary)
    received_rate = len(combined)/elapsed
    rate_ok = abs(received_rate/31250-1) < 0.05
    report = dict(elapsed_seconds=elapsed, received_pairs_per_second=received_rate, rate_ok=rate_ok, spi_before=len(before), uart_pairs=len(uart_samples), spi_after=len(after),
                  gaps=gaps, adc_errors=bad_adc, errors=errors, boundaries_match=boundaries,
                  uart_boundary=to_uart.boundary, spi_boundary=to_spi.boundary,
                  control_in_uart=uart_status, control_in_spi=spi_status,
                  passed=not (gaps or bad_adc or errors) and boundaries and rate_ok)
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
