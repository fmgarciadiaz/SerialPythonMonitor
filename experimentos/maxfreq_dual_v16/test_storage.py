"""Actual shared storage/validator bounds across CH1, dual and legacy changes."""
import subprocess
import tempfile
import unittest
from pathlib import Path

SKETCH=Path(__file__).resolve().parents[2]/'arduino/historico/v16/oscilloscope/sketch'


class StorageTests(unittest.TestCase):
    def test_all_profiles_and_legacy_queue_ownership_bounds(self):
        source=f'''constexpr unsigned SERIAL_BLOCK_PAIRS=512;
#include "{SKETCH/'acquisition_storage.h'}"
#include "{SKETCH/'node_validation.h'}"
#include <cassert>
#include <cstring>
struct Guard {{uint32_t before[8];scope_storage::Storage storage;uint32_t after[8];}};
int main(){{
Guard g;for(auto &v:g.before)v=0x12345678;for(auto &v:g.after)v=0x98765432;
for(unsigned repeat=0;repeat<3;++repeat) for(const auto &p:scope_native_profiles){{
const bool compact=p.channels==1;g.storage.bind(compact);
unsigned n=p.node_pairs;auto *adc=g.storage.adc;auto *ts=g.storage.timestamps;
for(unsigned node=0;node<2;++node) for(unsigned i=0;i<n;++i){{
ts[node*n+i]=0xfffffff0U+(node*n+i)*p.ticks;
for(unsigned ch=0;ch<p.channels;++ch)adc[node*n*p.channels+i*p.channels+ch]=(i*(13+16*ch))&((1U<<p.bits)-1);
}}
for(unsigned slot=0;slot<4;++slot){{auto &q=g.storage.queue[slot];
bool valid=compact?scope_validation::validate_node<true,true>(adc,ts,n,p.bits,p.ticks,false,0,q.single_samples):
scope_validation::validate_node<true,false>(adc,ts,n,p.bits,p.ticks,false,0,q.samples);
assert(valid);
for(unsigned i=0;i<n;++i){{
assert((compact?q.single_samples[i].ch1:q.samples[i].ch1)==adc[i*p.channels]);
if(!compact)assert(q.samples[i].ch2==adc[2*i+1]);
}}
}}
for(auto v:g.before)assert(v==0x12345678);for(auto v:g.after)assert(v==0x98765432);
}}
// Legacy CH1 writes ChannelPair; UART scratch must remain after both nodes.
g.storage.bind(false);for(unsigned i=0;i<3584;++i)g.storage.queue[3].samples[i]={{1,0}};
std::memset(g.storage.timestamps+4096,0x5a,sizeof(Packet));
for(auto v:g.after)assert(v==0x98765432);
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp=Path(folder)/'storage.cpp';cpp.write_text(source);binary=cpp.with_suffix('')
            built=subprocess.run(['c++','-std=c++17','-O1','-fsanitize=address,undefined',str(cpp),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            subprocess.run([str(binary)],check=True,capture_output=True)

