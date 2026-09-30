#!/usr/bin/env python3
"""Verifica paquetes DATA y continuidad temporal sin dibujar (V3/V4)."""
import argparse
import struct
import time


class Checker:
    def __init__(self, sample_rate=20000):
        self.period = 1_000_000 / sample_rate
        self.buffer = bytearray()
        self.previous = None
        self.packets = self.samples = self.skipped = self.bad_dt = self.bad_adc = 0
        self.lost_sync = 0

    def discard(self, count):
        self.skipped += count
        if self.packets:
            self.lost_sync += count
        del self.buffer[:count]

    def feed(self, data):
        self.buffer.extend(data)
        while True:
            start = self.buffer.find(b"DATA")
            if start < 0:
                discard = max(0, len(self.buffer) - 3)
                self.discard(discard)
                return
            self.discard(start)
            if len(self.buffer) < 7:
                return
            state, count = struct.unpack_from("<BH", self.buffer, 4)
            if state not in (0, 1) or count != 512:
                self.discard(1)
                continue
            size = 7 + count * 8
            if len(self.buffer) < size:
                return
            for timestamp, ain, aout in struct.iter_unpack("<IHH", self.buffer[7:size]):
                if self.previous is not None:
                    dt = (timestamp - self.previous) & 0xffffffff
                    if abs(dt - self.period) > 3:
                        self.bad_dt += 1
                self.previous = timestamp
                self.bad_adc += int(ain > 16383 or aout > 16383)
            self.samples += count
            self.packets += 1
            del self.buffer[:size]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="puerto USB del R4; cerrar antes el monitor")
    parser.add_argument("--baud", type=int, default=2000000)
    parser.add_argument("--sample-rate", type=float, default=20000)
    parser.add_argument("--seconds", type=float, default=15)
    args = parser.parse_args()
    if args.sample_rate <= 0 or args.seconds <= 0:
        parser.error("sample-rate y seconds deben ser positivos")
    import serial

    checker = Checker(args.sample_rate)
    with serial.Serial(args.port, args.baud, timeout=0.1) as port:
        # Drenar continuamente: dormir acumularía datos en el puente USB y
        # falsearía hacia arriba el caudal medido al vaciar ese atraso.
        warmup = time.monotonic() + 3
        while time.monotonic() < warmup:
            port.read(port.in_waiting or 1)
        port.reset_input_buffer()
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            checker.feed(port.read(port.in_waiting or 1))
        elapsed = time.monotonic() - start
    rate = checker.samples / elapsed
    print(f"Paquetes: {checker.packets}; pares: {checker.samples}; recibidos: {rate:.1f} pares/s")
    print(f"Saltos/repeticiones de timestamp: {checker.bad_dt}; ADC fuera de rango: {checker.bad_adc}")
    print(f"Bytes descartados al resincronizar: {checker.skipped}; cola final: {len(checker.buffer)} bytes")
    print(f"Bytes perdidos después del primer paquete: {checker.lost_sync}")
    # Se admite un fragmento inicial/final por abrir/cerrar a mitad de paquete.
    ok = (checker.packets > 0 and checker.bad_dt == 0 and checker.bad_adc == 0
          and checker.lost_sync == 0 and checker.skipped < 4103
          and abs(rate / args.sample_rate - 1) < 0.05)
    print("PASS: caudal y continuidad dentro de tolerancia" if ok else "FAIL: revisar velocidad/pérdidas del enlace")
    print("Sin CRC en DATA: esta prueba no descarta toda corrupción de amplitud.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
