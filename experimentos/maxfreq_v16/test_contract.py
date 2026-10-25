import unittest,struct,tempfile,subprocess,zlib
from pathlib import Path
from experimentos.maxfreq_v16.contract import Decoder,frame,seal,CAPACITY,request
EXP=Path(__file__).resolve().parent
def packet(bits,ticks,n,index,node,seq,values,timestamp):
 p=frame(20,seq);struct.pack_into('<i',p,32,992)
 struct.pack_into('<IIIIHBBIII',p,48,160000000//ticks,index&0xffffffff,0,0,len(values),bits,1,ticks,node,0)
 struct.pack_into('<I8I',p,80,timestamp&0xffffffff,n,1,1,100,1000,500,10000,1)
 data=0
 for i,v in enumerate(values):data|=v<<(i*bits)
 used=(len(values)*bits+7)//8;p[116:116+used]=data.to_bytes(used,'little')
 return seal(p)
class ContractTests(unittest.TestCase):
 def test_profiles_and_requests(self):
  for bits in (8,10,14):
   for ticks in (78,133,480,640):
    for n in (1984,2784,3456,3584,4096,7168,7936):
     p=request(0x80000001,bits,ticks,n)
     self.assertEqual(struct.unpack_from('<I',p,20)[0],n<<16|ticks)
  for args in ((12,133,3584),(14,77,3584),(8,133,1025),(8,133,8256)):
   with self.assertRaises(ValueError):request(0x80000001,*args)
 def test_python_and_c_nodes_wrap_and_rejections(self):
  base=EXP/'arduino/historico/v16/relay/base_verifier.c';header=base.with_name('config_relay_protocol.h')
  source=f'''#define main old_main
#include "{base}"
#undef main
#include "{header}"
int main(int argc,char**argv){{uint8_t p[BLOCK];init_crc();DualChecker d={{.bits=(unsigned)atoi(argv[1]),.period=(uint32_t)strtoul(argv[2],0,10)}};while(fread(p,1,BLOCK,stdin)==BLOCK)printf("%d\\n",dual_feed(&d,p));ping(p,0x80000001);if(!dual_command(p))return 2;return argc<3;}}
'''
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'checker.c';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(exe)],check=True,capture_output=True)
   for bits,n in ((8,3584),(10,2784),(14,3968)):
    with self.subTest(bits=bits):
     ticks=133;node=(1<<32)//n;start=node*n;frames=[];values=[i%((1<<bits)-1) for i in range(n)]
     for seq,offset in enumerate(range(0,n,CAPACITY[bits])):
      frames.append(packet(bits,ticks,n,start+offset,node,seq,values[offset:offset+CAPACITY[bits]],0xfffffff0+offset*ticks))
     d=Decoder();d.feed(b''.join(frames));self.assertEqual(d.pairs,n);self.assertEqual(d.nodes,1)
     bad=bytearray(frames[-1]);bad[987]=1;bad=seal(bad)
     with self.assertRaises(ValueError):Decoder().feed(b''.join(frames[:-1])+bad)
     result=subprocess.run([str(exe),str(bits),str(n<<16|ticks)],input=b''.join(frames)+bad,capture_output=True,check=True)
     self.assertEqual(result.stdout,b'1\n'*len(frames)+b'0\n')
 def test_gap_and_fault(self):
  first=packet(8,133,3584,0,0,0,[1]*864,0xfffffff0)
  second=packet(8,133,3584,868,0,1,[1]*864,0xfffffff0+868*133)
  with self.assertRaises(ValueError):Decoder().feed(first+second)
  bad=bytearray(first);struct.pack_into('<I',bad,56,1)
  with self.assertRaises(ValueError):Decoder().feed(seal(bad))
