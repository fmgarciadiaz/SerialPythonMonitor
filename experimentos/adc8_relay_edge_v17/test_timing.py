"""Portable C instrumentation contracts; no hardware."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from experimentos.adc8_relay_edge_v17.run import EXP,certified_sources

SOURCE=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include "relay_timing.h"
int main(void){
 struct RelayTiming t;rt_reset(&t);rt_calibrate(&t);
 assert(t.clock_pair.count==128);
 assert(rt_profile(8,1,100,3456)==0 && rt_profile(8,1,98,3456)==1);
 assert(rt_profile(8,1,112,3456)==-1 && rt_profile(8,2,100,3456)==-1);
 assert(rt_bin(1000)==0 && rt_bin(1001)==1 && rt_bin(100000001)==RT_BINS-1);
 t.profiles[0].iterations=2;t.profiles[0].completed=1;
 rt_stage(&t,0,RT_READY,10,1010);rt_stage(&t,0,RT_READY,10,2011);
 rt_stage(&t,-1,RT_READY,0,9999999);
 rt_ready_edge(&t,0,100,90,200,80,1);
 rt_ready_edge(&t,0,100,150,200,80,2);
 rt_ready_edge(&t,0,100,100,200,80,3);
 rt_ready_edge(&t,0,100,70,200,80,4);
 rt_ready_edge(&t,0,100,0,200,80,5);
 rt_ready_edge(&t,0,100,250,200,80,6);
 assert(t.profiles[0].edge_valid==3 && t.profiles[0].edge_preexisting==2 && t.profiles[0].edge_new==2 && t.profiles[0].edge_equal==1);
 assert(t.profiles[0].edge_stale==1 && t.profiles[0].edge_absent==1 && t.profiles[0].edge_future==1);
 for(unsigned i=0;i<10;++i){
  int slot=rt_ready_edge(&t,0,0,100,2000000U+i*1000000U,0,i);
  rt_tail_frame(&t,0,slot,20,i+1,42,3,5,100+i,872,7);
 }
 assert(t.profiles[0].tail_count==8);
 for(unsigned i=0;i<8;++i){assert(t.profiles[0].tails[i].returned_ns>=4000000U);assert(t.profiles[0].tails[i].has_adc_metrics && t.profiles[0].tails[i].queue==3 && t.profiles[0].tails[i].produced>=102);}
 rt_emit(&t,stdout,"low_profile");
 assert(t.profiles[0].iterations==0 && t.clock_pair.count==128);
 assert(t.profiles[0].stages[RT_READY].count==0);
 t.profiles[1].iterations=1;rt_stage(&t,1,RT_SPI,0,2000);
 rt_emit(&t,stdout,"process_exit");
 return 0;
}
'''


class TimingTests(unittest.TestCase):
    def test_c_histograms_profiles_partial_counts_reset_and_clock_control(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'test.c').write_text(SOURCE)
            subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I',str(EXP/'relay'),str(root/'test.c'),'-o',str(root/'test')],check=True)
            output=subprocess.check_output([str(root/'test')],text=True)
        rows=[json.loads(line.removeprefix('SPM_RELAY_TIMING ')) for line in output.splitlines()]
        self.assertEqual(len(rows),2)
        profile=rows[0]['profiles'][0]
        self.assertEqual((profile['iterations'],profile['completed']),(2,1))
        self.assertEqual(profile['stages']['ready_wait']['count'],2)
        self.assertEqual(profile['stages']['ready_wait']['sum_ns'],3001)
        self.assertEqual(profile['stages']['ready_wait']['max_ns'],2001)
        self.assertEqual(rows[1]['profiles'][0]['iterations'],0)
        self.assertEqual(rows[1]['profiles'][1]['stages']['spi_ioctl']['count'],1)
        self.assertEqual(rows[0]['clock_pair']['count'],128)
        self.assertEqual(len(profile['tails']),8)
        self.assertTrue(all(tail['has_adc_metrics'] and tail['node']==42 and tail['queue_peak']==5 for tail in profile['tails']))
        print('clock_pair ns mean/max:',rows[0]['clock_pair']['sum_ns']/128,rows[0]['clock_pair']['max_ns'])

    def test_only_explicit_instrumentation_differs_from_certified_relay(self):
        _,_,_,hashes=certified_sources()
        self.assertIn('relay/relay_timing.h',hashes)
        current=(EXP/'relay/unoq_config_stream.c').read_text()
        self.assertIn('if (now()-progress>=10)',current)
        self.assertLess(current.index('int timing_profile=-1'),current.index('goto done;'))
