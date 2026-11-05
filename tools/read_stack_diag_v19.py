#!/usr/bin/env python3
"""Measure V19 stack margins on a running diagnostic pair and restore ADC config."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monitor.v19.receiver.unoq_control import status_request
from monitor.v19.receiver.unoq_acquisition import Configuration, acquisition_reply, acquisition_request
from monitor.v19.receiver.unoq_switch import Phase
from monitor.v19.receiver.unoq_usb import BLOCK, MASK, Connection, ProtocolError


class FrameReader:
    def __init__(self, connection):
        self.connection = connection
        self.buffer = bytearray()
        self.previous_sequence = None

    def next_packet(self):
        while len(self.buffer) < BLOCK:
            data = self.connection.read()
            if data:
                self.buffer.extend(data)
        packet = bytes(self.buffer[:BLOCK])
        del self.buffer[:BLOCK]
        magic, version, kind, sequence, length = struct.unpack_from('<4sHHII', packet)
        if (magic, version, length) != (b'SCP1', 4, 972):
            raise ProtocolError('Cabecera SCP1 inválida durante lectura diagnóstica')
        if zlib.crc32(packet[:988]) != struct.unpack_from('<I', packet, 988)[0]:
            raise ProtocolError('CRC incorrecto durante lectura diagnóstica')
        if self.previous_sequence is not None and ((sequence - self.previous_sequence) & MASK) != 1:
            raise ProtocolError('Secuencia discontinua durante lectura diagnóstica')
        self.previous_sequence = sequence
        return packet, kind


def active_config(packet, kind):
    if kind not in (3, 15, 16, 19, 20, 21):
        return None
    rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from(
        '<IIIIHBBIII', packet, 48)
    encoded = period
    if kind in (20, 21):
        node_pairs = struct.unpack_from('<I', packet, 84)[0]
        encoded = (node_pairs << 16) | period | (0x80000000 if channels == 2 else 0)
    try:
        return Configuration.from_wire(bits, encoded)
    except ValueError as exc:
        raise ProtocolError('Configuración activa inválida al iniciar la medición') from exc


def configure(reader, connection, config, request_id):
    connection.socket.sendall(acquisition_request(request_id, config))
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        packet, kind = reader.next_packet()
        if kind != 7:
            continue
        reply = acquisition_reply(packet)
        if reply.request_id != request_id:
            continue
        if reply.phase == Phase.REJECTED:
            raise RuntimeError(f'El Q rechazó la configuración ADC: {reply.reason.name}')
        if reply.phase == Phase.APPLIED:
            if reply.active != config:
                raise RuntimeError('El Q aplicó una configuración distinta de la solicitada')
            return reply.active
    raise TimeoutError('El Q no confirmó APPLIED para la configuración ADC')


def read_stack_diagnostic(connection, reader, duration, output, bits, rate):
    original = None
    target = Configuration(bits, rate)
    if target._native is None:
        raise ValueError('La medición de pila requiere una tasa nativa V19')
    for _ in range(500):
        packet, kind = reader.next_packet()
        original = active_config(packet, kind)
        if original is not None:
            break
    if original is None:
        raise TimeoutError('No llegó el estado de adquisición inicial')

    restored = original == target
    config_id = 0x80000001

    next_ping = time.monotonic()
    ping_id = 0x80000101
    rows = []
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    next_record = started
    frame_count = 0
    producer_min = output_min = None

    capture_error = None
    try:
        if original != target:
            configure(reader, connection, target, config_id)
        while time.monotonic() - started < duration:
            now = time.monotonic()
            if now >= next_ping:
                connection.socket.sendall(status_request(ping_id))
                ping_id = ((ping_id + 1) & 0x7fffffff) | 0x80000000
                next_ping = now + 1.0
            packet, kind = reader.next_packet()
            if kind in (5, 7, 9, 12):
                continue
            if kind != 21:
                raise ProtocolError(
                    f'El Q envía tipo SCP1 {kind}; se esperaba 21. '
                    'Confirmá que está corriendo el firmware diagnóstico V19.')
            node_pairs, queue, queue_peak, copy_ticks, poll_ticks, slack_ticks, producer_free, output_free = struct.unpack_from('<8I', packet, 84)
            if not node_pairs or producer_free > 4096 or output_free > 4096:
                raise ProtocolError('Métricas de pila fuera de rango')
            frame_count += 1
            producer_min = producer_free if producer_min is None else min(producer_min, producer_free)
            output_min = output_free if output_min is None else min(output_min, output_free)
            if now >= next_record:
                sequence = struct.unpack_from('<I', packet, 8)[0]
                rows.append(dict(elapsed_seconds=now-started, sequence=sequence,
                                 producer_stack_free_bytes=producer_free,
                                 output_stack_free_bytes=output_free, queue=queue,
                                 queue_peak=queue_peak, copy_ticks=copy_ticks,
                                 poll_ticks=poll_ticks, slack_ticks=slack_ticks))
                next_record = now + 1.0
    except Exception as exc:
        capture_error = exc
    finally:
        if original != target:
            try:
                configure(reader, connection, original, config_id + 1)
                restored = True
            except Exception as exc:
                capture_error = RuntimeError(f'{capture_error or "captura"}; no se pudo restaurar ADC: {exc}')
        else:
            restored = True

    result = {
        'schema': 1,
        'version': 19,
        'started_utc': started_utc,
        'duration_seconds': time.monotonic() - started,
        'diagnostic_frames': frame_count,
        'tested_configuration': {'bits': target.bits, 'rate_sps': target.rate,
                                 'channels': target.channels},
        'original_configuration': {'bits': original.bits, 'rate_sps': original.rate,
                                   'channels': original.channels},
        'adc_configuration_restored': restored,
        'capture_error': str(capture_error) if capture_error else None,
        'minimum_free_bytes': {
            'producer_adc_dma': producer_min,
            'output_spi': output_min,
        },
        'last': rows[-1] if rows else None,
        'rows': rows,
        'physical_acceptance': 'pending',
        'firmware_installed_by_tool': False,
    }
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True, help='Número de serie ADB del UNO Q')
    parser.add_argument('--duration', type=float, default=60.0,
                        help='Duración de captura; ejecutar con carga representativa (default: 60 s)')
    parser.add_argument('--bits', type=int, default=8, choices=(8, 10, 12, 14, 16))
    parser.add_argument('--rate', type=int, default=1860465,
                        help='Tasa nativa V19; por defecto 1,860 MS/s en 8 bits')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'diagnosticos/resultados_v19/stack_usage_v19.json')
    args = parser.parse_args()
    if args.duration < 5 or args.duration > 3600:
        parser.error('--duration debe estar entre 5 y 3600 segundos')
    connection = Connection(args.serial)
    reader = FrameReader(connection)
    try:
        connection.open()
        result = read_stack_diagnostic(connection, reader, args.duration, args.output,
                                       args.bits, args.rate)
    finally:
        connection.close()
    print(json.dumps({key: result[key] for key in
                      ('duration_seconds', 'diagnostic_frames', 'tested_configuration',
                       'minimum_free_bytes', 'adc_configuration_restored', 'capture_error')},
                     indent=2, ensure_ascii=False))
    print(f"Informe: {Path(args.output).expanduser()}")
    return 2 if result['capture_error'] or not result['adc_configuration_restored'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
