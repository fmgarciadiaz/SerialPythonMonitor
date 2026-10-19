import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

from experimentos.adc8_compact_v17.contract import Decoder

HERE=Path(__file__).resolve().parent


def canonical(seq=1,node=0,offset=0,count=908,ticks=114,n=3632):
    p=bytearray(1024)
    struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,seq,972)
    struct.pack_into('<IIIIiiII',p,16,17,0,0,0,992,0,67,88)
    index=(node*n+offset)&0xffffffff
    timestamp=(index*ticks)&0xffffffff
    struct.pack_into('<IIIIHBBIII',p,48,160000000//ticks,index,0,0,count,8,1,ticks,node,0)
    struct.pack_into('<9I',p,80,timestamp,n,2,3,400,500,100000,300000,node)
    p[116:116+count]=bytes(i%256 for i in range(count))
    return p


def seal(p):
    p=bytearray(p);struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)


class CompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'check'
        source=Path(cls.tmp.name)/'check.c'
        source.write_text(r'''
#define main reference_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
int main(int argc,char **argv) {
 if(argc!=2)return 2;init_crc();uint8_t p[1024];
 DualChecker d={.period=(3632U<<16)|114U,.bits=8};
 if(!strcmp(argv[1],"pack")) {
  while(fread(p,1,1024,stdin)==1024) {
   if(get16(p+64)>908)return 3;c8_pack(p);put32(p+988,crc32(p,988));fwrite(p,1,992,stdout);
  }
 } else if(!strcmp(argv[1],"expand")) {
  uint8_t out[1024];
  while(fread(p,1,992,stdin)==992) {c8_expand(out,p);fwrite(out,1,1024,stdout);}
 } else while(fread(p,1,992,stdin)==992) {
  if(strcmp(argv[1],"stream")) {memset(&d,0,sizeof d);d.bits=8;d.period=(3632U<<16)|114U;}
  fputc(dual_feed(&d,p)?1:0,stdout);
 }
 return 0;
}
''')
        subprocess.run(['cc','-O2','-std=c11','-Wall','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(HERE/'arduino/v16/relay'),str(source),'-lm','-o',str(cls.binary)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def run_c(self,mode,data):
        return subprocess.run([str(self.binary),mode],input=data,check=True,capture_output=True).stdout

    def packet(self,**kwargs):return self.run_c('pack',canonical(**kwargs))

    def test_c_python_full_nodes_and_wrap(self):
        sources=[canonical(seq=(0xfffffffc+i)&0xffffffff,node=node,offset=offset)
                 for i,(node,offset) in enumerate((n,o) for n in (0xffffffff,0) for o in (0,908,1816,2724))]
        packets=self.run_c('pack',b''.join(sources))
        self.assertEqual(self.run_c('stream',packets),b'\1'*8)
        d=Decoder()
        for at in range(0,len(packets),137):d.feed(packets[at:at+137])
        self.assertEqual(d.pairs,7264);self.assertEqual(d.nodes,2)
        self.assertEqual(d.status['queue'],2);self.assertEqual(d.status['queue_peak'],3)
        self.assertEqual(d.status['copy_ticks'],400);self.assertEqual(d.status['send_ticks'],300000)
        self.assertEqual(d.status['slack_ticks'],100000)

    def test_lossless_dynamic_metadata_roundtrip(self):
        for result in (0,992):
            source=canonical()
            struct.pack_into('<I',source,32,result)
            for i,offset in enumerate((40,44,96,100,104,108,112)):
                struct.pack_into('<I',source,offset,(0xffffffff-i*0x1020304)&0xffffffff)
            packed=self.run_c('pack',source)
            self.assertEqual(self.run_c('expand',packed),source)

    def test_crc_every_byte_and_fault_flag(self):
        p=self.packet()
        mutations=[]
        for i in range(992):
            q=bytearray(p);q[i]^=1;mutations.append(q)
        self.assertEqual(self.run_c('single',b''.join(mutations)),b'\0'*992)
        for q in mutations:
            with self.assertRaises(ValueError):Decoder().feed(q)
        source=canonical();struct.pack_into('<I',source,20,1)
        fault=self.run_c('pack',source)
        self.assertEqual(self.run_c('single',fault),b'\0')
        with self.assertRaises(ValueError):Decoder().feed(fault)

    def test_resealed_invalid_metadata_and_continuity(self):
        p=self.packet();bad=[]
        for offset,fmt,value in [(20,'I',(3632<<16)|640),(40,'H',909),(42,'B',5),
                                  (43,'B',5),(44,'I',1),(48,'I',1),(32,'I',1)]:
            q=bytearray(p);struct.pack_into('<'+fmt,q,offset,value);bad.append(seal(q))
        self.assertEqual(self.run_c('single',b''.join(bad)),b'\0'*len(bad))
        for q in bad:
            with self.assertRaises(ValueError):Decoder().feed(q)
        for offset in (8,24,36):
            q=bytearray(self.packet(seq=2,offset=908));q[offset]^=1;q=seal(q)
            self.assertEqual(self.run_c('stream',p+q),b'\1\0')
            with self.assertRaises(ValueError):Decoder().feed(p+q)

    def test_short_packet_padding_and_legacy_unchanged(self):
        p=self.packet(count=16)
        q=bytearray(p);q[96]=1;q=seal(q)
        self.assertEqual(self.run_c('single',q),b'\0')
        with self.assertRaises(ValueError):Decoder().feed(q)
        legacy=seal(canonical(count=864)[:992])
        self.assertEqual(self.run_c('single',legacy),b'\1')
        d=Decoder();d.feed(legacy);self.assertEqual(d.pairs,864)
        copies=[HERE/'compact_adc8.h',HERE/'arduino/v16/relay/compact_adc8.h',HERE/'arduino/v16/oscilloscope/sketch/compact_adc8.h']
        self.assertEqual(len({p.read_bytes() for p in copies}),1)


if __name__=='__main__':unittest.main()
