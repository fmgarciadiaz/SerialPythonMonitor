import subprocess
import tempfile
import unittest
from pathlib import Path

class TraceTests(unittest.TestCase):
    def test_bounded_ring_trigger_replacement_and_slowest_order(self):
        header=Path(__file__).parent/'arduino/historico/v16/relay/causal_trace.h'
        code=r'''
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <errno.h>
#include <assert.h>
#include <string.h>
static double now(void){errno=EIO;return 1.;}
static uint32_t get32(const uint8_t*p){uint32_t x;memcpy(&x,p,4);return x;}
static uint16_t get16(const uint8_t*p){uint16_t x;memcpy(&x,p,2);return x;}
'''+ '#include "'+str(header.resolve())+'"\n'+r'''
int main(void){
 errno=EAGAIN;assert(trace_now()==1.);assert(errno==EAGAIN);
 for(unsigned i=0;i<3000;++i){
  struct TraceRow r={.seq=i,.peak=i<1500?2:i<2500?3:4};
  r.ns[7]=i;trace_add(r);
 }
 assert(trace_count==3000);assert(trace_peak==4);
 assert(trace_event_used==TRACE_RING+TRACE_POST);
 assert(trace_event[0].seq==2500-TRACE_RING);
 assert(trace_event[TRACE_RING].seq==2500);
 assert(trace_event[TRACE_RING+TRACE_POST-1].seq==2500+TRACE_POST-1);
 assert(trace_top_used==TRACE_TOP);assert(trace_top[0].seq==2999);
 assert(trace_top[TRACE_TOP-1].seq==3000-TRACE_TOP);
 assert(trace_sum[7]==(uint64_t)2999*3000/2);
 uint8_t p[992]={0};uint16_t k=20;uint32_t ticks=100;
 memcpy(p+6,&k,2);memcpy(p+68,&ticks,4);
 double t[8]={2,2.001,2.002,2.003,2.004,2.005,2.006,2.007};
 trace_record(p,t);assert(trace_count==3001);
 trace_dump();return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'test.c';source.write_text(code);binary=Path(d)/'test'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(source),'-o',str(binary)],check=True,capture_output=True)
            result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
        self.assertIn('CAUSAL_SUMMARY count=3001 event_peak=4 event_rows=1152',result.stderr)
        self.assertEqual(sum(line.startswith('CAUSAL event ') for line in result.stderr.splitlines()),1152)

if __name__=='__main__':unittest.main()
