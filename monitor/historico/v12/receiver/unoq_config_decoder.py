"""V12 SCP1 V3/992 decoder: acquisition profiles, generator and SPI/UART timeline."""
import secrets
import struct
import time
import zlib
from monitor.historico.v12.receiver.unoq_usb import BLOCK, MASK, SAMPLE, ProtocolError
from monitor.historico.v12.receiver.unoq_generator import generator_reply
from monitor.historico.v12.receiver.unoq_acquisition import Configuration, acquisition_reply
from monitor.historico.v12.receiver.unoq_switch import Mode, Phase, switch_request, switch_reply


class ConfigurationDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.sequence = None
        self.mode = None
        self.boundary = None
        self.config = None
        self.epoch = None
        self.previous_index = self.previous_timestamp = None
        self.pairs = 0
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
            if kind == 9:
                self.events.append(('generator', generator_reply(p)))
                continue
            if kind == 7:
                reply = acquisition_reply(p)
                if reply.phase == Phase.APPLIED and reply.epoch == self.epoch and reply.active != self.config:
                    raise ProtocolError('Configuración distinta con la misma época')
                self.events.append(('configuration', reply))
                if reply.phase == Phase.APPLIED and reply.epoch != self.epoch:
                    self.config = reply.active
                    self.epoch = reply.epoch
                    self.previous_index = self.previous_timestamp = None
                    self.boundary = 0
                continue
            if kind == 5:
                reply = switch_reply(p, struct.unpack_from('<I', p, 16)[0], p[20])
                self.replies.append(reply)
                self.events.append(('reply', reply))
                if reply.phase != Phase.APPLIED and self.mode is None:
                    self.mode = reply.active
                if reply.phase == Phase.APPLIED and reply.active != self.mode:
                    self.mode = reply.active
                    if self.mode == Mode.SPI:
                        self.previous_index = self.previous_timestamp = None
                        self.boundary = reply.boundary
                continue
            if kind != 3:
                raise ProtocolError('Tipo dual desconocido')
            ack, spi, bad, short, result, error = struct.unpack_from('<IIIIii', p, 16)
            rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from('<IIIIHBBIII', p, 48)
            if spi or bad or short or error or result not in (0, BLOCK):
                raise ProtocolError('Error SPI durante cambio de salida')
            if dropped or fatal or flags & 1:
                raise ProtocolError('Adquisición dual interrumpida')
            try:
                config = Configuration(bits, rate)
            except ValueError as exc: raise ProtocolError('Configuración ADC inválida') from exc
            if period != config.period or channels != 2:
                raise ProtocolError('Período ADC inválido')
            if self.config is None:
                self.config, self.epoch = config, flags >> 1
            if config != self.config or flags >> 1 != self.epoch:
                raise ProtocolError('Adquisición cambió sin confirmación')
            self.status = dict(ack=ack, rate=rate, bits=bits, dropped=dropped, fatal=fatal, epoch=flags >> 1, prepare_us=struct.unpack_from("<I",p,40)[0], check_us=struct.unpack_from("<I",p,44)[0])
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
            if not 1 <= count <= 113 or node*2048 & MASK != index-index%2048 or count > 2048-index%2048:
                raise ProtocolError('Fragmento fuera del nodo ADC')
            if any(p[80+count*8:988]): raise ProtocolError('Padding ADC inválido')
            decoded = []
            for i in range(count):
                timestamp, a, b = SAMPLE.unpack_from(p,80+i*8)
                current = (index+i)&MASK
                if a > config.maximum or b > config.maximum: raise ProtocolError('ADC fuera de rango')
                if self.previous_index is not None:
                    if (current-self.previous_index)&MASK != 1 or (timestamp-self.previous_timestamp)&MASK != period:
                        raise ProtocolError('Muestras ADC discontinuas')
                self.previous_index, self.previous_timestamp = current, timestamp
                decoded.append((timestamp,a,b,current))
            self.pairs += count
            samples.extend(decoded)
            self.events.append(('samples', decoded))
        return samples
