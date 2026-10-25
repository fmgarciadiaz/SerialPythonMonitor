"""Host-only SPI16 gate: real protocol packers, relay checker and receiver."""
import json
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from experimentos.fs_max_v18 import probe_journal, run_probe
from monitor.v18.receiver import unoq_native
from monitor.v18.receiver.unoq_config_decoder import ConfigurationDecoder

HERE = Path(__file__).resolve().parent
SKETCH = HERE / 'spi16/oscilloscope/sketch'
RELAY = HERE / 'spi16/relay'

PRODUCER = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "spi16_geometry.h"
#include "benchmark_protocol.h"
#include "sample_packing.h"
struct Sample { uint16_t ch1; };
int main() {
    static_assert(scope_spi16::transfer_words(scope_bench::BLOCK_BYTES)==496);
    static_assert(scope_spi16::dma_bytes(false)==2 && scope_spi16::dma_bytes(true)==4);
    static_assert(scope_spi16::fifo_threshold_field(false)==0);
    static_assert(scope_spi16::fifo_threshold_field(true)==1);
    Sample samples[872];
    for(unsigned i=0;i<872;++i) samples[i].ch1=uint16_t((i*17+91)&255);
    uint8_t p[992];
    scope_bench::frame(p,scope_bench::PING,0x80000011U);
    scope_bench::seal(p);
    if(std::fwrite(p,1,sizeof p,stdout)!=sizeof p) return 4;
    for(unsigned seq=0;seq<4;++seq) {
        std::memset(p,0,sizeof p);
        scope_bench::data_frame(p,seq,0x80000011U,0,0,0,992,0,7,9);
        scope_bench::put16(p+6,20);
        scope_bench::put32(p+48,160000000U/88U);
        scope_bench::put32(p+52,seq*872U);
        scope_bench::put16(p+64,872);
        p[66]=8;p[67]=1;
        scope_bench::put32(p+68,88);
        scope_bench::put32(p+80,seq*872U*88U);
        scope_bench::put32(p+84,3488);
        scope_bench::put32(p+88,1);
        scope_bench::put32(p+92,1);
        scope_bench::put32(p+96,50);
        scope_bench::put32(p+100,30);
        scope_bench::put32(p+104,200);
        scope_bench::put32(p+108,100);
        scope_bench::put32(p+112,1);
        if(maxfreq_packing::pack(p+116,samples,872,8)!=872) return 2;
        scope_bench::seal(p);
        if(std::fwrite(p,1,sizeof p,stdout)!=sizeof p) return 3;
    }
    return 0;
}
'''

CHECKER = r'''
#define main base_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
int main(void) {
    init_crc();
    DualChecker checker={0};checker.bits=8;checker.period=(3488U<<16)|88U;
    uint8_t p[992];
    if(fread(p,1,sizeof p,stdin)!=sizeof p || !dual_command(p)) return 4;
    for(unsigned i=0;i<4;++i) {
        if(fread(p,1,sizeof p,stdin)!=sizeof p || !dual_feed(&checker,p)) return 2;
    }
    if(checker.adc.sample_pairs!=3488 || checker.adc.valid_blocks!=4 ||
       checker.adc.previous_sample!=3487 || checker.sequence!=3) return 3;
    return 0;
}
'''


def spi16_wire(memory):
    # Native little-endian 16-bit loads; each SPI frame shifts MSB first.
    assert len(memory) % 2 == 0
    return b''.join(bytes((memory[i+1], memory[i])) for i in range(0,len(memory),2))


def spi16_peer_receive(wire):
    # Linux SPI16 writes each received word back in native little-endian order.
    return spi16_wire(wire)


class SPI16GateTests(unittest.TestCase):
    def build(self, folder, name, source, compiler, include):
        src=folder/(name+('.cpp' if compiler=='c++' else '.c'))
        src.write_text(source)
        out=folder/name
        subprocess.run([compiler,'-O2','-std=c++17' if compiler=='c++' else '-std=c11',
                        '-I',str(include),str(src),'-lm','-o',str(out)],check=True)
        return out

    def test_full_node_bytes_survive_spi16_both_directions(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)
            producer=self.build(folder,'producer',PRODUCER,'c++',SKETCH)
            checker=self.build(folder,'checker',CHECKER,'cc',RELAY)
            logical=subprocess.check_output([str(producer)])
            self.assertEqual(len(logical),5*992)
            wire=b''.join(spi16_wire(logical[i:i+992]) for i in range(0,len(logical),992))
            self.assertEqual(wire[:4],b'CS1P')
            received=b''.join(spi16_peer_receive(wire[i:i+992]) for i in range(0,len(wire),992))
            self.assertEqual(received,logical)
            self.assertNotEqual(wire,logical)  # An SPI8 peer sees a damaged header.
            self.assertEqual(subprocess.run([str(checker)],input=received).returncode,0)
            self.assertNotEqual(subprocess.run([str(checker)],input=wire).returncode,0)
            from experimentos.fs_max_v18.test_wordping import ping
            self.assertEqual(received[:992],bytes(ping(0x80000011)))
            data=received[992:]
            for seq in range(4):
                frame=data[seq*992:(seq+1)*992]
                self.assertEqual(frame[:4],b'SCP1')
                self.assertEqual(struct.unpack_from('<I',frame,32)[0],992)
                self.assertEqual(struct.unpack_from('<I',frame,988)[0],zlib.crc32(frame[:988]))
                self.assertEqual(frame[116:988],bytes((i*17+91)&255 for i in range(872)))
            profiles=json.loads((HERE/'spi16/candidate_profiles.json').read_text())
            with patch.object(unoq_native,'PROFILES',tuple(profiles)):
                decoded=ConfigurationDecoder().feed(data)
            self.assertEqual(len(decoded),3488)
            self.assertEqual([decoded[i][1] for i in (0,871,872,3487)],
                             [(i%872*17+91)&255 for i in (0,871,872,3487)])
            self.assertEqual(decoded[-1][0],3487*88)

    def test_ping_command_and_crc_keep_exact_logical_bytes(self):
        from experimentos.fs_max_v18.test_wordping import ping
        original=bytes(ping(0x80000011))
        self.assertEqual(spi16_peer_receive(spi16_wire(original)),original)
        self.assertEqual(struct.unpack_from('<I',original,988)[0],zlib.crc32(original[:988]))
        self.assertNotEqual(spi16_wire(original)[:4],b'SCP1')

    def test_recipe_stays_private_and_has_unique_app_identity(self):
        rows=run_probe.plan([8],15,[88],recipe='spi16')
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['node_pairs'],rows[0]['queue_slots']),(3488,8))
        self.assertTrue(rows[0]['internal_only'])
        app=probe_journal.APP+'-spi16'
        self.assertEqual(probe_journal.RECIPES[app],'Scope V18 Rate Probe SPI16')
        self.assertIn(app,probe_journal.REMOTE_MANIFEST)
        with self.assertRaises(ValueError):
            probe_journal.adoption_decision([],[],{}, {}, remote_app=app+'-typo')
        from tools.gui_experimental_v18 import APPS,selected_profile
        self.assertEqual(APPS['spi16'],'scope-v18-rate-probe-spi16-main-1')
        self.assertEqual(selected_profile('spi16','8:88')['ticks'],88)


if __name__ == '__main__':
    unittest.main()
