#pragma once
/* Bounded TCP backlog. A partial frame always precedes later frames. */
#define SCOPE_SEND_SLOTS 64U
struct ScopeSendQueue {
    uint8_t frames[SCOPE_SEND_SLOTS][992];
    unsigned head,count,offset;
};
typedef ssize_t (*ScopeSendCall)(int,const void *,size_t,int);
static void scope_send_reset(struct ScopeSendQueue *q) { q->head=q->count=q->offset=0; }
static int scope_send_frame(struct ScopeSendQueue *q,int fd,const uint8_t *frame,ScopeSendCall call) {
    if(q->count==SCOPE_SEND_SLOTS) {errno=ENOBUFS;return -1;}
    memcpy(q->frames[(q->head+q->count)%SCOPE_SEND_SLOTS],frame,992);
    ++q->count;
    // One call normally; at most two to finish a partial frame and recover.
    for(unsigned attempts=0;q->count && attempts<2;++attempts) {
        size_t remaining=992U-q->offset;
        ssize_t n=call(fd,q->frames[q->head]+q->offset,remaining,MSG_DONTWAIT|MSG_NOSIGNAL);
        if(n<0) {
            if(errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR)return 0;
            return -1;
        }
        if(!n || (size_t)n>remaining) {errno=EIO;return -1;}
        q->offset+=(unsigned)n;
        if(q->offset==992) {q->offset=0;q->head=(q->head+1)%SCOPE_SEND_SLOTS;--q->count;}
    }
    return 0;
}
