from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.prepare_pair_send_v19 import HEADER,ROOT


class PairSendTests(unittest.TestCase):
    def test_all_partial_boundaries_errors_and_ring_wrap_preserve_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/'frame_send_queue.h').write_bytes((ROOT/'arduino/v19/relay/frame_send_queue.h').read_bytes())
            (p/'pair_send.h').write_text(HEADER)
            (p/'test.c').write_text(r'''#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <errno.h>
#include <assert.h>
#include "frame_send_queue.h"
#include "pair_send.h"
static uint8_t received[5000];static size_t used;static ssize_t first;static unsigned calls;
static ssize_t fake(int fd,const void *data,size_t n,int flags) {
 (void)fd;(void)flags;++calls;
 ssize_t out=calls==1?first:(ssize_t)n;
 if(out<0) {errno=(int)-out;return -1;}
 if((size_t)out<=n && out) {memcpy(received+used,data,(size_t)out);used+=(size_t)out;}
 return out;
}
int main(void) {
 uint8_t pair[1984],third[992],fourth[992];for(unsigned i=0;i<1984;++i)pair[i]=(uint8_t)(i*37);
 memset(third,0x56,sizeof third);memset(fourth,0xab,sizeof fourth);
 for(unsigned head=0;head<64;++head) {
  for(ssize_t amount=1;amount<=1984;++amount) {
   struct ScopeSendQueue q={0};scope_send_reset(&q);q.head=head;first=amount;calls=used=0;
   assert(scope_send_pair(&q,0,pair,fake)==0);
   assert(scope_send_frame(&q,0,third,fake)==0);
   assert(scope_send_frame(&q,0,fourth,fake)==0);
   assert(!q.count && !q.offset && used==3968);
   assert(!memcmp(received,pair,1984) && !memcmp(received+1984,third,992) && !memcmp(received+2976,fourth,992));
  }
 }
 int transient[]={EAGAIN,EWOULDBLOCK,EINTR};
 for(unsigned i=0;i<3;++i) {
  struct ScopeSendQueue q={0};first=-transient[i];calls=used=0;
  assert(scope_send_pair(&q,0,pair,fake)==0 && q.count==2 && !q.offset);
  assert(scope_send_frame(&q,0,third,fake)==0);
  assert(scope_send_frame(&q,0,fourth,fake)==0 && !q.count);
  assert(used==3968 && !memcmp(received,pair,1984) && !memcmp(received+1984,third,992) && !memcmp(received+2976,fourth,992));
 }
 ssize_t failures[]={0,1985,-EPIPE};
 for(unsigned i=0;i<3;++i) {
  struct ScopeSendQueue q={0};first=failures[i];calls=used=0;
  assert(scope_send_pair(&q,0,pair,fake)<0 && !q.count);
 }
 struct ScopeSendQueue q={0};q.count=1;calls=0;
 assert(scope_send_pair(&q,0,pair,fake)<0 && !calls);
 return 0;
}''')
            result=subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            subprocess.run([str(p/'test')],check=True,timeout=10)
