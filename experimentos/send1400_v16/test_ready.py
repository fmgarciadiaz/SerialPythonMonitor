"""Verify bounded READY waiting never grants credit from stale/invalid edges."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class ReadyTests(unittest.TestCase):
    def test_ready_credit_and_timeout(self):
        path=Path(__file__).resolve().parent/'arduino/v16/relay/base_verifier.c'
        text=path.read_text();function=text[text.index('static int ready_event('):text.index('static int ready_initial(')]
        source='''#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <math.h>
#include <assert.h>
#include <string.h>
typedef long ssize_t;
#define GPIO_V2_LINE_EVENT_RISING_EDGE 1
#define POLLIN 1
struct gpio_v2_line_event {uint64_t timestamp_ns;uint32_t id,line_seqno;};
struct pollfd {int fd;short events,revents;};
typedef struct {int fd;uint32_t sequence;} Ready;
static double clock_value;
static int scenario,reads,polls;
static double now(void) {clock_value+=0.000001;return clock_value;}
static ssize_t read(int fd,void *out,size_t n) {
 (void)fd;++reads;
 if(scenario==1 && reads==1){errno=EINTR;return -1;}
 if(scenario==2 && !polls){errno=EAGAIN;return -1;}
 if(scenario==3){errno=EAGAIN;return -1;}
 struct gpio_v2_line_event e={.timestamp_ns=1000100000ULL,.id=1,.line_seqno=1};
 if(scenario==4){e.line_seqno=reads;e.timestamp_ns=reads==1?999000000ULL:1000100000ULL;}
 if(scenario==5)e.line_seqno=2;
 if(scenario==6)e.id=0;
 if(scenario==7)return 0;
 memcpy(out,&e,n);return n;
}
static int poll(struct pollfd *p,unsigned n,int timeout) {
 (void)n;assert(timeout>0);++polls;
 if(scenario==3)return 0;
 p->revents=POLLIN;return 1;
}
'''+function+'''
int main(void){
 for(scenario=0;scenario<=7;++scenario){
  Ready r={.fd=1,.sequence=0};reads=polls=0;clock_value=1.0;
  int ok=ready_event(&r,2.0,1.0);
  if(scenario<=2 || scenario==4){assert(ok==0);assert(r.sequence==(scenario==4?2:1));}
  else {assert(ok==-1);assert(errno==(scenario==3?ETIMEDOUT:scenario==5||scenario==6?EOVERFLOW:EIO));}
  if(scenario==2||scenario==3){assert(polls==1);assert(reads>1 && reads<100);}
  else assert(polls==0);
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'ready.c';src.write_text(source);binary=src.with_suffix('')
            subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True)

if __name__=='__main__': unittest.main()
