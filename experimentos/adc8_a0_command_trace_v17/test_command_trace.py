"""Portable command lifecycle and frozen bounded evidence, no hardware."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from experimentos.adc8_a0_command_trace_v17.run import EXP,STAGES,certified_sources

SOURCE=r'''
#include <assert.h>
#include "cmd_trace.h"
int main(void){
 struct CommandTrace t;ct_reset(&t);
 /* First bytes in a partial frame do not create a command before completion. */
 assert(t.count==0);
 ct_command(&t,1,13,9,0,480,480,100,200);
 ct_spi(&t,1,300,0);ct_spi(&t,1,400,1);
 ct_ack(&t,1,2,0,12,960,480,500);ct_enqueue(&t,1,600,0);
 assert(ct_find(&t,1)->first_byte_ns==100 && ct_find(&t,1)->complete_ns==200);
 assert(ct_find(&t,1)->spi_start_ns==300 && ct_find(&t,1)->spi_end_ns==400);
 assert(ct_find(&t,1)->ack_enqueue_return_ns==600);
 for(unsigned i=2;i<=140;++i)ct_command(&t,i,13,9,0,i*480,480,i,i+1);
 assert(t.count==128 && t.commands==140 && t.overwrites==12 && !ct_find(&t,1));
 ct_ack(&t,999,2,0,10,1000,900,700);assert(t.unknown_acks==1);
 ct_ack(&t,140,4,2,29,67200,66720,1000);
 assert(t.frozen_valid && t.frozen_count==128 && t.fault_id==140);
 ct_command(&t,141,11,9,3,0,0,1100,1200);
 ct_ack(&t,140,0,0,30,0,0,1300);
 ct_enqueue(&t,140,1400,13);
 assert(t.commands_after_freeze==1 && t.frozen[127].ack_state==4);
 assert(t.frozen[127].ack_enqueue_return_ns==1400 && t.frozen[127].enqueue_queue_count==13);
 ct_emit(&t,stdout,"low_profile");assert(!t.dirty && t.frozen_valid);
 return 0;
}
'''


class CommandTraceTests(unittest.TestCase):
    def test_lifecycle_overwrites_first_underrun_freeze_and_enqueue_annotation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'test.c').write_text(SOURCE)
            subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I',str(EXP/'relay'),str(root/'test.c'),'-o',str(root/'test')],check=True)
            output=subprocess.check_output([str(root/'test')],text=True)
        result=json.loads(output.removeprefix('SPM_COMMAND_TRACE '))
        self.assertEqual((result['commands'],result['overwrites'],result['commands_after_freeze']),(141,12,1))
        self.assertEqual(len(result['records']),128)
        self.assertEqual(result['records'][-1]['id'],140)
        self.assertEqual(result['records'][-1]['ack_state'],4)
        self.assertEqual(result['records'][-1]['ack_enqueue_return_ns'],1400)

    def test_only_command_instrumentation_differs_from_accept_sources(self):
        self.assertEqual(STAGES,(('command_trace_120',120),))
        _,_,_,hashes=certified_sources()
        self.assertIn('relay/cmd_trace.h',hashes)
        current=(EXP/'relay/unoq_config_stream.c').read_text()
        self.assertLess(current.index('if (!dual_feed'),current.index('ct_ack(&command_trace'))
        self.assertIn('if (!pc_received) {partial_since=now();command_first_byte_ns=rt_now();}',current)
