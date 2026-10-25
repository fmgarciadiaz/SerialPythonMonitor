import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = r'''
#include <assert.h>
#include <errno.h>
#include <sys/socket.h>
#include <unistd.h>
#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif
#include "cmd_trace.h"
static struct CommandTrace trace;
static unsigned completions;
static void completed(const uint8_t *frame){
 assert(frame[0]==42);++completions;ct_socket_complete(&trace,1,900);
}
#define SCOPE_FRAME_SOCKET_COMPLETE(frame) completed(frame)
#include "frame_send_queue.h"
static unsigned calls;
static ssize_t partial(int fd,const void *data,size_t len,int flags){
 (void)fd;(void)data;(void)flags;++calls;
 if(calls==1)return 100;
 if(calls==2){errno=EAGAIN;return -1;}
 return (ssize_t)len;
}
int main(void){
 ct_reset(&trace);ct_command(&trace,1,13,9,0,0,480,100,200);
 ct_spi(&trace,1,300,0);ct_spi(&trace,1,400,1);
 ct_ack(&trace,1,4,2,29,480,0,500); /* freezes before send */
 struct ScopeSendQueue q;scope_send_reset(&q);uint8_t frame[992]={42};
 assert(scope_send_frame(&q,0,frame,partial)==0);
 assert(completions==0 && q.offset==100 && q.count==1);
 ct_enqueue(&trace,1,600,q.count);
 assert(scope_send_frame(&q,0,frame,partial)==0);
 assert(completions==2 && q.count==0);
 assert(trace.frozen[0].ack_socket_complete_ns==900);
 assert(trace.stages[CT_ACK_SOCKET].count==1);
 assert(trace.stages[CT_ACK_SOCKET].max_ns==400);
 ct_emit(&trace,stdout,"test");return 0;
}
'''


class RelayTraceTests(unittest.TestCase):
    def test_partial_eagain_completion_and_frozen_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'test.c').write_text(SOURCE)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                            '-I',str(Path(__file__).parent/'relay'),str(root/'test.c'),
                            '-o',str(root/'test')],check=True)
            result = subprocess.check_output([str(root/'test')],text=True)
        data = json.loads(result.removeprefix('SPM_COMMAND_TRACE '))
        self.assertEqual(data['version'],3)
        self.assertEqual(data['records'][0]['ack_socket_complete_ns'],900)
