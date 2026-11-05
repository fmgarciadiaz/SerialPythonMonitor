#include <sys/socket.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#ifndef QUEUE_HEADER
#define QUEUE_HEADER "frame_send_queue.h"
#endif
#include QUEUE_HEADER
static uint32_t rng=1;
static unsigned calls, blocked, accepted, rejected, recoveries;
static uint8_t expected[128*992];
static size_t pending;
static uint32_t random32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static ssize_t sender(int fd,const void *data,size_t n,int flags){
 (void)fd;assert(flags & MSG_DONTWAIT);assert(flags & MSG_NOSIGNAL);assert(++calls<=2);
 if(blocked || random32()%7==0){errno=(random32()%2)?EAGAIN:EINTR;return -1;}
 size_t k=1+random32()%n;
 assert(k<=pending);assert(memcmp(expected,data,k)==0);
 memmove(expected,expected+k,pending-k);pending-=k;return (ssize_t)k;
}
static void verify(const struct ScopeSendQueue *q){
 assert(q->count<=64);assert(q->offset<992);assert(pending==q->count*992U-q->offset);
 size_t pos=0;
 for(unsigned i=0;i<q->count;++i){unsigned start=i?0:q->offset;size_t n=992-start;
 assert(memcmp(expected+pos,q->frames[(q->head+i)%64]+start,n)==0);pos+=n;}
}
int main(void){
 struct ScopeSendQueue q;scope_send_reset(&q);
 for(unsigned step=0;step<100000;++step){
  uint8_t frame[992];for(unsigned j=0;j<992;++j)frame[j]=(uint8_t)(step*17U+j*31U+(step>>8));
  unsigned was_full=q.count==64;calls=0;blocked=step%401<100;
  // A full candidate pre-drains old bytes before it can accept this frame.
  // The expected tail is speculative until return; callbacks consume only older bytes.
  size_t old_pending=pending;memcpy(expected+pending,frame,992);pending+=992;
  int result=scope_send_frame(&q,0,frame,sender);
  if(result==0){++accepted;if(was_full)++recoveries;}
  else {assert(errno==ENOBUFS);assert(was_full);assert(pending>=992);pending-=992;++rejected;}
  (void)old_pending;verify(&q);
 }
 printf("accepted=%u rejected=%u full_recoveries=%u queued=%u\n",accepted,rejected,recoveries,q.count);
 return 0;
}
