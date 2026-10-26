import json,subprocess,tempfile,unittest
from pathlib import Path
from experimentos.relay_telemetry_v18.prepare import ROOT,HERE,manifest

class TelemetryTests(unittest.TestCase):
    def test_candidate_changes_only_instrumented_relay_and_new_header(self):
        receipt=json.loads((HERE/'candidate_v4.manifest.json').read_text())
        self.assertEqual(receipt['baseline'],manifest(ROOT/'arduino/v18/relay'))
        candidate=manifest(HERE/'candidate_v4');self.assertEqual(receipt['candidate'],candidate)
        self.assertEqual(set(candidate)-set(receipt['baseline']),{'telemetry.h'})
        self.assertEqual({p for p in receipt['baseline'] if receipt['baseline'][p]!=candidate[p]}, {'unoq_config_stream.c'})
    def test_partial_send_retry_errno_and_queue_saturation_keep_wire_bytes(self):
        program=r'''
#include <stdint.h>
#include <stddef.h>
#include <sys/types.h>
#include <errno.h>
#include <stdio.h>
#include <inttypes.h>
#include <string.h>
#define MSG_DONTWAIT 1
#define MSG_NOSIGNAL 2
static unsigned calls=0,blocked=1;
static uint8_t wire[4000];static size_t used=0;
static ssize_t fake_send(int fd,const void *data,size_t size,int flags) {
    (void)fd;(void)flags;++calls;
    if(blocked){errno=EAGAIN;return -1;}
    size_t n=size>113?113:size;memcpy(wire+used,data,n);used+=n;errno=EINPROGRESS;return (ssize_t)n;
}
#define send fake_send
#include "telemetry.h"
#include "frame_send_queue.h"
int main(void) {
    struct ScopeSendQueue q={0};uint8_t a[992],b[992];memset(a,17,sizeof a);memset(b,33,sizeof b);
    scope_diag_select(8,0,86,3);
    scope_diag_ready(1.,1.002);scope_diag_spi_begin(2.);scope_diag_spi_end(2.001,1);
    scope_diag_spi_begin(2.004);scope_diag_spi_end(2.0045,1);
    if(scope_diag.transfers!=2 || scope_diag.ready_max_s<.00199 || scope_diag.spi_max_s<.00099 || scope_diag.service_gap_max_s<.00399)return 1;
    if(scope_send_frame(&q,1,a,scope_diag_send)!=0 || errno!=EAGAIN || scope_diag.would_block!=1 || q.count!=1)return 2;
    blocked=0;
    if(scope_send_frame(&q,1,b,scope_diag_send)!=0 || errno!=EINPROGRESS)return 3;
    /* Flush using the same callback, preserving byte order and partial offsets. */
    while(q.count) {
        size_t remaining=992-q.offset;ssize_t n=scope_diag_send(1,q.frames[q.head]+q.offset,remaining,3);
        if(n<=0)return 4;q.offset+=(unsigned)n;
        if(q.offset==992){q.offset=0;q.head=(q.head+1)%SCOPE_SEND_SLOTS;--q.count;}
    }
    if(used!=1984 || memcmp(wire,a,992) || memcmp(wire+992,b,992) || !scope_diag.partial)return 5;
    blocked=1;scope_send_reset(&q);
    for(unsigned i=0;i<SCOPE_SEND_SLOTS;i++)if(scope_send_frame(&q,1,a,scope_diag_send))return 6;
    unsigned count=q.count;if(scope_send_frame(&q,1,b,scope_diag_send)!=-1 || errno!=ENOBUFS || q.count!=count)return 7;
    scope_diag_backlog(count);if(scope_diag.backlog_peak!=64)return 8;
    scope_diag_select(10,0,118,4);
    if(scope_diag.attempts || scope_diag.ready_max_s || scope_diag.service_gap_max_s)return 10;
    scope_diag_spi_begin(10.);scope_diag_spi_end(10.5,0);
    if(scope_diag.attempts!=1 || scope_diag.transfers || scope_diag.spi_failures!=1 || scope_diag.spi_max_s!=.5)return 11;
    scope_diag_select(10,0,118,4);if(scope_diag.attempts!=1)return 12;
    for(unsigned i=5;i<16;++i)scope_diag_select(10,0,118,i);
    if(scope_diag_history_count!=8 || scope_diag_history_overwritten!=4)return 13;
    errno=ERANGE;scope_diag_report("test");if(errno!=ERANGE)return 9;
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);source=path/'test.c';source.write_text(program)
            result=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-I',str(HERE/'candidate_v4'),'-I',str(ROOT/'arduino/v18/relay'),str(source),'-o',str(path/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(path/'test')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('reason=test',run.stderr)
