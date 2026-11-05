#include <sys/socket.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include "frame_send_queue.h"
static unsigned calls, mode, completed;
static unsigned char seen[64*992];
static size_t used;
static ssize_t sender(int fd,const void *data,size_t n,int flags) {
    (void)fd;(void)flags;++calls;
    if(mode==1){errno=EAGAIN;return -1;}
    if(mode==2)n=n>100?100:n;
    if(mode==3){errno=EPIPE;return -1;}
    memcpy(seen+used,data,n);used+=n;++completed;return n;
}
static void full(struct ScopeSendQueue *q) {
    scope_send_reset(q);q->count=64;
    for(unsigned i=0;i<64;++i)memset(q->frames[i],i,992);
    calls=completed=used=0;
}
int main(void) {
    struct ScopeSendQueue q;uint8_t next[992];memset(next,64,992);
    full(&q);mode=0;
    assert(scope_send_frame(&q,0,next,sender)==0);
    assert(calls==2 && q.count==63 && q.head==2);
    assert(q.frames[0][0]==64 && seen[0]==0 && seen[992]==1);
    full(&q);mode=1;
    assert(scope_send_frame(&q,0,next,sender)==-1 && errno==ENOBUFS);
    assert(calls==1 && q.count==64 && q.offset==0 && q.frames[0][0]==0);
    full(&q);mode=2;
    assert(scope_send_frame(&q,0,next,sender)==-1 && errno==ENOBUFS);
    assert(calls==2 && q.offset==200 && q.count==64 && q.frames[0][0]==0);
    mode=0;calls=0;
    assert(scope_send_frame(&q,0,next,sender)==0 && calls==2);
    assert(q.count==63 && q.offset==0);
    for(unsigned i=0;i<992;++i)assert(seen[i]==0);
    full(&q);mode=3;
    assert(scope_send_frame(&q,0,next,sender)==-1 && errno==EPIPE && calls==1);
    scope_send_reset(&q);calls=used=0;mode=0;
    assert(scope_send_frame(&q,0,next,sender)==0 && q.count==0 && calls==1);
    return 0;
}
