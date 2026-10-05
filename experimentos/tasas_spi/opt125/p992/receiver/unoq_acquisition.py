"""Validated SET_ACQUISITION contract and supported integer-microsecond rates."""
from dataclasses import dataclass
import struct
import zlib
from experimentos.tasas_spi.opt125.p992.receiver.unoq_switch import Phase, Reason
from experimentos.tasas_spi.opt125.p992.receiver.unoq_usb import ProtocolError

BITS = (8, 10, 12, 14, 16)
UART_RATES = (1000, 2000, 4000, 5000, 8000, 10000, 12500, 15625, 20000, 25000, 31250)

SPI_RATES = UART_RATES + (40000, 50000, 62500, 100000, 125000, 200000, 250000)
RATES = SPI_RATES

@dataclass(frozen=True)
class Configuration:
    bits: int = 14
    rate: int = 31250
    def __post_init__(self):
        if self.bits not in BITS or self.rate not in RATES or (self.bits == 16 and self.rate > 50000):
            raise ValueError('Bits o tasa no admitidos por la adquisición actual')
    @property
    def period(self): return 1000000//self.rate
    @property
    def sampling_cycles(self):
        if self.bits != 16: return 391 if self.rate <= 40000 else 68 if self.rate <= 200000 else 36
        for maximum, cycles in ((2000,391),(12500,68),(20000,36),(31250,20),(40000,12),(50000,5)):
            if self.rate <= maximum: return cycles
    @property
    def sampling_us(self): return self.sampling_cycles/40
    @property
    def maximum(self): return (1 << self.bits)-1
    @property
    def sample_timeout(self): return max(2, 4096/self.rate+0.5)


def acquisition_request(rid, config):
    if not 0x80000000 <= rid < 0xffffffff: raise ValueError('Identificador inválido')
    p = bytearray(992)
    struct.pack_into('<4sHHII', p, 0, b'SCP1', 3, 6, rid, 972)
    p[16] = config.bits
    struct.pack_into('<I', p, 20, config.period)
    struct.pack_into('<I', p, 988, zlib.crc32(p[:988]))
    return bytes(p)

@dataclass(frozen=True)
class AcquisitionReply:
    request_id: int
    requested_bits: int
    active: Configuration
    phase: Phase
    reason: Reason
    requested_period: int
    epoch: int


def acquisition_reply(p):
    if len(p)!=992 or struct.unpack_from('<4sHH',p)!=(b'SCP1',3,7) or struct.unpack_from('<I',p,12)[0]!=972:
        raise ProtocolError('Cabecera de adquisición inválida')
    if zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]:
        raise ProtocolError('CRC de adquisición incorrecto')
    rid, requested, bits, phase, reason, wanted, period, epoch = struct.unpack_from('<IBBBBIII',p,16)
    if not 0x80000000 <= rid < 0xffffffff or any(p[36:988]) or epoch > 0x7fffffff:
        raise ProtocolError('Campos reservados de adquisición inválidos')
    try:
        if not period or 1000000%period: raise ValueError()
        active = Configuration(bits,1000000//period)
        phase, reason = Phase(phase), Reason(reason)
        if phase!=Phase.REJECTED:
            if not wanted or 1000000%wanted: raise ValueError()
            Configuration(requested,1000000//wanted)
        if (phase==Phase.REJECTED)!=(reason!=Reason.OK): raise ValueError()
        if phase==Phase.APPLIED and (requested!=bits or wanted!=period): raise ValueError()
    except ValueError as exc: raise ProtocolError('Estado de adquisición contradictorio') from exc
    return AcquisitionReply(rid,requested,active,phase,reason,wanted,epoch)
