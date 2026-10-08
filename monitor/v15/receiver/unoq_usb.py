"""PC transport: USB-only ADB tunnel and strict SCP1 ADC decoding (stdlib)."""
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time
import zlib

BLOCK = 992
MASK = 0xffffffff
SAMPLE = struct.Struct('<IHH')


class ProtocolError(ValueError):
    pass


class Decoder:
    def __init__(self, check_ack_sequence=True):
        self.check_ack_sequence = check_ack_sequence
        self.buffer = bytearray()
        self.blocks = self.pairs = self.bytes = 0
        self.previous_sequence = self.previous_ack = None
        self.previous_index = self.previous_timestamp = None

    def feed(self, data):
        self.buffer.extend(data)
        samples = []
        while len(self.buffer) >= BLOCK:
            packet = bytes(self.buffer[:BLOCK])
            del self.buffer[:BLOCK]
            samples.extend(self.frame(packet))
        return samples

    def frame(self, p):
        if len(p) != BLOCK:
            raise ProtocolError('Trama incompleta')
        magic, version, kind, sequence, length = struct.unpack_from('<4sHHII', p)
        if (magic, version, kind, length) != (b'SCP1', 3, 3, 972):
            raise ProtocolError('Cabecera SCP1 ADC inválida')
        if zlib.crc32(p[:-4]) != struct.unpack_from('<I', p, 988)[0]:
            raise ProtocolError('CRC incorrecto en el PC')
        ack, spi, commands, short, result, error, _, _ = struct.unpack_from('<IIIIiiII', p, 16)
        if spi or commands or short or error or result not in (0, BLOCK):
            raise ProtocolError(f'Error del enlace SPI: {spi}/{commands}/{short}, retorno {result}, error {error}')
        rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from('<IIIIHBBIII', p, 48)
        if dropped or fatal or flags:
            raise ProtocolError(f'Adquisición interrumpida: {dropped} nodos perdidos, {fatal} errores, flags {flags}')
        if (rate, bits, channels, period) != (31250, 14, 2, 32) or not 1 <= count <= 113:
            raise ProtocolError('Configuración o cantidad de muestras inválida')
        if (node*2048 & MASK) != index-index%2048 or count > 2048-index%2048:
            raise ProtocolError('Fragmento fuera del nodo ADC')
        if any(p[80+count*8:988]):
            raise ProtocolError('Padding inválido')
        if self.previous_sequence is not None:
            if (sequence-self.previous_sequence)&MASK != 1:
                raise ProtocolError('Pérdida o repetición de bloques')
            if self.check_ack_sequence and (ack-self.previous_ack)&MASK != 1:
                raise ProtocolError('ACK discontinuo')
        samples = []
        previous_index, previous_timestamp = self.previous_index, self.previous_timestamp
        for i in range(count):
            timestamp, a, b = SAMPLE.unpack_from(p, 80+i*8)
            current = (index+i)&MASK
            if a > 16383 or b > 16383:
                raise ProtocolError('Muestra fuera del rango de 14 bits')
            if previous_index is not None:
                if (current-previous_index)&MASK != 1:
                    raise ProtocolError('Pérdida o repetición de muestras')
                if (timestamp-previous_timestamp)&MASK != 32:
                    raise ProtocolError('Timestamp discontinuo')
            samples.append((timestamp, a, b, current))
            previous_index, previous_timestamp = current, timestamp
        self.previous_sequence, self.previous_ack = sequence, ack
        self.previous_index, self.previous_timestamp = previous_index, previous_timestamp
        self.blocks += 1
        self.pairs += count
        self.bytes += BLOCK
        return samples


def adb_path():
    override = os.environ.get('UNOQ_ADB') or shutil.which('adb')
    if override:
        return override
    candidates = sorted((Path.home()/'Library/Arduino15/packages/arduino/tools/adb').glob('*/adb'))
    if candidates:
        return str(candidates[-1])
    raise RuntimeError('No se encontró ADB. Instalar las herramientas del UNO Q o definir UNOQ_ADB.')


def adb(*args):
    result = subprocess.run([adb_path(), *args], text=True, capture_output=True, timeout=3)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'ADB falló')
    return result.stdout.strip()


def usb_devices():
    devices = []
    for line in adb('devices', '-l').splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == 'device' and any(f.startswith('usb:') for f in fields[2:]):
            devices.append(fields[0])
    return devices


class Connection:
    def __init__(self, serial):
        self.serial = serial
        self.wav_firmware = False
        self.local_port = None
        self.socket = None
        self.last_data = time.monotonic()

    def open(self):
        if self.serial not in usb_devices():
            raise RuntimeError('El UNO Q seleccionado no está conectado por USB/ADB.')
        try:
            # Detect the running app before sending protocol additions to old relays.
            try:
                names = adb('-s', self.serial, 'shell', 'docker', 'ps', '--format', '{{.Names}}').splitlines()
                self.wav_firmware = any(name in names for name in ('scope-wav-v12-audio-main-1','scope-pulse-us-v13-main-1'))
            except RuntimeError:
                self.wav_firmware = False
            self.local_port = int(adb('-s', self.serial, 'forward', 'tcp:0', 'tcp:8766'))
            self.socket = socket.create_connection(('127.0.0.1', self.local_port), timeout=1)
            # Small commands/audio blocks should leave immediately, without Nagle batching.
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.settimeout(0.1)
            self.last_data = time.monotonic()
        except Exception:
            self.close()
            raise
        return self

    def read(self):
        try:
            data = self.socket.recv(65536)
        except socket.timeout:
            if time.monotonic()-self.last_data > 2:
                raise RuntimeError('El Q dejó de entregar muestras durante más de 2 segundos.')
            return b''
        if not data:
            raise RuntimeError('El Q cerró el flujo. Revisar el relay, la adquisición y el cable USB.')
        self.last_data = time.monotonic()
        return data

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self.local_port is not None:
            port, self.local_port = self.local_port, None
            try:
                adb('-s', self.serial, 'forward', '--remove', f'tcp:{port}')
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                pass  # USB may have disappeared; never remove unrelated forwards.

    def __enter__(self):
        return self.open()

    def __exit__(self, *args):
        self.close()
