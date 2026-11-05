"""Deterministic native SCP1 frames, without transport or hardware."""
import struct
import zlib
import numpy as np


def native_frame(config,index=0,count=4,timestamp=0,sequence=0):
    maximum=config.maximum;channels=config.channels
    scalars=[(index*17+i*37)&maximum for i in range(count*channels)]
    scalars[:4]=[0,maximum,1,maximum-1]
    group=4 if config.bits in (10,14) else 2 if config.bits==12 else 1
    packed=b''.join(sum(value<<(config.bits*j) for j,value in enumerate(scalars[i:i+group])).to_bytes(group*config.bits//8,'little')
                    for i in range(0,len(scalars),group))
    packet=bytearray(992)
    struct.pack_into('<4sHHII',packet,0,b'SCP1',4,20,sequence,972)
    struct.pack_into('<i',packet,32,992)
    struct.pack_into('<IIIIHBBIII',packet,48,config.rate,index,0,0,count,config.bits,
                     channels,config.period,index//config.node_pairs,2)
    struct.pack_into('<I',packet,80,timestamp)
    struct.pack_into('<8I',packet,84,config.node_pairs,1,2,100,100,100,100,sequence)
    packet[116:116+len(packed)]=packed
    struct.pack_into('<I',packet,988,zlib.crc32(packet[:988]))
    rows=np.asarray([((timestamp+i*config.period)&0xffffffff,scalars[i*channels],
                      scalars[i*channels+1] if channels==2 else 0,(index+i)&0xffffffff)
                     for i in range(count)],dtype=np.uint32)
    return bytes(packet),rows
