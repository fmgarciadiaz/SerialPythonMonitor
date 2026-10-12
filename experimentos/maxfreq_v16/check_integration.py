"""Compile the exact staged relay and MCU packing without modifying production."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from monitor.v16.receiver import unoq_native
from monitor.v16.receiver.unoq_config_decoder import ConfigurationDecoder
from tests.v16.test_ch1_fast import extract
from experimentos.maxfreq_v16 import integrate_firmware as integration
from experimentos.maxfreq_v16.accepted import AcceptedProfile, firmware_header

ROOT = integration.ROOT
EXP = integration.EXP


def main():
    with tempfile.TemporaryDirectory(prefix='v16-native-') as folder:
        root=Path(folder)
        for path in ('arduino/v16/oscilloscope/sketch','arduino/v16/relay'):
            shutil.copytree(ROOT/path,root/path)
        shutil.copytree(EXP/'arduino',root/'experiment/arduino')
        header=firmware_header([AcceptedProfile(8,131,6912,1,False),
                               AcceptedProfile(10,176,8192,1,True),
                               AcceptedProfile(14,214,7936,1,False)])
        for path in ('arduino/v16/oscilloscope/sketch','arduino/v16/relay'):
            (root/path/'native_profiles.h').write_text(header)
        shutil.copy2(EXP/'arduino/v16/oscilloscope/sketch/sample_packing.h',
                     root/'arduino/v16/oscilloscope/sketch/sample_packing.h')
        integration.ROOT=root;integration.EXP=root/'experiment'
        integration.SKETCH=root/'arduino/v16/oscilloscope/sketch'
        if 'static bool native()' not in (integration.SKETCH/'acquisition.h').read_text():
            integration.main()
        base=root/'arduino/v16/relay/base_verifier.c'
        relay=base.with_name('config_relay_protocol.h')
        source=root/'relay.c'
        source.write_text(f'#define main baseline_main\n#include "{base}"\n#undef main\n#include "{relay}"\nint main(int argc,char **argv){{(void)argc;init_crc();DualChecker d={{.bits=(unsigned)atoi(argv[1]),.period=(uint32_t)strtoul(argv[2],0,10)}};uint8_t p[BLOCK];while(fread(p,1,BLOCK,stdin)==BLOCK)if(!dual_feed(&d,p))return 1;return 0;}}\n')
        subprocess.run(['cc','-O2','-std=c11',str(source),'-lm','-o',str(root/'relay')],check=True)
        body=extract(integration.SKETCH/'sketch.ino','build_native_samples')
        benchmark=integration.SKETCH/'benchmark_protocol.h'
        packing=integration.SKETCH/'sample_packing.h'
        cpp=root/'packer.cpp'
        cpp.write_text(f'''#include "{benchmark}"
#include "{packing}"
#include <algorithm>
#include <cstdlib>
#include <cstdio>
using namespace scope_bench;
int k_sem_count_get(int*){{return 3;}}
namespace acquisition{{
struct Sample{{uint16_t ch1;}};
struct Node{{uint32_t index,timestamp;Sample single_samples[8192];}};
unsigned bits=8,period=131,epoch=0,dropped_nodes=0,fatal_errors=0,QUEUE_SLOTS=4,
queue_peak=2,copy_max=100,poll_max=100,slack_min=100,send_previous=100,produced=1,n=6912;
int empty_slots;
unsigned node_pairs(){{return n;}}
}}
{body}
int main(int argc,char **argv){{(void)argc;
acquisition::bits=std::atoi(argv[1]);acquisition::period=std::atoi(argv[2]);acquisition::n=std::atoi(argv[3]);
acquisition::Node node{{argc>4?uint32_t(std::strtoul(argv[4],0,10)):0U,0xfffffff0U,{{}}}};
for(unsigned i=0;i<acquisition::n;++i)node.single_samples[i].ch1=(i*13)&((1U<<acquisition::bits)-1);
unsigned cap=acquisition::bits==8?864:acquisition::bits==10?696:496,seq=0;
for(unsigned off=0;off<acquisition::n;){{uint8_t p[992]={{}};unsigned count=std::min(cap,acquisition::n-off);
build_native_samples(p,&node,off,count);data_frame(p,seq++,0,0,0,0,992);put16(p+6,20);seal(p);fwrite(p,1,992,stdout);off+=count;}}
}}
''')
        subprocess.run(['c++','-O2','-std=c++17',str(cpp),'-o',str(root/'packer')],check=True)
        for bits,ticks,n in ((8,131,6912),(10,176,8192),(14,214,7936)):
            for node_index in (0,(1<<32)//n):
                packets=subprocess.run([str(root/'packer'),str(bits),str(ticks),str(n),str(node_index)],check=True,capture_output=True).stdout
                profile=dict(bits=bits,ticks=ticks,node_pairs=n,channels=1,headroom=False)
                with patch.object(unoq_native,'PROFILES',(profile,)):
                    rows=ConfigurationDecoder().feed(packets)
                assert [r[1] for r in rows]==[(i*13)&((1<<bits)-1) for i in range(n)]
                assert [r[3] for r in rows]==[(node_index*n+i)&0xffffffff for i in range(n)]
                subprocess.run([str(root/'relay'),str(bits),str((n<<16)|ticks)],input=packets,check=True)
        print('Exact staged MCU packer, relay and Python decoder agree for ADC8/10/14')
    integration.ROOT=ROOT;integration.EXP=EXP;integration.SKETCH=ROOT/'arduino/v16/oscilloscope/sketch'


if __name__=='__main__':
    main()
