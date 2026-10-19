import subprocess,tempfile,unittest
from pathlib import Path
class FrameSendQueueTests(unittest.TestCase):
    def test_fragmentation_backpressure_order_wrap_and_bounded_failure(self):
        header=Path(__file__).resolve().parents[2]/'arduino/v17/relay/frame_send_queue.h'
        code=r'''
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <sys/socket.h>
'''+ '#include "'+str(header)+'"\n'+r'''
static uint8_t wire[400*992];static unsigned used,calls,mode;
static ssize_t sink(int fd,const void*p,size_t n,int flags){
 (void)fd;(void)flags;++calls;
 if(mode==1){errno=EAGAIN;return -1;}
 if(mode==2){errno=EPIPE;return -1;}
 if(calls%5==1){errno=EAGAIN;return -1;}
 if(calls%7==2){errno=EINTR;return -1;}
 if(calls%3==0 && n>800)n=800;
 memcpy(wire+used,p,n);used+=(unsigned)n;return (ssize_t)n;
}
int main(void){
 struct ScopeSendQueue q={0};uint8_t f[992];
 for(unsigned i=0;i<200;++i){memset(f,(int)i,sizeof f);assert(scope_send_frame(&q,0,f,sink)==0);}
 while(q.count){unsigned end=q.count;for(unsigned a=0;a<200 && q.count>=end;++a){
  // Drain existing data without introducing another frame; same partial-write rules.
  ssize_t n=sink(0,q.frames[q.head]+q.offset,992-q.offset,0);
  if(n<0)continue;q.offset+=(unsigned)n;
  if(q.offset==992){q.offset=0;q.head=(q.head+1)%SCOPE_SEND_SLOTS;--q.count;}
 }}
 assert(used==200*992);
 for(unsigned i=0;i<used;++i)assert(wire[i]==(uint8_t)(i/992));
 scope_send_reset(&q);mode=1;
 for(unsigned i=0;i<SCOPE_SEND_SLOTS;++i)assert(scope_send_frame(&q,0,f,sink)==0);
 assert(scope_send_frame(&q,0,f,sink)==-1 && errno==ENOBUFS);
 scope_send_reset(&q);mode=2;assert(scope_send_frame(&q,0,f,sink)==-1 && errno==EPIPE);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.c';p.write_text(code);exe=Path(d)/'test'
            subprocess.run(['cc','-std=c11','-fsanitize=address,undefined',str(p),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
