"""DAC generator contract. Frequencies in millihertz, levels in 12-bit DAC codes."""
from dataclasses import dataclass
import struct
import zlib
from typing import Optional
from monitor.v15.receiver.unoq_switch import Phase, Reason
from monitor.v15.receiver.unoq_usb import ProtocolError
CONFIG = struct.Struct('<BBBBIIHHI')
WAVES = ('Cuadrada', 'Seno', 'Triángulo', 'Rampa', 'Pulso')
MODES = ('Continuo', 'Sweep', 'Chirp')
UPDATE_HZ = 1000000
MAX_FREQUENCY_MHZ = 20000000

@dataclass(frozen=True)
class GeneratorConfig:
    wave: int = 0
    enabled: int = 1
    mode: int = 0
    frequency: int = 2500
    final_frequency: int = 2500
    low: int = 0
    high: int = 4095
    duration: int = 1000
    duration_us: int = 0
    def __post_init__(self):
        if any(type(v) is not int for v in self.__dict__.values()) or not (
            0 <= self.wave <= 4 and self.enabled in (0,1) and 0 <= self.mode <= 2 and
            100 <= self.frequency <= MAX_FREQUENCY_MHZ and 100 <= self.final_frequency <= MAX_FREQUENCY_MHZ and
            0 <= self.low <= self.high <= 4095 and ((100 <= self.duration <= 65535 and self.wave == 4 and self.mode == 0) if self.duration_us else 1 <= self.duration <= 600000) and self.duration_us in (0,1) and
            (self.wave != 4 or self.mode == 0)):
            raise ValueError('Generador: frecuencia 0,1 Hz–20 kHz, niveles 0–3,3 V y duración 1–600.000 ms')
    def pack(self):
        return CONFIG.pack(self.wave, self.enabled, self.mode, self.duration_us, self.frequency,
                           self.final_frequency, self.low, self.high, self.duration)

def unpack_config(p, offset):
    wave, enabled, mode, reserved, frequency, final, low, high, duration = CONFIG.unpack_from(p,offset)
    if reserved not in (0,1): raise ValueError('Unidad de duración inválida')
    return GeneratorConfig(wave,enabled,mode,frequency,final,low,high,duration,reserved)

def generator_request(rid, config=None):
    if not 0x80000000 <= rid < 0xffffffff: raise ValueError('Identificador inválido')
    p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',3,10 if config is None else 8,rid,972)
    if config is not None: p[16:36]=config.pack()
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return bytes(p)

@dataclass(frozen=True)
class GeneratorReply:
    request_id: int
    phase: Phase
    reason: Reason
    running: bool
    active: GeneratorConfig
    requested: Optional[GeneratorConfig]
    pulse_us_capable: bool = False

def generator_reply(p):
    if len(p)!=992 or struct.unpack_from('<4sHH',p)!=(b'SCP1',3,9) or struct.unpack_from('<I',p,12)[0]!=972:
        raise ProtocolError('Cabecera de generador inválida')
    if zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]: raise ProtocolError('CRC de generador incorrecto')
    rid=struct.unpack_from('<I',p,16)[0]
    try:
        phase,reason=Phase(p[20]),Reason(p[21])
        active=unpack_config(p,24)
        # Unsupported request fields are echoed verbatim by the MCU on rejection.
        requested=unpack_config(p,44) if phase!=Phase.REJECTED else None
        if not 0x80000000<=rid<0xffffffff or p[22]>1 or p[23]>1 or any(p[64:988]): raise ValueError()
        if (phase==Phase.REJECTED)!=(reason!=Reason.OK): raise ValueError()
        if p[22] and not active.enabled: raise ValueError()
        if phase==Phase.APPLIED and active!=requested: raise ValueError()
    except ValueError as exc: raise ProtocolError('Estado de generador contradictorio') from exc
    return GeneratorReply(rid,phase,reason,bool(p[22]),active,requested,bool(p[23]&1))
