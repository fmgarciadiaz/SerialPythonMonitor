"""Local SCP1 test vectors for V18; no imports from archived tests."""
import struct
import zlib

def packet(index=0,count=226,t0=0,seq=0,version=4,epoch=0):
 p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',version,3,seq,972)
 struct.pack_into('<i',p,32,992)
 struct.pack_into('<IIIIHBBIII',p,48,125000,index,0,0,count,14,2,8,index//2048,epoch<<1)
 struct.pack_into('<I',p,80,t0)
 for i in range(count):struct.pack_into('<HH',p,84+4*i,123,456)
 return seal(p)

def seal(p):struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
