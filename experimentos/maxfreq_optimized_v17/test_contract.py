"""Actual packing plus C/Python frame validators, including ADC12 tails/wraps."""
import unittest
import tempfile
import subprocess
from pathlib import Path
from experimentos.maxfreq_v16.test_contract import packet
from experimentos.maxfreq_v16 import contract

EXP = Path(__file__).resolve().parent


class OptimizedContractTests(unittest.TestCase):
    def test_actual_packing_and_validators(self):
        sketch = EXP/'arduino/v16/oscilloscope/sketch'
        relay = EXP/'arduino/v16/relay'
        source = f'''#include "{sketch/'sample_packing.h'}"
#include <cassert>
#include <vector>
struct Sample {{unsigned ch1;}};
int main() {{for(unsigned bits:{{8U,10U,12U,14U}})for(unsigned n:{{4U,16U,576U,8192U}}) {{
 std::vector<Sample> x(n);std::vector<unsigned char> bytes(n*bits/8+8,0xaa);
 for(unsigned i=0;i<n;++i)x[i].ch1=(i*739+17)&((1U<<bits)-1);
 assert(maxfreq_packing::pack(bytes.data(),x.data(),n,bits)==n*bits/8);
 unsigned long long acc=0;unsigned avail=0,pos=0;
 for(unsigned i=0;i<n;++i){{while(avail<bits){{acc|=(unsigned long long)bytes[pos++]<<avail;avail+=8;}}
 assert((acc&((1U<<bits)-1))==x[i].ch1);acc>>=bits;avail-=bits;}}
 for(unsigned i=n*bits/8;i<bytes.size();++i)assert(bytes[i]==0xaa);
}}}}
'''
        checker = f'''#define main old_main
#include "{relay/'base_verifier.c'}"
#undef main
#include "{relay/'config_relay_protocol.h'}"
int main(int argc,char**argv){{uint8_t p[BLOCK];init_crc();DualChecker d={{.bits=(unsigned)atoi(argv[1]),.period=(uint32_t)strtoul(argv[2],0,10)}};while(fread(p,1,BLOCK,stdin)==BLOCK)printf("%d\\n",dual_feed(&d,p));return argc<3;}}
'''
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            cpp = folder/'pack.cpp'; cpp.write_text(source)
            subprocess.run(['c++', '-O2', '-std=c++17', str(cpp), '-o', str(folder/'pack')], check=True)
            subprocess.run([str(folder/'pack')], check=True)
            c = folder/'checker.c'; c.write_text(checker)
            subprocess.run(['cc', '-O2', '-std=c11', str(c), '-lm', '-o', str(folder/'checker')], check=True)
            previous = dict(contract.CAPACITY)
            try:
                contract.CAPACITY[12] = 576
                for bits, n in ((10,2784),(12,2304),(12,8192),(14,7936)):
                    ticks = 133; node = (1<<32)//n; start = node*n
                    values = [(i*739)&((1<<bits)-1) for i in range(n)]
                    frames = [packet(bits,ticks,n,start+offset,node,seq,
                        values[offset:offset+contract.CAPACITY[bits]],0xfffffff0+offset*ticks)
                        for seq,offset in enumerate(range(0,n,contract.CAPACITY[bits]))]
                    decoder = contract.Decoder(); decoder.feed(b''.join(frames))
                    self.assertEqual((decoder.pairs,decoder.nodes),(n,1))
                    bad = bytearray(frames[-1]); bad[987]=1; bad=contract.seal(bad)
                    output = subprocess.run([str(folder/'checker'),str(bits),str(n<<16|ticks)],
                        input=b''.join(frames)+bad,check=True,capture_output=True).stdout
                    self.assertEqual(output,b'1\n'*len(frames)+b'0\n')
            finally:
                contract.CAPACITY.clear(); contract.CAPACITY.update(previous)


if __name__ == '__main__': unittest.main()
