"""Batch2 host gates against the actual ownership and relay helpers."""
import json
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from experimentos.fs_max_v18 import probe_journal, run_probe
from experimentos.fs_max_v18.test_spi16 import PRODUCER
from monitor.v18.receiver import unoq_native
from monitor.v18.receiver.unoq_config_decoder import ConfigurationDecoder

HERE=Path(__file__).resolve().parent
SKETCH=HERE/'batch2/oscilloscope/sketch'
RELAY=HERE/'batch2/relay'

OWNERSHIP=r'''
#include "batch2_ownership.h"
#include "spi16_geometry.h"
using namespace scope_batch2;
int main() {
    if(scope_spi16::physical_bytes!=1984 ||
       scope_spi16::transfer_words(scope_spi16::physical_bytes)!=992 ||
       scope_spi16::logical_result(1984)!=992 ||
       scope_spi16::logical_result(-5)!=-5) return 6;
    const Half normal[2]={{Source::Normal,false},{Source::Idle,false}};
    const Half pipeline[2]={{Source::Pipelined,false},{Source::Pipelined,false}};
    const Half word[2]={{Source::Word,false},{Source::Word,true}};
    if(select_source(false,false,true,true)!=Source::Idle) return 1;
    if(select_source(true,true,true,true)!=Source::Reply) return 2;
    if(credits_after_physical(normal,false).frames!=0 ||
       credits_after_physical(pipeline,false).frames!=0 ||
       credits_after_physical(word,false).nodes!=0) return 3;
    if(credits_after_physical(normal,true).frames!=1 ||
       credits_after_physical(pipeline,true).frames!=2 ||
       credits_after_physical(word,true).nodes!=1) return 4;
    if(!early_slot_release(word[0]) || !early_slot_release(word[1]) ||
       early_slot_release(pipeline[0])) return 5;
    return 0;
}
'''

RELAY_CHECK=r'''
#define main base_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
#include "batch2_relay.h"
int main(int argc,char **argv) {
    if(argc!=2) return 1;
    init_crc();
    uint8_t pc[BLOCK],tx[SCOPE_BATCH2_BYTES],rx[SCOPE_BATCH2_BYTES];
    ping(pc,UINT32_C(0x80000021));
    scope_batch2_prepare_tx(tx,UINT32_C(0x7ffffffe),pc,true);
    if(get32(tx+8)!=UINT32_C(0x7ffffffe) ||
       get32(tx+BLOCK+8)!=UINT32_C(0x80000021) ||
       memcmp(tx+BLOCK,pc,BLOCK) || !dual_command(tx+BLOCK)) return 2;
    if(!scope_batch2_reconnect_guard(false,get32(tx+BLOCK+8),tx)) return 3;
    scope_batch2_prepare_tx(tx,UINT32_C(0x7fffffff),pc,false);
    if(get32(tx+8)!=UINT32_C(0x7fffffff) || get32(tx+BLOCK+8)!=0) return 4;
    uint8_t quiet[SCOPE_BATCH2_BYTES]={0};
    if(scope_batch2_reconnect_guard(false,0,quiet)) return 8;
    if(!scope_batch2_reconnect_guard(true,0,quiet)) return 9;
    put32(quiet+16,UINT32_C(0x80000021));
    if(!scope_batch2_reconnect_guard(false,0,quiet)) return 10;
    put32(quiet+16,0);put32(quiet+BLOCK+16,UINT32_C(0x80000021));
    if(!scope_batch2_reconnect_guard(false,0,quiet)) return 11;
    if(fread(rx,1,sizeof rx,stdin)!=sizeof rx) return 5;
    DualChecker checker={0};checker.bits=8;checker.period=(3488U<<16)|88U;
    const unsigned failed=scope_batch2_validate(&checker,rx);
    if(argv[1][0]=='g') {
        if(failed || checker.adc.sample_pairs!=1744 ||
           checker.adc.valid_blocks!=2 || checker.sequence!=get32(rx+BLOCK+8)) return 6;
    } else {
        if(failed!=2 || checker.adc.sample_pairs || checker.have_sequence) return 7;
    }
    return 0;
}
'''

