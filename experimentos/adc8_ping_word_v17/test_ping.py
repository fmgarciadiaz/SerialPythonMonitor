from pathlib import Path
import subprocess
import tempfile
import unittest

SKETCH=Path(__file__).resolve().parent/'arduino/historico/v16/oscilloscope/sketch'


class PingEquivalenceTests(unittest.TestCase):
    def test_qualification_requires_repeated_chain_gain_and_headroom(self):
        from experimentos.adc8_ping_word_v17.run import PingProbe
        probe=PingProbe.__new__(PingProbe)
        probe.save=lambda:None
        rows=[dict(stage='abba',ticks=ticks,variant=variant,ok=True,headroom_ok=True,
                   metrics=dict(send_mean_us=value))
              for ticks in (114,112) for variant,value in
              [('A',2200),('B',2100),('B',2090),('A',2190)]]
        probe.report={'cases':rows}
        self.assertTrue(probe.gate())
        rows[1]['headroom_ok']=False
        self.assertFalse(probe.gate())
        rows[1]['headroom_ok']=True
        rows[2]['metrics']['send_mean_us']=2195
        self.assertFalse(probe.gate())

    def test_valid_and_adversarial_packets_match_reference(self):
        source=r'''
#include <cstdint>
#include <cstring>
#include <random>
#include <cassert>
#include "benchmark_protocol.h"
using namespace scope_bench;
static void compare(const uint8_t *p, bool expected) {
    assert(valid_ping_reference(p)==expected);
    assert(valid_ping_word(p)==expected);
    assert(valid_ping(p)==expected);
}
int main() {
    std::mt19937 random(713);
    alignas(32) uint8_t p[BLOCK_BYTES], changed[BLOCK_BYTES];
    for (unsigned j=0;j<2048;j++) {
        const uint32_t seq=j<5 ? (uint32_t[]){0,1,0x7fffffffU,0x80000000U,0xffffffffU}[j] : random();
        frame(p,PING,seq); seal(p); compare(p,true);
        if (j<5) for (unsigned i=0;i<BLOCK_BYTES;i++) {
            memcpy(changed,p,BLOCK_BYTES);changed[i]^=1;compare(changed,false);
            if (i<BLOCK_BYTES-CRC_BYTES) {
                seal(changed); compare(changed,false);
            }
        }
        for (unsigned k=0;k<4;k++) {
            for (unsigned i=0;i<BLOCK_BYTES;i++) changed[i]=uint8_t(random());
            if(k&1)seal(changed);
            assert(valid_ping_reference(changed)==valid_ping_word(changed));
        }
    }
    // The function contract does not require aligned callers.
    uint8_t unaligned[BLOCK_BYTES+1];memcpy(unaligned+1,p,BLOCK_BYTES);
    compare(unaligned+1,true);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/'check.cpp';src.write_text(source)
            for variant in (0,1):
                # Include the real header with a temporary selector, preserving
                # both experiment source variants and their hashes.
                header=(SKETCH/'benchmark_protocol.h').read_text().replace(
                    '#include "ping_variant.h"',f'#define SCOPE_WORD_PING {variant}')
                (Path(directory)/'benchmark_protocol.h').write_text(header)
                binary=Path(directory)/f'check{variant}'
                subprocess.run(['c++','-std=c++17','-O2','-I',directory,'-I',str(SKETCH),str(src),'-o',str(binary)],check=True,capture_output=True)
                subprocess.run([str(binary)],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
