"""V16 SCP1 V4/992 decoder: acquisition profiles, generator and SPI/UART timeline."""
import secrets
import struct
import time
import zlib
from monitor.historico.v16.receiver.unoq_usb import BLOCK, MASK, SAMPLE, ProtocolError
from monitor.historico.v16.receiver.unoq_generator import generator_reply
from monitor.historico.v16.receiver.unoq_wav import status as wav_status
from monitor.historico.v16.receiver.unoq_acquisition import Configuration, acquisition_reply
from monitor.historico.v16.receiver.unoq_switch import Mode, Phase, switch_request, switch_reply


class SingleDecoder:
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
            if (magic, version, length) != (b'SCP1', 4, 972):
                raise ProtocolError('Cabecera dual inválida')
            if zlib.crc32(p[:988]) != struct.unpack_from('<I', p, 988)[0]:
                raise ProtocolError('CRC dual incorrecto')
            if self.sequence is not None and (seq-self.sequence)&MASK != 1:
                raise ProtocolError('Secuencia dual discontinua')
            self.sequence = seq
            if kind == 12:
                self.events.append(('wav', wav_status(p)))
                continue
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
            if kind not in (18,19):
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
            if period != config.period or channels != config.channels or kind!=(19 if config.channels==1 else 18) or bits!=8:
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
            if not 1 <= count <= 904//channels or node*3584 & MASK != index-index%3584 or count > 3584-index%3584:
                raise ProtocolError('Fragmento fuera del nodo ADC')
            used=count*channels
            if any(p[84+used:988]): raise ProtocolError('Padding ADC inválido')
            timestamp = struct.unpack_from('<I',p,80)[0]
            # The packet stores one timestamp/index; all subsequent positions
            # are derived below. Validate the received boundary once, including
            # uint32 wrap, rather than rechecking positions we just generated.
            if self.previous_index is not None:
                if (index-self.previous_index)&MASK != 1 or (timestamp-self.previous_timestamp)&MASK != period:
                    raise ProtocolError('Muestras ADC discontinuas')
            maximum=config.maximum
            decoded=[]
            # Do not retain a second list of tracked tuples for every frame:
            # at ADC100k it triggers collections in the audio refill path.
            for i in range(count):
                a=p[84+i*channels];b=p[85+i*channels] if channels==2 else 0
                decoded.append(((timestamp+i*period)&MASK,a,b,(index+i)&MASK))
            self.previous_timestamp,_,_,self.previous_index=decoded[-1]
            self.pairs += count
            samples.extend(decoded)
            self.events.append(('samples', decoded))
        return samples
