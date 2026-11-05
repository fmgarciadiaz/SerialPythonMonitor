import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from tools.prepare_cycle_trace_v19 import CYCLE_HEADER, HEADER, cycle_instrument, replace_once, ROOT


class CycleTraceTests(unittest.TestCase):
    def test_generator_keeps_transfer_and_ownership_contract(self):
        source=(ROOT/'arduino/v19/relay/unoq_config_stream.c').read_text()
        result=cycle_instrument(source)
        for text in ('ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)',
                     'scope_batch2_validate(&checker,rx)',
                     'scope_send_frame(&send_queue,client,frame,send)'):
            self.assertEqual(result.count(text),source.count(text))
        self.assertIn('scope_cycle_begin(trace_t[0])',result)
        self.assertIn('scope_cycle_end(trace_t,rx)',result)
        with self.assertRaises(ValueError):cycle_instrument(result)

    @unittest.skipUnless(shutil.which('cc'),'C compiler required')
    def test_c_cycle_partition_tail_bound_and_counter_context(self):
        preamble='''#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdbool.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#define BLOCK 992
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static uint32_t get32(const uint8_t *p){return get16(p)|((uint32_t)get16(p+2)<<16);}
static void put32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
'''
        header=replace_once(HEADER,'static void scope_trace_flush(void) {',
            'static void scope_cycle_flush(void);\nstatic void scope_trace_flush(void) {\n    scope_cycle_flush();')
        main='''int main(void){
 uint8_t rx[2*BLOCK]={0};rx[6]=20;rx[64]=1;put32(rx+80,2);put32(rx+92,3);
 (void)scope_trace_clock();scope_trace_update(true,rx);scope_trace_phase=2;
 for(unsigned i=0;i<20;++i){
  uint64_t t[8];for(unsigned j=0;j<8;++j)t[j]=1000+2000*i+100*j;
  put32(rx+8,2*i);put32(rx+72,i);put32(rx+108,800+i);
  scope_cycle_end(t,rx);scope_trace_observe(t,0);scope_cycle_begin(t[0]+1000+i);
 }
 scope_trace_flush();return 0;
}
'''
        from tests.v19.test_relay_wire_metrics import packet
        fixture=','.join(str(byte) for byte in packet()+packet())
        main=main.replace('uint8_t rx[2*BLOCK]={0};rx[6]=20;rx[64]=1;put32(rx+80,2);',
                          'uint8_t rx[2*BLOCK]={'+fixture+'};')
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'test.c';binary=Path(folder)/'test'
            (Path(folder)/'latency.h').write_text(header)
            (Path(folder)/'cycle.h').write_text(CYCLE_HEADER)
            source.write_text(preamble+'#include "latency.h"\n#include "cycle.h"\n'+main)
            compiled=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
        lines=result.stderr.splitlines()
        row=json.loads(next(line[len('SCOPE_CYCLE '):] for line in lines if line.startswith('SCOPE_CYCLE ')))
        self.assertEqual(row['count'],20)
        self.assertEqual(row['covered_ns'],14000)
        self.assertEqual(row['cycle_ns'],row['covered_ns']+row['gap_ns'])
        events=[json.loads(line[len('SCOPE_CYCLE_EVENT '):]) for line in lines if line.startswith('SCOPE_CYCLE_EVENT ')]
        tails=[r for r in events if r['kind']=='slow_cycle']
        self.assertEqual(len(tails),8)
        self.assertTrue(all(event['epoch']==1 for event in events))
        self.assertEqual(tails[0]['node'],19)
        self.assertEqual(tails[0]['previous_node_send_ticks'],819)
        self.assertEqual(tails[0]['gap_ns'],319)
        self.assertEqual(len([r for r in events if r['kind']=='peak_observed']),1)
