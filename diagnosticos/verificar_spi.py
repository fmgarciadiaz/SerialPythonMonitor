#!/usr/bin/env python3
"""Benchmark SPI3 en Linux del UNO Q. No configura ADC ni modifica el USB.

Sin dependencias externas: usa el ioctl SPI_IOC_MESSAGE del kernel Linux.
El firmware V6 y este verificador deben usar bloques de 512 bytes.
"""
import argparse
import ctypes
import json
import math
import struct
import sys
import time
import zlib

BLOCK_BYTES = 512
HEADER = struct.Struct('<4sHHII')
VERSION = 2
STATUS = struct.Struct('<IIIIiiII')
PAYLOAD_BYTES = BLOCK_BYTES - HEADER.size - 4
PATTERN_BYTES = PAYLOAD_BYTES - STATUS.size
MASK = 0xffffffff
# El patrón es XOR de una base fija con cuatro bytes de la secuencia.
# translate y las asignaciones por pasos recorren los bytes en C, evitando
# ejecutar 492 iteraciones Python por trama. Se conservan exactamente los bytes.
_BASE_LANES = tuple(bytes((i * 17 + 0x5a) & 255 for i in range(lane, PAYLOAD_BYTES, 4))
                    for lane in range(4))
_XOR_TABLES = tuple(bytes(value ^ key for value in range(256)) for key in range(256))


def pattern(sequence):
    seed = (sequence * 0x9e3779b1) & MASK
    result = bytearray(PAYLOAD_BYTES)
    for lane in range(4):
        result[lane::4] = _BASE_LANES[lane].translate(_XOR_TABLES[(seed >> (8 * lane)) & 255])
    return bytes(result)


def ping(sequence):
    data = HEADER.pack(b'SCP1', VERSION, 2, sequence, PAYLOAD_BYTES) + pattern(sequence)
    return data + struct.pack('<I', zlib.crc32(data))


class Checker:
    def __init__(self):
        self.transfers = self.valid_blocks = 0
        self.bad_headers = self.bad_payloads = self.crc_errors = 0
        self.missing_blocks = self.duplicates = self.out_of_order = 0
        self.ack_errors = self.counter_resets = 0
        self.previous = None
        self.first_counters = self.last_counters = None
        self.last_driver_result = None
        self.last_driver_error = None
        self.mcu_timing_blocks = self.mcu_prepare_us_sum = self.mcu_check_us_sum = 0
        self.mcu_prepare_us_max = self.mcu_check_us_max = 0
        self.mcu_spi_errors = self.mcu_bad_commands = self.mcu_short_transfers = 0

    def feed(self, data, expected_ack=None):
        self.transfers += 1
        if len(data) != BLOCK_BYTES:
            self.bad_headers += 1
            return
        magic, version, kind, sequence, length = HEADER.unpack_from(data)
        header_ok = (magic, version, kind, length) == (b'SCP1', VERSION, 1, PAYLOAD_BYTES)
        crc_ok = struct.unpack_from('<I', data, BLOCK_BYTES-4)[0] == zlib.crc32(data[:-4])
        self.bad_headers += not header_ok
        self.crc_errors += not crc_ok
        if not header_ok or not crc_ok:
            return
        if self.previous is not None:
            delta = (sequence - self.previous) & MASK
            if delta == 0:
                self.duplicates += 1
            elif delta >= 0x80000000:
                self.out_of_order += 1
            else:
                self.missing_blocks += delta - 1
                self.previous = sequence
        else:
            self.previous = sequence
        ack, errors, bad_commands, shorts, result, last_error, prepare_us, check_us = STATUS.unpack_from(data, HEADER.size)
        self.last_driver_result = result
        self.last_driver_error = last_error
        self.mcu_timing_blocks += 1
        self.mcu_prepare_us_sum += prepare_us
        self.mcu_check_us_sum += check_us
        self.mcu_prepare_us_max = max(self.mcu_prepare_us_max, prepare_us)
        self.mcu_check_us_max = max(self.mcu_check_us_max, check_us)
        if expected_ack is not None and ack != expected_ack:
            self.ack_errors += 1
        counters = (errors, bad_commands, shorts)
        if self.first_counters is None:
            self.first_counters = counters
        if self.last_counters is not None:
            deltas = [(new-old) & MASK for new, old in zip(counters, self.last_counters)]
            if any(d >= 0x80000000 for d in deltas):
                self.counter_resets += 1
            else:
                self.mcu_spi_errors += deltas[0]
                self.mcu_bad_commands += deltas[1]
                self.mcu_short_transfers += deltas[2]
        self.last_counters = counters
        if data[HEADER.size+STATUS.size:-4] != pattern(sequence)[STATUS.size:]:
            self.bad_payloads += 1
        else:
            self.valid_blocks += 1

    def report(self, elapsed):
        result = dict(vars(self))
        result.update(elapsed_s=elapsed, wire_bytes=self.transfers * BLOCK_BYTES,
                      mcu_prepare_us_mean=self.mcu_prepare_us_sum / max(self.mcu_timing_blocks, 1),
                      mcu_check_us_mean=self.mcu_check_us_sum / max(self.mcu_timing_blocks, 1),
                      wire_Bps=self.transfers * BLOCK_BYTES / max(elapsed, 1e-9),
                      verified_pattern_bytes=self.valid_blocks * PATTERN_BYTES,
                      verified_pattern_Bps=self.valid_blocks * PATTERN_BYTES / max(elapsed, 1e-9))
        result['integrity_pass'] = self.valid_blocks > 0 and not any((
            self.bad_headers, self.bad_payloads, self.crc_errors, self.missing_blocks,
            self.duplicates, self.out_of_order, self.ack_errors, self.counter_resets,
            self.mcu_spi_errors, self.mcu_bad_commands, self.mcu_short_transfers))
        return result


