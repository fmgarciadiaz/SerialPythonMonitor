from pathlib import Path
import subprocess
import tempfile
import unittest


class BatchTests(unittest.TestCase):
    def test_real_c_buffer_order_flush_and_backpressure(self):
        folder=Path(__file__).resolve().parent/'arduino/historico/v16/relay'
        code=r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <sys/socket.h>
#define BLOCK 992
#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif
static unsigned calls;
static int failure;
static unsigned char wire[BLOCK*8];
static size_t length;
static ssize_t fake_send(int fd,const void *p,size_t n,int flags) {
 assert(fd==7);(void)flags;calls++;
 if(failure) {errno=EAGAIN;return failure==1?-1:(ssize_t)n-1;}
 memcpy(wire+length,p,n);length+=n;return (ssize_t)n;
}
#define send fake_send
#include "tcp_batch.h"
int main(void) {
 unsigned char a[BLOCK],b[BLOCK];memset(a,1,sizeof a);memset(b,2,sizeof b);
 TcpBatch q={0};
 assert(tcp_batch_frame(&q,7,a,1,false,0)==0 && calls==1 && q.used==0);
 assert(!memcmp(wire,a,BLOCK));calls=0;length=0;
 assert(tcp_batch_frame(&q,7,a,2,false,1)==0 && calls==0 && q.used==BLOCK);
 assert(tcp_batch_frame(&q,7,b,2,false,1.0005)==0 && calls==1 && q.used==0);
 assert(length==2*BLOCK && !memcmp(wire,a,BLOCK) && !memcmp(wire+BLOCK,b,BLOCK));
 calls=0;length=0;
 assert(tcp_batch_frame(&q,7,a,2,false,2)==0);
 assert(tcp_batch_frame(&q,7,b,2,true,2.0005)==0 && calls==1);
 assert(length==2*BLOCK && wire[0]==1 && wire[BLOCK]==2); /* ACK after DATA */
 calls=0;length=0;
 assert(tcp_batch_frame(&q,7,a,2,true,3)==0 && calls==1 && length==BLOCK);
 assert(tcp_batch_frame(&q,7,b,2,false,4)==0);
 assert(tcp_batch_frame(&q,7,a,2,false,4.002)==0 && calls==2 && q.used==BLOCK);
 assert(tcp_batch_flush(&q,7)==0 && calls==3); /* timeout without partner */
 for(failure=1;failure<=2;failure++) {
  assert(tcp_batch_frame(&q,7,a,2,false,5)==0);
  assert(tcp_batch_frame(&q,7,b,2,false,5.0001)==-1 && q.used==0);
 }
 failure=0;length=0;
 assert(tcp_batch_frame(&q,7,a,2,false,6)==0);tcp_batch_reset(&q);
 assert(tcp_batch_frame(&q,7,b,2,true,7)==0);
 assert(length==BLOCK && wire[0]==2); /* no abandoned bytes to new session */
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'batch.c';src.write_text(code);binary=Path(tmp)/'batch'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(folder),str(src),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
