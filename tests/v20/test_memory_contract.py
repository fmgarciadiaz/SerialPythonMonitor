import hashlib
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from monitor.v20.memory_contract import load_contract,verify_board,verify_output
from monitor.v20.q_support.board import Board
from tools.v20_memory_fix import manifests

ROOT=Path(__file__).resolve().parents[2]


class MemoryContractTests(unittest.TestCase):
    def test_actual_pinned_layout_excludes_original_overlap(self):
        contract=load_contract();begin=contract['begin'];end=begin+0x34060
        self.assertLess(0x20040000,contract['kernel_image_end'])
        self.assertGreaterEqual(begin,contract['kernel_image_end'])
        self.assertLessEqual(end,contract['end']);self.assertEqual(begin%32,0)
        with patch('tools.v20_memory_fix.NEW',ROOT/'respaldos/parejas/v20_before_storage_lifetime_20261101/oscilloscope'):
            old,new=manifests()
        self.assertEqual(set(new)-set(old),{'sketch/acquisition_memory.h'})
        self.assertEqual({p for p in old if old[p]!=new[p]},{'sketch/acquisition.h'})

    def test_all_bsp_files_required_and_changes_fail_closed(self):
        c=load_contract();text='\n'.join(d+'  '+p for p,d in c['bsp_files'].items())
        self.assertEqual(verify_output(text,c),c['bsp_files'])
        for bad in ('',text+'\n'+text.splitlines()[0],text.replace(next(iter(c['bsp_files'].values())),'0'*64)):
            with self.assertRaises(RuntimeError):verify_output(bad,c)
        board=Mock();board.shell.return_value=SimpleNamespace(stdout=text)
        self.assertEqual(verify_board(board),c)
        board.shell.assert_called_once_with('sha256sum',*c['bsp_files'],capture=True)

    def test_board_does_not_reset_or_upload_on_bsp_mismatch(self):
        board=object.__new__(Board);board.config={'ready_boot':{'chip':'unused'},'remote_app':'unused'}
        board.stop=Mock();board.cli=Mock()
        with patch('monitor.v20.memory_contract.verify_board',side_effect=RuntimeError('BSP changed')):
            with self.assertRaises(RuntimeError):board.start()
        board.stop.assert_not_called();board.cli.assert_not_called()

    def test_word_initialization_lifetime_once_and_real_storage_switches(self):
        code=r'''
#include <cassert>
#include <cstring>
#define SERIAL_BLOCK_PAIRS 128U
#define CONFIG_DCACHE_LINE_SIZE 16
#include "generator_protocol.h"
#include "acquisition_storage.h"
#include "acquisition_memory.h"
struct alignas(32) Observed {
 uint32_t values[7];uint32_t tag;
 Observed(){for(unsigned i=0;i<7;++i)assert(!values[i]);tag=123;}
};
int main(){
 alignas(32) unsigned char small[32];memset(small,0xa5,sizeof(small));bool made=false;
 auto &object=scope_acquisition_memory::initialize_once<Observed>(small,made);
 assert(made&&object.tag==123);object.values[0]=99;
 auto &again=scope_acquisition_memory::initialize_once<Observed>(small,made);
 assert(&again==&object&&again.values[0]==99);
 static_assert(scope_acquisition_memory::fits<scope_storage::Storage>(),"bounds");
 alignas(32) unsigned char arena[sizeof(scope_storage::Storage)+64];memset(arena,0xa5,sizeof(arena));
 bool initialized=false;auto &s=scope_acquisition_memory::initialize_once<scope_storage::Storage>(arena+32,initialized);
 for(unsigned i=0;i<sizeof(s);++i)assert(!arena[32+i]);
 for(unsigned i=0;i<32;++i){assert(arena[i]==0xa5);assert(arena[32+sizeof(s)+i]==0xa5);}
 s.bind(true,16,3488);
 for(unsigned slot=0;slot<16;++slot){auto &node=s.at(slot,16);assert(node.single_samples==s.memory.single.fast.samples[slot]);
  node.single_samples[3487].ch1=uint16_t(slot+1);}
 scope_acquisition_memory::initialize_once<scope_storage::Storage>(arena+32,initialized);
 for(unsigned slot=0;slot<16;++slot)assert(s.at(slot,16).single_samples[3487].ch1==slot+1);
 s.bind(false,4);for(unsigned slot=0;slot<4;++slot)assert(s.at(slot).samples==s.memory.dual.samples[slot]);
 for(unsigned pass=0;pass<100;++pass){
  assert(s.bind(true,4));
  for(unsigned slot=0;slot<4;++slot){assert(s.at(slot).single_samples==s.memory.single.samples+slot*SCOPE_NATIVE_MAX_SINGLE);
   s.at(slot).single_samples[SCOPE_NATIVE_MAX_SINGLE-1].ch1=uint16_t(slot+10);}
  auto *adc=s.adc;auto *last=s.at(3).single_samples;
  assert(!s.bind(true,5,100));assert(!s.bind(true,16,3489));assert(!s.bind(true,4,0));assert(!s.bind(false,16));
  assert(s.adc==adc&&last[SCOPE_NATIVE_MAX_SINGLE-1].ch1==13);
  assert(s.bind(false,4));assert(s.bind(true,16,3456));
 }
 s.bind(true,16,3488);for(unsigned slot=0;slot<16;++slot)assert(s.at(slot,16).single_samples==s.memory.single.fast.samples[slot]);
 for(unsigned i=0;i<32;++i){assert(arena[i]==0xa5);assert(arena[32+sizeof(s)+i]==0xa5);}
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary);(p/'test.cpp').write_text(code)
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v20/oscilloscope/sketch'),
                            str(p/'test.cpp'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)

    def test_early_power_and_dma_guard_precede_arena_access(self):
        s=(ROOT/'arduino/v20/oscilloscope/sketch/acquisition.h').read_text().split('static bool start() {',1)[1]
        self.assertLess(s.index('RCC->AHB2ENR1 |= RCC_AHB2ENR1_SRAM3EN'),s.index('initialize_once'))
        self.assertLess(s.index('__DSB()'),s.index('initialize_once'))
        self.assertLess(s.index('DMA_CCR_EN) return false'),s.index('initialize_once'))
        self.assertLess(s.index('initialize_once'),s.index('storage.bind('))

    def test_equal_file_count_cannot_substitute_unaudited_bsp_file(self):
        import json
        contract=load_contract();files=contract['bsp_files']
        key=next(path for path in files if path.endswith('.elf'))
        files[key+'.unrelated']=files.pop(key)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'arduino/v20';folder.mkdir(parents=True)
            (folder/'unoq.json').write_text(json.dumps({'memory_contract':contract}))
            with patch('monitor.v20.memory_contract.ROOT',root):
                with self.assertRaises(ValueError):load_contract()
