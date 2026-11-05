#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#include <signal.h>
#include "frame_send_queue.h"
static unsigned calls;
static ssize_t counted_send(int fd,const void *p,size_t n,int flags){assert(++calls<=2);return send(fd,p,n,flags);}
static uint8_t value(size_t byte){size_t id=byte/992,j=byte%992;return (uint8_t)(id*17+j*31+(id>>8));}
static void read_available(int fd,size_t *received){
 uint8_t buf[4096];ssize_t n;
 while((n=recv(fd,buf,sizeof(buf),MSG_DONTWAIT))>0){for(ssize_t j=0;j<n;++j)assert(buf[j]==value(*received+(size_t)j));*received+=(size_t)n;}
 assert(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK));
}
int main(void){
 alarm(30);
 int listener=socket(AF_INET,SOCK_STREAM,0);assert(listener>=0);
 struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 assert(bind(listener,(void *)&a,sizeof(a))==0);assert(listen(listener,1)==0);
 socklen_t len=sizeof(a);assert(getsockname(listener,(void *)&a,&len)==0);
 int writer=socket(AF_INET,SOCK_STREAM,0);assert(writer>=0);assert(connect(writer,(void *)&a,sizeof(a))==0);
 fprintf(stderr,"connected\n");int reader=accept(listener,0,0);assert(reader>=0);close(listener);
 assert(fcntl(writer,F_SETFL,O_NONBLOCK)==0);assert(fcntl(reader,F_SETFL,O_NONBLOCK)==0);
 int bytes=4096;assert(setsockopt(writer,SOL_SOCKET,SO_SNDBUF,&bytes,sizeof(bytes))==0);
 struct ScopeSendQueue q;scope_send_reset(&q);size_t accepted=0,received=0;unsigned rejects=0,recovered=0;
 fprintf(stderr,"begin\n");for(unsigned step=0;step<10000;++step){
  uint8_t frame[992];for(unsigned j=0;j<992;++j)frame[j]=value(accepted*992+j);
  calls=0;unsigned full=q.count==64;int result=scope_send_frame(&q,writer,frame,counted_send);
  if(result==0){++accepted;if(full)++recovered;}else{assert(errno==ENOBUFS);++rejects;}
  if(step%1000>=700)read_available(reader,&received);
 }
 fprintf(stderr,"loop done\n");
 // Drain the final queue with the same bounded primitive, then verify all accepted bytes.
 for(unsigned step=0;q.count && step<100000;++step){unsigned budget=2;calls=0;assert(scope_send_drain(&q,writer,counted_send,&budget)==0);read_available(reader,&received);}
 assert(q.count==0);assert(shutdown(writer,SHUT_WR)==0);
 assert(fcntl(reader,F_SETFL,0)==0);
 uint8_t buf[4096];ssize_t n;while((n=recv(reader,buf,sizeof(buf),0))>0){for(ssize_t j=0;j<n;++j)assert(buf[j]==value(received+(size_t)j));received+=(size_t)n;}
 assert(n==0 && received==accepted*992);assert(rejects>0 && recovered>0);
 printf("TCP bytes=%zu accepted=%zu rejects=%u full_recoveries=%u FIFO=PASS\n",received,accepted,rejects,recovered);
 close(reader);close(writer);return 0;
}
