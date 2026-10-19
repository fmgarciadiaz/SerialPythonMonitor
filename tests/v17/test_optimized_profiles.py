"""Production C/C++ packing and frame validation for the new CH1 profiles."""
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v17.receiver.unoq_native import PROFILES
from monitor.v17.receiver.unoq_usb import ProtocolError
from experimentos.maxfreq_v16 import contract
from experimentos.maxfreq_v16.test_contract import packet

ROOT = Path(__file__).resolve().parents[2]


class OptimizedProfilesTests(unittest.TestCase):
    def test_pending_profiles_cannot_be_selected_in_gui(self):
        from monitor.v17.app import _configuration_supported
        for p in PROFILES:
            if not p.get('optimized_transport'):
                continue
            with self.subTest(bits=p['bits'],ticks=p['ticks']):
                self.assertEqual(_configuration_supported(p['bits'],160000000//p['ticks']),
                    not (p.get('integration_pending',False) or p.get('internal_only',False)))

    def test_production_packing_frames_and_decoder_agree(self):
        sketch = ROOT/'arduino/v17/oscilloscope/sketch'
        relay = ROOT/'arduino/v17/relay'
        packing = f'''#include "{sketch/'sample_packing.h'}"
#include <cassert>
#include <vector>
struct Sample {{unsigned ch1;}};
int main() {{for(unsigned bits:{{8U,10U,12U,14U}})for(unsigned n:{{4U,576U,8192U}}) {{
 std::vector<Sample> x(n);std::vector<unsigned char> bytes(n*bits/8+8,0xaa);
 for(unsigned i=0;i<n;++i)x[i].ch1=(i*739+17)&((1U<<bits)-1);
 x[0].ch1=0;x[1].ch1=(1U<<bits)-1;x[2].ch1=1;x[3].ch1=(1U<<bits)-2;
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
            cpp = folder/'pack.cpp'; cpp.write_text(packing)
            subprocess.run(['c++', '-O2', '-std=c++17', str(cpp), '-o', str(folder/'pack')], check=True)
            subprocess.run([str(folder/'pack')], check=True)
            reference=ROOT/'diagnosticos/referencias/v17_relay_before_proposal/config_relay_protocol.h'
            executables=[]
            for name,body in (('checker',checker),('before',checker.replace(str(relay/'config_relay_protocol.h'),str(reference)))):
                c=folder/(name+'.c');c.write_text(body)
                exe=folder/name
                subprocess.run(['cc','-O2','-std=c11','-I',str(relay),str(c),'-lm','-o',str(exe)],check=True)
                executables.append(exe)
            def verify(bits,period,frames,expected):
                for exe in executables:
                    output=subprocess.run([str(exe),str(bits),str(period)],input=frames,
                        check=True,capture_output=True).stdout
                    self.assertEqual(output,expected,msg=f'{exe.name} ADC{bits}')
            capacities = dict(contract.CAPACITY)
            capacities[12] = 576
            with patch.dict(contract.CAPACITY, capacities):
                for profile in PROFILES:
                    if not profile.get('optimized_transport'):
                        continue
                    bits, ticks, n = (profile[k] for k in ('bits', 'ticks', 'node_pairs'))
                    config = Configuration(bits, 160000000//ticks)
                    self.assertEqual(Configuration.from_wire(bits, config.request_period), config)
                    self.assertEqual(config.channels, 1)
                    node = (1<<32)//n; start = node*n
                    values = [(i*739)&((1<<bits)-1) for i in range(n)]
                    values[-4:]=[0,(1<<bits)-1,1,(1<<bits)-2]
                    frames = [packet(bits,ticks,n,start+offset,node,seq,
                        values[offset:offset+capacities[bits]],0xfffffff0+offset*ticks)
                        for seq,offset in enumerate(range(0,n,capacities[bits]))]
                    decoder = ConfigurationDecoder(); rows = decoder.feed(b''.join(frames))
                    self.assertEqual([row[1] for row in rows], values)
                    self.assertEqual(rows[-1][0], (0xfffffff0+(n-1)*ticks)&0xffffffff)
                    bad = bytearray(frames[-1]); bad[987] = 1; bad = contract.seal(bad)
                    with self.assertRaises(ProtocolError):
                        ConfigurationDecoder().feed(b''.join(frames[:-1])+bad)
                    verify(bits,config.request_period,b''.join(frames)+bad,b'1\n'*len(frames)+b'0\n')
                    for field in (8,52,56,60,68,72,76,80,84):
                        # Recompute CRC: each metadata invariant must still be
                        # checked even when packed values need no reconstruction.
                        corrupt=bytearray(frames[1])
                        struct.pack_into('<I',corrupt,field,struct.unpack_from('<I',corrupt,field)[0]+1)
                        corrupt=contract.seal(corrupt)
                        verify(bits,config.request_period,frames[0]+corrupt,b'1\n0\n')
                    for field in (64,66,67,88,92):
                        corrupt=bytearray(frames[1])
                        if field==64:struct.pack_into('<H',corrupt,64,struct.unpack_from('<H',corrupt,64)[0]+1)
                        elif field in (66,67):corrupt[field]+=1
                        else:struct.pack_into('<I',corrupt,field,profile.get('queue_slots',4)+1)
                        verify(bits,config.request_period,frames[0]+contract.seal(corrupt),b'1\n0\n')
                    crc_bad=bytearray(frames[1]);crc_bad[116]^=1
                    verify(bits,config.request_period,frames[0]+crc_bad,b'1\n0\n')
                    # With a repaired CRC, another N-bit value remains in range
                    # under both validators; the old loop adds no range evidence.
                    verify(bits,config.request_period,frames[0]+contract.seal(crc_bad),b'1\n1\n')


if __name__ == '__main__':
    unittest.main()
