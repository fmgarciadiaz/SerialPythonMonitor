#!/usr/bin/env python3
"""Synthetic throughput only; does not validate UNO Q hardware."""
import json,struct,sys,time,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experimentos.tasas_spi.receiver.unoq_config_decoder import ConfigurationDecoder

def main():
    frames=[];index=0;total=262144;sequence=0;period=4
    while index<total:
        count=min(53,2048-index%2048,total-index)
        p=bytearray(512)
        struct.pack_into('<4sHHII',p,0,b'SCP1',2,3,sequence,492)
        struct.pack_into('<I',p,32,512)
        struct.pack_into('<IIIIHBBIII',p,48,250000,index,0,0,count,14,2,period,index//2048,0)
        for i in range(count):struct.pack_into('<IHH',p,80+8*i,(index+i)*period,1000,2000)
        struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
        frames.append(bytes(p));index+=count;sequence+=1
    stream=b''.join(frames);trials=[]
    for _ in range(3):
        decoder=ConfigurationDecoder();started=time.perf_counter();count=0
        for offset in range(0,len(stream),65536):count+=len(decoder.feed(stream[offset:offset+65536]))
        elapsed=time.perf_counter()-started
        assert count==total
        trials.append({'pairs':count,'seconds':elapsed,'pairs_per_second':count/elapsed})
    output={'synthetic_only':True,'wire_bytes':len(stream),'trials':trials}
    p=ROOT/'experimentos/tasas_spi/resultados/benchmark_receptor.json';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
if __name__=='__main__':main()
