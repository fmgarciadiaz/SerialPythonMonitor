from pathlib import Path
import subprocess
import tempfile
import unittest


class ReadyTests(unittest.TestCase):
    def test_actual_wait_preserves_fresh_edge_and_errors(self):
        folder = Path(__file__).resolve().parent
        source = (folder/'arduino/historico/v16/relay/base_verifier.c').read_text()
        start = source.index('static unsigned ready_spin_us=50;')
        end = source.index('static int ready_initial(', start)
        function = source[start:end]
        prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <math.h>
#include <sys/types.h>
#define GPIO_V2_LINE_EVENT_RISING_EDGE 1
#define POLLIN 1
typedef struct { int fd; uint32_t sequence; } Ready;
struct gpio_v2_line_event { uint64_t timestamp_ns; uint32_t id,line_seqno; };
struct pollfd {int fd;short events,revents;};
static double clock_now;
static int reads,polls,scenario;
static double now(void) {clock_now+=.000001;return clock_now;}
static ssize_t read(int fd,void *out,size_t size) {
 (void)fd; reads++;
 if(reads==1) {errno=EAGAIN;return -1;}
 if(scenario==4) {errno=EINTR;scenario=0;return -1;}
 struct gpio_v2_line_event *e=out;
 e->id=scenario==2?2:1;
 e->line_seqno=scenario==3?9:(uint32_t)(reads-1);
 e->timestamp_ns=reads==2?500000000:2000000000;
 return scenario==5?1:(ssize_t)size;
}
static int poll(struct pollfd *p,int count,int timeout) {
 (void)count;(void)timeout;polls++;p->revents=POLLIN;return 1;
}
'''
        suffix = r'''
static void reset(void) {reads=polls=scenario=0;clock_now=0;errno=0;}
int main(void) {
 for(int spin=0;spin<=50;spin+=50) {
  reset();ready_spin_us=spin;Ready r={.fd=7};
  assert(ready_event(&r,10,1)==0);
  assert(r.sequence==2); /* old event consumed, never grants a transfer */
  assert(polls==(spin==0?1:0));
  for(int bad=2;bad<=3;bad++) {
   reset();ready_spin_us=spin;r.sequence=0;scenario=bad;
   assert(ready_event(&r,10,1)==-1 && errno==EOVERFLOW);
  }
  reset();ready_spin_us=spin;r.sequence=0;scenario=5;
  assert(ready_event(&r,10,1)==-1 && errno==EIO);
  reset();ready_spin_us=spin;r.sequence=0;
  assert(ready_event(&r,0,1)==-1 && errno==ETIMEDOUT);
 }
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'ready.c';src.write_text(prefix+function+suffix)
            binary=Path(tmp)/'ready'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(src),'-lm','-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)


if __name__ == '__main__':
    unittest.main()
