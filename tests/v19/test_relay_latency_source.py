import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.prepare_latency_trace_v19 import HEADER,instrument,ROOT
from tools.summarize_relay_latency_v19 import summarize


class RelayLatencyTests(unittest.TestCase):
    def test_generator_preserves_original_transfer_and_validation_calls(self):
        original=(ROOT/'arduino/v19/relay/unoq_config_stream.c').read_text()
        candidate=instrument(original)
        for anchor in ('ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)',
                       'scope_batch2_validate(&checker,rx)',
                       'scope_batch2_prepare_tx(tx,command,pc_command,pending)',
                       'scope_send_frame(&send_queue,client,frame,send)',
                       'dual_command(pc_command)'):
            self.assertEqual(candidate.count(anchor),original.count(anchor))
        with self.assertRaises(ValueError):instrument(candidate)

    def test_compiled_accumulator_phase_and_histogram_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            source='''#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
enum {BLOCK=992};
static unsigned get16(const uint8_t *p) {return p[0]|(p[1]<<8);}
static uint32_t get32(const uint8_t *p) {uint32_t n;memcpy(&n,p,4);return n;}
\n#include "trace.h"
'''+'''
int main(void) {
 assert(scope_trace_clock()>0);
 uint8_t frame[1984]={0};frame[6]=12;frame[24]=2;
 uint32_t rate=40000;memcpy(frame+40,&rate,4);
 uint64_t times[8]={0,5000,25000,75000,175000,375000,775000,1375000};
 scope_trace_update(true,frame);scope_trace_observe(times,3);
 assert(scope_trace_groups[2].count==1);
 assert(scope_trace_groups[2].sum[0]==5000);
 assert(scope_trace_groups[2].hist[0][1]==1);
 scope_trace_update(false,frame);
 assert(scope_trace_groups[2].count==0 && !scope_trace_active);
 return 0;
}'''
            (folder/'test.c').write_text(source)
            (folder/'trace.h').write_text(HEADER)
            compiled=subprocess.run(['cc','-O2','-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror',str(folder/'test.c'),'-o',str(folder/'test')],text=True,capture_output=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(folder/'test')],check=True,text=True,capture_output=True)
            row=json.loads(result.stderr.removeprefix('SCOPE_LATENCY ').strip())
            self.assertEqual(row['phase'],2)
            self.assertEqual(row['stages']['spi_ioctl']['sum_ns'],50000)
            summary=summarize(result.stderr)
            self.assertEqual(summary['phases'][2]['stages']['spi_ioctl']['mean_us'],50)
            row['stages']['spi_ioctl']['hist'][0]+=1
            with self.assertRaisesRegex(ValueError,'coverage'):
                summarize('SCOPE_LATENCY '+json.dumps(row))
