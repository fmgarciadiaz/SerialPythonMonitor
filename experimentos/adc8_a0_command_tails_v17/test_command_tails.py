"""Fixed per-stage command tails; all tests are offline."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from experimentos.adc8_a0_command_tails_v17.run import EXP,STAGES,certified_sources

SOURCE=r'''
#include <assert.h>
#include "cmd_trace.h"
int main(void){
 struct CommandTrace t;ct_reset(&t);
 for(unsigned i=1;i<=20;++i){
  ct_command(&t,i,13,9,0,i*480,480,100,100+i);
  ct_spi(&t,i,200+i,0);ct_spi(&t,i,999,0);ct_spi(&t,i,300+i,1);ct_spi(&t,i,999,1);
  ct_ack(&t,i,2,0,12,i*480,0,400+i);ct_ack(&t,i,2,0,10,0,0,999);
  ct_enqueue(&t,i,500+i,0);ct_enqueue(&t,i,999,0);
 }
 assert(t.stages[CT_FIRST_COMPLETE].count==20 && t.stages[CT_FIRST_COMPLETE].sum_ns==210);
 assert(t.stages[CT_FIRST_COMPLETE].top_count==8 && t.stages[CT_FIRST_COMPLETE].top[0].ns==20 && t.stages[CT_FIRST_COMPLETE].top[7].ns==13);
 assert(t.stages[CT_COMPLETE_SPI].count==20 && t.stages[CT_COMPLETE_SPI].max_ns==100);
 assert(t.stages[CT_SPI_ACK].count==20 && t.stages[CT_ACK_ENQUEUE].count==20 && t.unknown_acks==0);
 struct CtRecord invalid={0};ct_observe(&t,&invalid,CT_FIRST_COMPLETE,0,1);
 invalid.stats_mask=0;ct_observe(&t,&invalid,CT_FIRST_COMPLETE,20,10);
 invalid.stats_mask=0;ct_observe(&t,&invalid,CT_FIRST_COMPLETE,1,(uint64_t)-1);
 assert(t.stages[CT_FIRST_COMPLETE].rejected==3 && t.stages[CT_FIRST_COMPLETE].count==20);
 for(unsigned i=21;i<=160;++i)ct_command(&t,i,13,9,0,i*480,480,100,200);
 assert(t.overwrites==32 && t.stages[CT_SPI_ACK].censored_overwrite==12);
 ct_spi(&t,160,300,0);ct_spi(&t,160,400,1);ct_ack(&t,160,4,2,29,76800,76320,500);
 assert(t.frozen_valid && t.frozen[127].id==160 && t.frozen[127].ack_state==4);
 assert(t.stages[CT_ACK_ENQUEUE].missing_at_freeze==128);
 ct_enqueue(&t,160,600,13);ct_enqueue(&t,160,700,1);
 assert(t.stages[CT_ACK_ENQUEUE].count==21 && t.frozen[127].ack_enqueue_return_ns==600);
 ct_command(&t,161,11,9,3,0,0,700,800);
 assert(t.frozen[127].id==160 && t.commands_after_freeze==1);
 ct_emit(&t,stdout,"low_profile");return 0;
}
'''


class CommandTailTests(unittest.TestCase):
    def test_lifecycle_duplicates_top8_censoring_invalid_intervals_and_freeze(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'test.c').write_text(SOURCE)
            subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I',str(EXP/'relay'),str(root/'test.c'),'-o',str(root/'test')],check=True)
            output=subprocess.check_output([str(root/'test')],text=True)
        result=json.loads(output.removeprefix('SPM_COMMAND_TRACE '))
        self.assertEqual(result['version'],2)
        self.assertEqual(len(result['records']),128)
        stages=result['stages'];self.assertEqual(len(stages),5)
        for stage in stages.values():
            self.assertLessEqual(len(stage['top']),8)
            self.assertEqual([tail['ns'] for tail in stage['top']],sorted([tail['ns'] for tail in stage['top']],reverse=True))
        self.assertEqual(result['records'][-1]['id'],160)
        self.assertEqual(result['records'][-1]['ack_state'],4)

    def test_only_header_changes_from_previous_trace_and_three_independent_cases(self):
        _,_,_,hashes=certified_sources()
        self.assertIn('relay/cmd_trace.h',hashes)
        self.assertEqual([seconds for _,seconds in STAGES],[120,120,120])
