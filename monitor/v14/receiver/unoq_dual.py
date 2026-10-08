"""V14 SCP1 V3/992 compatibility decoder for fixed-profile dual output; the app uses ConfigurationDecoder."""
import secrets
import struct
import time
import zlib
from monitor.v14.receiver.unoq_usb import BLOCK, MASK, Decoder, ProtocolError
from monitor.v14.receiver.unoq_switch import Mode, Phase, switch_request, switch_reply


class DualDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.sequence = None
        self.mode = None
        self.boundary = None
        self.adc = Decoder(check_ack_sequence=False)
        self.replies = []
        self.status = None
        self.statuses = []

    def feed(self, data):
        self.buffer.extend(data)
        samples = []
        self.replies = []
        self.statuses = []
        self.events = []
        while len(self.buffer) >= BLOCK:
            p = bytes(self.buffer[:BLOCK])
            del self.buffer[:BLOCK]
            magic, version, kind, seq, length = struct.unpack_from('<4sHHII', p)
            if (magic, version, length) != (b'SCP1', 3, 972):
                raise ProtocolError('Cabecera dual inválida')
            if zlib.crc32(p[:988]) != struct.unpack_from('<I', p, 988)[0]:
                raise ProtocolError('CRC dual incorrecto')
            if self.sequence is not None and (seq-self.sequence)&MASK != 1:
                raise ProtocolError('Secuencia dual discontinua')
            self.sequence = seq
            if kind == 5:
                reply = switch_reply(p, struct.unpack_from('<I', p, 16)[0], p[20])
                self.replies.append(reply)
                self.events.append(('reply', reply))
                if reply.phase != Phase.APPLIED and self.mode is None:
                    self.mode = reply.active
                if reply.phase == Phase.APPLIED and reply.active != self.mode:
                    self.mode = reply.active
                    if self.mode == Mode.SPI:
                        self.adc.previous_index = self.adc.previous_timestamp = None
                        self.boundary = reply.boundary
                continue
            if kind != 3:
                raise ProtocolError('Tipo dual desconocido')
            ack, spi, bad, short, result, error = struct.unpack_from('<IIIIii', p, 16)
            rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from('<IIIIHBBIII', p, 48)
            if spi or bad or short or error or result not in (0, BLOCK):
                raise ProtocolError('Error SPI durante cambio de salida')
            if dropped or fatal or flags:
                raise ProtocolError('Adquisición dual interrumpida')
            if (rate, bits, channels, period) != (31250, 14, 2, 32):
                raise ProtocolError('Configuración ADC dual inválida')
            self.status = dict(ack=ack, rate=rate, bits=bits, dropped=dropped, fatal=fatal)
            self.statuses.append(self.status)
            if not count:
                if index or node or any(p[80:988]):
                    raise ProtocolError('Estado vacío inválido')
                continue
            if self.mode is None:
                self.mode = Mode.SPI
            if self.mode != Mode.SPI:
                raise ProtocolError('Muestras SPI durante modo UART')
            if self.boundary is not None:
                if index != self.boundary:
                    raise ProtocolError('La primera muestra no coincide con APPLIED')
                self.boundary = None
            self.adc.previous_sequence = (seq-1)&MASK
            decoded = self.adc.frame(p)
            samples.extend(decoded)
            self.events.append(('samples', decoded))
        return samples


class DualSession:
    def __init__(self, connection, on_samples=None):
        self.connection = connection
        self.decoder = DualDecoder()
        self.on_samples = on_samples or (lambda samples: None)
        self.next_id = 0x80000000 + secrets.randbelow(0x7fffffff)

    def read(self):
        samples = self.decoder.feed(self.connection.read())
        self.on_samples(samples)
        return samples

    def select(self, mode, timeout=3):
        mode = Mode(mode)
        rid = self.next_id
        self.next_id = 0x80000000 if rid == 0xfffffffe else rid+1
        self.connection.socket.sendall(switch_request(rid, mode))
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.read()
            for reply in self.decoder.replies:
                if reply.request_id != rid:
                    continue
                if reply.requested != mode:
                    raise ProtocolError('ACK para otro modo de salida')
                if reply.phase == Phase.REJECTED:
                    raise RuntimeError(f'Q rechazó cambio de salida: {reply.reason.name}')
                if reply.phase == Phase.APPLIED:
                    return reply
        raise TimeoutError('El Q no confirmó APPLIED; el modo de salida es incierto')

    def query(self, timeout=2):
        from monitor.v14.receiver.unoq_control import status_request
        rid = self.next_id
        self.next_id = 0x80000000 if rid == 0xfffffffe else rid+1
        self.connection.socket.sendall(status_request(rid))
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.read()
            for status in self.decoder.statuses:
                if status['ack'] == rid:
                    return status
        raise TimeoutError('El Q no confirmó PING en el modo activo')