class SpiTransfer(ctypes.Structure):
    # linux/spi/spidev.h: __u64 tx/rx, __u32 len/speed, __u16 delay, seis __u8.
    _fields_ = [('tx_buf', ctypes.c_uint64), ('rx_buf', ctypes.c_uint64),
                ('len', ctypes.c_uint32), ('speed_hz', ctypes.c_uint32),
                ('delay_usecs', ctypes.c_uint16), ('bits_per_word', ctypes.c_uint8),
                ('cs_change', ctypes.c_uint8), ('tx_nbits', ctypes.c_uint8),
                ('rx_nbits', ctypes.c_uint8), ('word_delay_usecs', ctypes.c_uint8),
                ('pad', ctypes.c_uint8)]


class LinuxSPI:
    def __init__(self, path, hz):
        if not sys.platform.startswith('linux'):
            raise RuntimeError('El acceso físico SPI debe ejecutarse en Linux del UNO Q.')
        import fcntl
        import os
        self.ioctl = fcntl.ioctl
        self.fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        try:
            # Exclusión cooperativa entre instancias de este benchmark.
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert ctypes.sizeof(SpiTransfer) == 32
            self.ioctl(self.fd, 0x40016b01, b'\x00')  # SPI_IOC_WR_MODE: mode 0
            self.ioctl(self.fd, 0x40016b03, b'\x08')  # SPI_IOC_WR_BITS_PER_WORD
            self.ioctl(self.fd, 0x40046b04, struct.pack('=I', hz))
            configured = bytearray(4)
            self.ioctl(self.fd, 0x80046b04, configured, True)
            self.configured_hz = struct.unpack('=I', configured)[0]
            self.hz = hz
            self.tx = ctypes.create_string_buffer(BLOCK_BYTES)
            self.rx = ctypes.create_string_buffer(BLOCK_BYTES)
            self.ioctl_s = 0.0
            self.ioctl_max_s = 0.0
        except BaseException:
            os.close(self.fd)
            raise

    def exchange(self, data):
        if len(data) != BLOCK_BYTES:
            raise ValueError('Una transacción debe contener exactamente 512 bytes.')
        self.tx.raw = data
        ctypes.memset(ctypes.addressof(self.rx), 0, BLOCK_BYTES)
        transfer = SpiTransfer(tx_buf=ctypes.addressof(self.tx), rx_buf=ctypes.addressof(self.rx),
                               len=BLOCK_BYTES, speed_hz=self.hz, bits_per_word=8)
        descriptor = bytes(transfer)
        started = time.monotonic()
        self.ioctl(self.fd, 0x40206b00, descriptor)  # SPI_IOC_MESSAGE(1)
        duration = time.monotonic() - started
        self.ioctl_s += duration
        self.ioctl_max_s = max(self.ioctl_max_s, duration)
        return self.rx.raw

    def close(self):
        import os
        os.close(self.fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='/dev/spidev0.0')
    parser.add_argument('--hz', type=int, default=1000000)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--gap-us', type=float, default=1000,
                        help='Pausa entre bloques para rearmar el periférico; se incluye en el caudal.')
    parser.add_argument('--min-payload-bps', type=float, default=750000,
                        help='Umbral de bytes/s de patrón verificado, no de reloj SPI.')
    args = parser.parse_args(argv)
    if not (all(math.isfinite(n) for n in (args.seconds, args.gap_us, args.min_payload_bps))
            and 0 < args.hz <= MASK and args.seconds > 0 and args.gap_us >= 0
            and args.min_payload_bps > 0):
        parser.error('Frecuencia, duración y umbral positivos; gap no negativo.')
    checker = Checker()
    spi = None
    error = None
    started = time.monotonic()
    elapsed = 0.0
    prepare_s = exchange_s = check_s = gap_s = 0.0
    try:
        spi = LinuxSPI(args.device, args.hz)
        started = time.monotonic()
        previous_command = None
        command = 0
        last_progress = started
        draining = False
        while True:
            before = time.monotonic()
            packet = ping(command)
            prepared = time.monotonic()
            data = spi.exchange(packet)
            exchanged = time.monotonic()
            checker.feed(data, previous_command)
            checked = time.monotonic()
            prepare_s += prepared - before
            exchange_s += exchanged - prepared
            check_s += checked - exchanged
            previous_command = command
            command = (command + 1) & MASK
            if draining:
                break
            if args.gap_us:
                time.sleep(args.gap_us / 1e6)
            now = time.monotonic()
            gap_s += now - checked
            if now - last_progress >= 10:
                print(json.dumps({'progress': checker.report(now-started)}), flush=True)
                last_progress = now
            # Un intercambio adicional confirma el último PING del intervalo.
            draining = now - started >= args.seconds
        elapsed = time.monotonic() - started
    except (OSError, RuntimeError, KeyboardInterrupt) as exc:
        elapsed = time.monotonic() - started
        error = f'{type(exc).__name__}: {exc}'
    finally:
        if spi is not None:
            spi.close()
    report = checker.report(elapsed)
    report.update(device=args.device, requested_hz=args.hz,
                  configured_hz=spi.configured_hz if spi else None,
                  block_bytes=BLOCK_BYTES, gap_us=args.gap_us,
                  minimum_pattern_Bps=args.min_payload_bps, error=error)
    report.update(implementation='python', protocol_version=VERSION,
                  pattern_bytes_per_block=PATTERN_BYTES,
                  timing_s=dict(prepare=prepare_s, exchange=exchange_s, check=check_s,
                                gap=gap_s, ioctl=spi.ioctl_s if spi else 0,
                                ioctl_max=spi.ioctl_max_s if spi else 0))
    report['throughput_pass'] = report['verified_pattern_Bps'] >= args.min_payload_bps
    report['pass'] = report['integrity_pass'] and report['throughput_pass'] and error is None
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
