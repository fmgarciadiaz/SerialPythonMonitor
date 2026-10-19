"""Validated SET_ACQUISITION contract and supported integer-microsecond rates."""
from dataclasses import dataclass, InitVar
from typing import Optional
import struct
import zlib
from monitor.v17.receiver.unoq_switch import Phase, Reason
from monitor.v17.receiver.unoq_usb import ProtocolError
from monitor.v17.receiver.unoq_native import PROFILES, profile, wire_profile, code

BITS = (8, 10, 12, 14, 16)
UART_RATES = (1000, 2000, 4000, 5000, 8000, 10000, 12500, 15625, 20000, 25000, 31250)

SPI_RATES = UART_RATES + (40000, 50000, 62500, 66666, 71428, 100000, 125000, 200000, 250000, 333333, 599250, 661157, 1203007)
SINGLE_CHANNEL_PERIODS = {599250: 267, 661157: 242, 1203007: 133}
LEGACY_RATES = SPI_RATES
SPI_RATES = tuple(sorted(set(SPI_RATES) | {160000000 // p["ticks"] for p in PROFILES if not p.get("internal_only")}))
RATES = SPI_RATES

@dataclass(frozen=True, eq=False)
class Configuration:
    bits: int = 14
    rate: int = 31250
    wire_period: InitVar[Optional[int]] = None
    def __post_init__(self, wire_period):
        native = profile(self.bits, self.rate) if wire_period is None else wire_profile(self.bits, wire_period)
        if native is not None:
            if self.rate != 160000000 // native['ticks']:
                raise ValueError('Tasa nativa contradictoria')
            object.__setattr__(self, '_native', native)
            return
        object.__setattr__(self, '_native', None)
        if wire_period is not None and wire_period > 65535:
            raise ValueError('Perfil nativo no validado')
        if (self.rate in SINGLE_CHANNEL_PERIODS and self.bits!=(8 if self.rate==1203007 else 14)) or self.bits not in BITS or self.rate not in LEGACY_RATES or (self.bits == 16 and self.rate > 71428):
            raise ValueError('Bits o tasa no admitidos por la adquisición actual')
    def __eq__(self, other):
        if not isinstance(other, Configuration): return NotImplemented
        return (self.bits, self.rate, self.request_period) == (other.bits, other.rate, other.request_period)
    def __hash__(self): return hash((self.bits, self.rate, self.request_period))
    @property
    def period(self): return self._native['ticks'] if self._native else SINGLE_CHANNEL_PERIODS[self.rate] if self.channels==1 else 1000000//self.rate
    @property
    def request_period(self): return code(self._native) if self._native else self.period
    @property
    def node_pairs(self): return self._native['node_pairs'] if self._native else 3584 if self.rate==1203007 else 2048
    @classmethod
    def from_wire(cls, bits, encoded):
        if not encoded: raise ValueError('Período nulo')
        native = wire_profile(bits, encoded)
        rate = 160000000 // native['ticks'] if native else (160000000 if encoded in SINGLE_CHANNEL_PERIODS.values() else 1000000) // encoded
        config = cls(bits, rate, wire_period=encoded)
        if config.request_period != encoded: raise ValueError('Período no admitido')
        return config
    @property
    def channels(self): return self._native["channels"] if self._native else 1 if self.rate in SINGLE_CHANNEL_PERIODS else 2
    @property
    def timestamp_hz(self): return 160000000 if self._native or self.channels==1 else 1000000
    @property
    def dt_us(self): return self.period*1000000/self.timestamp_hz
    @property
    def actual_rate(self): return self.timestamp_hz/self.period
    @property
    def sampling_cycles(self):
        if self._native or self.rate==1203007: return 5
        if self.bits != 16: return 391 if self.rate <= 40000 else 68 if self.rate <= 200000 else 36
        for maximum, cycles in ((2000,391),(12500,68),(20000,36),(31250,20),(40000,12),(50000,5),(71428,5)):
            if self.rate <= maximum: return cycles
    @property
    def sampling_us(self): return self.sampling_cycles/54
    @property
    def maximum(self): return (1 << self.bits)-1
    @property
    def sample_timeout(self): return max(2, 4096/self.rate+0.5)


def acquisition_request(rid, config):
    if not 0x80000000 <= rid < 0xffffffff: raise ValueError('Identificador inválido')
    p = bytearray(992)
    struct.pack_into('<4sHHII', p, 0, b'SCP1', 4, 6, rid, 972)
    p[16] = config.bits
    struct.pack_into('<I', p, 20, config.request_period)
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
    if len(p)!=992 or struct.unpack_from('<4sHH',p)!=(b'SCP1',4,7) or struct.unpack_from('<I',p,12)[0]!=972:
        raise ProtocolError('Cabecera de adquisición inválida')
    if zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]:
        raise ProtocolError('CRC de adquisición incorrecto')
    rid, requested, bits, phase, reason, wanted, period, epoch = struct.unpack_from('<IBBBBIII',p,16)
    if not 0x80000000 <= rid < 0xffffffff or any(p[36:988]) or epoch > 0x7fffffff:
        raise ProtocolError('Campos reservados de adquisición inválidos')
    try:
        if not period: raise ValueError()
        active = Configuration.from_wire(bits,period)
        phase, reason = Phase(phase), Reason(reason)
        if phase!=Phase.REJECTED:
            if not wanted: raise ValueError()
            Configuration.from_wire(requested,wanted)
        if (phase==Phase.REJECTED)!=(reason!=Reason.OK): raise ValueError()
        if phase==Phase.APPLIED and (requested!=bits or wanted!=period): raise ValueError()
    except ValueError as exc: raise ProtocolError('Estado de adquisición contradictorio') from exc
    return AcquisitionReply(rid,requested,active,phase,reason,wanted,epoch)
