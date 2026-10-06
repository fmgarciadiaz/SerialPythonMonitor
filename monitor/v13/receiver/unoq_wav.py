"""SCP1 v3 WAV streaming contract; one acknowledged chunk at a time."""
from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib
import numpy as np
from monitor.v13.receiver.unoq_usb import ProtocolError

RATE = 20000
RATES = (20000,40000,50000)
CHUNK = 480
class State(IntEnum):
    IDLE=0
    BUFFERING=1
    PLAYING=2
    DONE=3
    UNDERRUN=4
    FAULT=5

def _frame(kind, rid):
    if not 0x80000000 <= rid < 0xffffffff: raise ValueError('Identificador WAV inválido')
    p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',3,kind,rid,972)
    return p

def _finish(p):
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return bytes(p)

def command(rid, session=0, op=0, total=0, rate=20000):
    if op not in range(4) or not 0 <= session <= 0xffffffff or not 0 <= total <= 0xffffffff:
        raise ValueError('Comando WAV inválido')
    if rate not in RATES: raise ValueError("Tasa WAV no soportada")
    p=_frame(11,rid)
    struct.pack_into('<IB3xI',p,16,session,op,total)
    if op==1 and rate!=20000: struct.pack_into('<I',p,28,rate)
    return _finish(p)

def chunk(rid,session,offset,codes):
    data=np.asarray(codes)
    if data.ndim!=1 or not 1 <= len(data) <= CHUNK or data.dtype.kind not in 'ui' or np.any(data>4095) or np.any(data<0):
        raise ValueError('Muestras WAV inválidas')
    p=_frame(13,rid)
    struct.pack_into('<IIHH',p,16,session,offset,len(data),0)
    p[28:28+len(data)*2]=data.astype('<u2').tobytes()
    return _finish(p)

@dataclass(frozen=True)
class Status:
    request_id:int
    session:int
    state:State
    reason:int
    free_blocks:int
    accepted:int
    played:int
    total:int
    rate:int
    rates_mask:int=1

def status(p):
    if len(p)!=992 or struct.unpack_from('<4sHH',p)!=(b'SCP1',3,12) or struct.unpack_from('<I',p,12)[0]!=972 or zlib.crc32(p[:988])!=struct.unpack_from('<I',p,988)[0]:
        raise ProtocolError('Estado WAV inválido')
    rid,session,state,reason,free,accepted,played,total,rate=struct.unpack_from('<IIBBHIIII',p,16)
    mask=struct.unpack_from("<I",p,44)[0]
    try:
        state=State(state)
        if not 0x80000000<=rid<0xffffffff or not 0<=free<=16 or played>accepted or accepted>total or reason not in range(5) or rate not in RATES or mask not in (0,7) or (mask==0 and rate!=20000) or any(p[48:988]): raise ValueError()
    except ValueError as exc: raise ProtocolError('Estado WAV contradictorio') from exc
    return Status(rid,session,state,reason,free,accepted,played,total,rate,mask or 1)