APPLIED_PRODUCER=r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "acquisition_protocol.h"
#include "benchmark_protocol.h"
#include "sample_packing.h"
struct Sample { uint16_t ch1; };
int main() {
    uint8_t p[992];
    const uint32_t period=(3488U<<16)|88U;
    scope_acq::Reply reply{0x80000031U,8,8,scope_control::APPLIED,
                           scope_control::OK,period,period,1};
    scope_acq::encode(p,0,reply);
    if(std::fwrite(p,1,992,stdout)!=992) return 2;
    Sample samples[872];for(unsigned i=0;i<872;++i)samples[i].ch1=uint16_t(i&255);
    std::memset(p,0,sizeof p);
    scope_bench::data_frame(p,1,0x80000021U,0,0,0,992);
    scope_bench::put16(p+6,20);
    scope_bench::put32(p+48,160000000U/88U);
    scope_bench::put16(p+64,872);p[66]=8;p[67]=1;
    scope_bench::put32(p+68,88);
    scope_bench::put32(p+76,2);
    scope_bench::put32(p+84,3488);
    scope_bench::put32(p+88,1);
    scope_bench::put32(p+92,1);
    maxfreq_packing::pack(p+116,samples,872,8);
    scope_bench::seal(p);
    return std::fwrite(p,1,992,stdout)==992?0:3;
}
'''

APPLIED_CHECK=r'''
#define main base_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
#include "batch2_relay.h"
int main(void) {
    init_crc();uint8_t rx[SCOPE_BATCH2_BYTES];
    if(fread(rx,1,sizeof rx,stdin)!=sizeof rx)return 2;
    DualChecker d={0};d.bits=14;d.period=32;
    if(scope_batch2_validate(&d,rx))return 3;
    if(d.bits!=8 || d.period!=((3488U<<16)|88U) || d.epoch!=1 ||
       d.adc.sample_pairs!=872 || d.sequence!=1)return 4;
    return 0;
}
'''


def build(folder,name,source,compiler,include):
    ext='.cpp' if compiler=='c++' else '.c'
    src=folder/(name+ext);src.write_text(source)
    target=folder/name
    subprocess.run([compiler,'-O2','-std=c++17' if compiler=='c++' else '-std=c11',
                    '-I',str(include),str(src),'-lm','-o',str(target)],check=True)
    return target


class Batch2Tests(unittest.TestCase):
    def test_ownership_and_selection_use_real_helper(self):
        with tempfile.TemporaryDirectory() as name:
            target=build(Path(name),'ownership',OWNERSHIP,'c++',SKETCH)
            subprocess.run([str(target)],check=True)

    def test_relay_atomic_crc_wrap_and_pc_ping_last(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)
            producer=build(folder,'producer',PRODUCER,'c++',SKETCH)
            checker=build(folder,'relay_check',RELAY_CHECK,'cc',RELAY)
            logical=subprocess.check_output([str(producer)])
            self.assertEqual(len(logical),5*992)
            batch=bytearray(logical[992:992+1984])
            # Logical sequence wraps inside a single physical SPI transfer.
            for half,seq in enumerate((0xffffffff,0)):
                struct.pack_into('<I',batch,half*992+8,seq)
                offset=half*992
                struct.pack_into('<I',batch,offset+988,zlib.crc32(batch[offset:offset+988]))
            self.assertEqual(subprocess.run([str(checker),'good'],input=batch).returncode,0)
            batch[992+120]^=1
            self.assertEqual(subprocess.run([str(checker),'bad'],input=batch).returncode,0)

    def test_applied_then_new_samples_same_batch(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)
            producer=build(folder,'applied',APPLIED_PRODUCER,'c++',SKETCH)
            checker=build(folder,'applied_check',APPLIED_CHECK,'cc',RELAY)
            data=subprocess.check_output([str(producer)])
            self.assertEqual(len(data),1984)
            self.assertEqual(subprocess.run([str(checker)],input=data).returncode,0)
            profiles=json.loads((HERE/'batch2/candidate_profiles.json').read_text())
            with patch.object(unoq_native,'PROFILES',tuple(profiles)):
                decoder=ConfigurationDecoder()
                records=decoder.feed(data)
            self.assertEqual(len(records),872)
            self.assertEqual(decoder.config.bits,8)
            self.assertEqual(decoder.epoch,1)
            self.assertEqual(records[-1][1],871&255)

    def test_private_runner_and_gui_identity(self):
        rows=run_probe.plan([8],15,[88],recipe='batch2')
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['node_pairs'],rows[0]['queue_slots']),(3488,8))
        self.assertTrue(rows[0]['internal_only'])
        app=probe_journal.APP+'-batch2'
        self.assertEqual(probe_journal.RECIPES[app],'Scope V18 Rate Probe Batch2')
        self.assertIn(app,probe_journal.REMOTE_MANIFEST)
        from tools.gui_experimental_v18 import APPS,selected_profile
        self.assertEqual(APPS['batch2'],'scope-v18-rate-probe-batch2-main-1')
        self.assertEqual(selected_profile('batch2','8:88')['ticks'],88)


if __name__=='__main__':unittest.main()
