"""V18 SCP1 V4/992 decoder: acquisition profiles, generator and SPI/UART timeline."""
from functools import lru_cache
import secrets
import struct
import time
import zlib
from monitor.v18.receiver.native_unpack import unpack_native, NativeRecords, numeric_records, join_records
from monitor.v18.receiver.unoq_usb import BLOCK, MASK, SAMPLE, ProtocolError
from monitor.v18.receiver.unoq_generator import generator_reply
from monitor.v18.receiver.unoq_wav import status as wav_status
from monitor.v18.receiver.unoq_acquisition import Configuration, acquisition_reply
from monitor.v18.receiver.unoq_switch import Mode, Phase, switch_request, switch_reply


@lru_cache(maxsize=128)
def _wire_configuration(bits, encoded):
    return Configuration.from_wire(bits, encoded)


class ConfigurationDecoder:
    def __init__(self):
        self.numeric = False  # GUI opt-in; default readers keep Python rows.
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

    def feed(self, data, *, collect_samples=True):
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
                if reply.phase == Phase.APPLIED and reply.epoch == self.epoch and (reply.active != self.config or reply.active.request_period != self.config.request_period):
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
            if kind not in (3,15,16,19,20):
                raise ProtocolError('Tipo dual desconocido')
            ack, spi, bad, short, result, error = struct.unpack_from('<IIIIii', p, 16)
            rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from('<IIIIHBBIII', p, 48)
            if spi or bad or short or error or result not in (0, BLOCK):
                raise ProtocolError('Error SPI durante cambio de salida')
            if dropped or fatal or flags & 1:
                raise ProtocolError('Adquisición dual interrumpida')
            try:
                config = _wire_configuration(bits, ((struct.unpack_from('<I', p, 84)[0] << 16) | period | (0x80000000 if channels == 2 else 0))) if kind == 20 else _wire_configuration(bits, period)
            except ValueError as exc: raise ProtocolError('Configuración ADC inválida') from exc
            if rate != config.rate or period != config.period or channels != config.channels or (kind != 20 and ((kind in (16,19))!=(config.channels==1) or (kind==19)!=(bits==8 and rate==1203007) or (kind==15 and bits!=14))):
                raise ProtocolError('Período ADC inválido')
            if self.config is None:
                self.config, self.epoch = config, flags >> 1
            if config != self.config or config.request_period != self.config.request_period or flags >> 1 != self.epoch:
                raise ProtocolError('Adquisición cambió sin confirmación')
            self.status = dict(ack=ack, rate=rate, bits=bits, dropped=dropped, fatal=fatal, epoch=flags >> 1, prepare_us=struct.unpack_from("<I",p,40)[0], check_us=struct.unpack_from("<I",p,44)[0])
            if kind == 20:
                metrics = struct.unpack_from('<8I', p, 84)
                if metrics[0] != config.node_pairs or metrics[1] > (config._native or {}).get("queue_slots",4) or metrics[2] > (config._native or {}).get("queue_slots",4):
                    raise ProtocolError('Métricas del nodo inválidas')
                self.status['queue_slots']=(config._native or {}).get('queue_slots',4)
                self.status.update(zip(('node_pairs','queue','queue_peak','copy_ticks','poll_ticks','slack_ticks','send_ticks','produced'), metrics))
            self.statuses.append(self.status)
            if not count:
                if index or node or struct.unpack_from("<I",p,80)[0] or any(p[116 if kind==20 else 84:988]):
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
            node_pairs=config.node_pairs
            capacity=(872*8//(bits*channels)) & ~3 if kind==20 else 904 if kind==19 else 516 if kind==16 else 258 if kind==15 else 226
            node_offset=(index-node*node_pairs)&MASK
            if not 1 <= count <= capacity or ((kind in (15,16,20)) and ((count|index)&(1 if kind==15 else 3))) or node_offset>=node_pairs or count > node_pairs-node_offset:
                raise ProtocolError('Fragmento fuera del nodo ADC')
            used=count*bits*channels//8 if kind==20 else count if kind==19 else count//4*7 if kind==16 else count//2*7 if kind==15 else count*4
            payload=116 if kind==20 else 84
            if any(p[payload+used:988]): raise ProtocolError('Padding ADC inválido')
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
            if kind == 20:
                decoded=unpack_native(p[payload:payload+used],bits,channels,count,timestamp,period,index,self.numeric)
                if decoded is not None:
                    pass
                elif bits == 8 and channels == 1:
                    decoded=[((timestamp+i*period)&MASK,a,0,(index+i)&MASK)
                             for i,a in enumerate(p[payload:payload+used])]
                elif bits in (8,16) and channels == 2:
                    fmt='<BB' if bits==8 else '<HH'
                    decoded=[((timestamp+i*period)&MASK,a,b,(index+i)&MASK)
                             for i,(a,b) in enumerate(struct.iter_unpack(fmt,p[payload:payload+used]))]
                else:
                    group_scalars=4 if bits in (10,14) else 2 if bits==12 else 1
                    width=group_scalars*bits//8
                    group_pairs=group_scalars//channels
                    for group,offset in enumerate(range(payload,payload+used,width)):
                        word=int.from_bytes(p[offset:offset+width],'little')
                        for j in range(group_pairs):
                            i=group*group_pairs+j
                            a=(word>>(j*channels*bits))&maximum
                            b=(word>>((j*channels+1)*bits))&maximum if channels==2 else 0
                            decoded.append(((timestamp+i*period)&MASK,a,b,(index+i)&MASK))
            elif kind == 19:
                decoded=[((timestamp+i*period)&MASK,a,0,(index+i)&MASK) for i,a in enumerate(p[84:84+used])]
            elif kind == 16:
                for group,offset in enumerate(range(84,84+used,7)):
                    word=int.from_bytes(p[offset:offset+7],'little')
                    for j in range(4):
                        i=group*4+j
                        decoded.append(((timestamp+i*period)&MASK,(word>>(j*14))&16383,0,(index+i)&MASK))
            elif kind == 15:
                for i, offset in enumerate(range(84, 84+used, 7)):
                    lo = struct.unpack_from('<I', p, offset)[0]
                    hi = p[offset+4] | p[offset+5] << 8 | p[offset+6] << 16
                    j = i*2
                    decoded.append(((timestamp+j*period)&MASK, lo&16383, (lo>>14)&16383, (index+j)&MASK))
                    decoded.append(((timestamp+(j+1)*period)&MASK, (lo>>28)|((hi&1023)<<4), hi>>10, (index+j+1)&MASK))
            else:
                for i, (a,b) in enumerate(struct.iter_unpack('<HH', p[84:84+used])):
                    if a>maximum or b>maximum: raise ProtocolError('ADC fuera de rango')
                    decoded.append(((timestamp+i*period)&MASK,a,b,(index+i)&MASK))
            if self.numeric:
                decoded=numeric_records(decoded)
            self.previous_timestamp,_,_,self.previous_index=decoded[-1]
            self.pairs += count
            if collect_samples:
                if isinstance(decoded,NativeRecords):
                    samples.append(decoded)
                else:
                    samples.extend(decoded)
            self.events.append(('samples', decoded))
        return join_records(samples) if samples and isinstance(samples[0],NativeRecords) else samples
