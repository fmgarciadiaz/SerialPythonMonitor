"""Compile actual MCU frame construction/capacity and compare both decoders."""
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.historico.v16.test_ch1_fast import extract
from experimentos.maxfreq_dual_v16.contract import Decoder,CAPACITY
from monitor.historico.v16.receiver import unoq_native
from monitor.historico.v16.receiver.unoq_config_decoder import ConfigurationDecoder

EXP=Path(__file__).resolve().parent


class ProductionFrameTests(unittest.TestCase):
    def test_actual_firmware_full_nodes_all_bits(self):
        sketch=EXP.parents[1]/'arduino/historico/v16/oscilloscope/sketch'
        body=extract(sketch/'sketch.ino','build_native_samples')
        text=(sketch/'sketch.ino').read_text()
        count_line=next(line.strip() for line in text.splitlines() if 'const unsigned count = min(' in line)
        base=EXP.parents[1]/'arduino/historico/v16/relay/base_verifier.c'
        relay=base.with_name('config_relay_protocol.h')
        source=f'''#include "{sketch/'benchmark_protocol.h'}"
#include "{sketch/'sample_packing.h'}"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
using namespace scope_bench;
using std::min;
int k_sem_count_get(int*){{return 3;}}
namespace acquisition{{
struct Pair{{uint16_t ch1,ch2;}};
struct Single{{uint16_t ch1;}};
struct Node{{uint32_t index,timestamp;union {{ Pair samples[4176]; Single single_samples[8192]; }};}};
unsigned channels,bits,period,n,epoch=0,dropped_nodes=0,fatal_errors=0,QUEUE_SLOTS=4,
queue_peak=2,copy_max=100,poll_max=100,slack_min=100,send_previous=100,produced=1;
int empty_slots;
unsigned node_pairs(){{return n;}}
bool single(){{return channels==1;}}
bool native(){{return true;}}
}}
{body}
int main(int argc,char**argv){{(void)argc;
acquisition::bits=std::atoi(argv[1]);acquisition::period=std::atoi(argv[2]);acquisition::n=std::atoi(argv[3]);acquisition::channels=std::atoi(argv[5]);
acquisition::Node node{{uint32_t(std::strtoul(argv[4],0,10)),0xfffffff0U,{{}}}};
for(unsigned i=0;i<acquisition::n;++i) if(acquisition::single()) node.single_samples[i].ch1=uint16_t((i*13)&((1U<<acquisition::bits)-1)); else node.samples[i]={{uint16_t((i*13)&((1U<<acquisition::bits)-1)),uint16_t((i*29)&((1U<<acquisition::bits)-1))}};
unsigned seq=0;for(unsigned offset=0;offset<acquisition::n;){{
{count_line}
uint8_t p[992]={{}};build_native_samples(p,&node,offset,count);data_frame(p,seq++,0,0,0,0,992);put16(p+6,20);seal(p);fwrite(p,1,992,stdout);offset+=count;
}}
}}
'''
        checker=f'#define main baseline_main\n#include "{base}"\n#undef main\n#include "{relay}"\nint main(int argc,char**argv){{(void)argc;init_crc();DualChecker d={{.bits=(unsigned)atoi(argv[1]),.period=(uint32_t)strtoul(argv[2],0,10)}};uint8_t p[BLOCK];while(fread(p,1,BLOCK,stdin)==BLOCK)if(!dual_feed(&d,p))return 1;return 0;}}'
        with tempfile.TemporaryDirectory() as folder:
            cpp=Path(folder)/'frames.cpp';cpp.write_text(source);binary=cpp.with_suffix('')
            c=Path(folder)/'relay.c';c.write_text(checker);verify=c.with_suffix('')
            subprocess.run(['c++','-O2','-std=c++17',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run(['cc','-O2','-std=c11',str(c),'-lm','-o',str(verify)],check=True,capture_output=True)
            for profile in unoq_native.PROFILES:
                bits,n,ticks,channels=(profile[k] for k in ('bits','node_pairs','ticks','channels'))
                for node in (0,(1<<32)//n):
                    packets=subprocess.run([str(binary),str(bits),str(ticks),str(n),str(node),str(channels)],check=True,capture_output=True).stdout
                    self.assertEqual(struct.unpack_from('<H',packets,64)[0],CAPACITY[bits] if channels==2 else {8:864,10:696,14:496}[bits])
                    if channels==2:
                        diagnostic=Decoder();diagnostic.feed(packets)
                        self.assertEqual(diagnostic.pairs,n)
                    with patch.object(unoq_native,'PROFILES',(profile,)):
                        rows=ConfigurationDecoder().feed(packets)
                        numeric=ConfigurationDecoder();numeric.numeric=True
                        self.assertEqual(list(numeric.feed(packets)),rows)
                    self.assertEqual([(r[1],r[2]) for r in rows],
                                     [((i*13)&((1<<bits)-1),(i*29)&((1<<bits)-1) if channels==2 else 0) for i in range(n)])
                    self.assertEqual([r[3] for r in rows],[(node*n+i)&0xffffffff for i in range(n)])
                    subprocess.run([str(verify),str(bits),str((0x80000000 if channels==2 else 0)|(n<<16)|ticks)],input=packets,check=True)
