#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/socket.h>

typedef struct { uint8_t bytes[2*BLOCK]; size_t used; double since; } TcpBatch;
static void tcp_batch_reset(TcpBatch *b) { b->used=0; b->since=0; }
static int tcp_batch_flush(TcpBatch *b,int fd) {
    if(!b->used) return 0;
    size_t expected=b->used;
    ssize_t sent=send(fd,b->bytes,expected,MSG_DONTWAIT|MSG_NOSIGNAL);
    tcp_batch_reset(b);
    return sent==(ssize_t)expected ? 0 : -1;
}
static int tcp_batch_frame(TcpBatch *b,int fd,const uint8_t *frame,
                           unsigned batch_size,bool immediate,double at) {
    if(batch_size==1) {
        // Reference path: no added copy or buffering.
        return send(fd,frame,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL)==BLOCK ? 0 : -1;
    }
    if(b->used && at-b->since>=0.001 && tcp_batch_flush(b,fd)<0) return -1;
    if(!b->used) b->since=at;
    memcpy(b->bytes+b->used,frame,BLOCK);
    b->used+=BLOCK;
    return (immediate || b->used==sizeof b->bytes) ? tcp_batch_flush(b,fd) : 0;
}
