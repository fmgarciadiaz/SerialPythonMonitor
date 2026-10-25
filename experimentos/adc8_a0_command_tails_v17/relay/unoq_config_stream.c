#define _GNU_SOURCE
/* Linux relay: preserve every SCP1 byte through USB/ADB to the PC.
 * Reuse the physically validated SPI/READY and validation implementation. */
#define main benchmark_main
#include "base_verifier.c"
#undef main
#include "config_relay_protocol.h"
#include "transport_policy.h"
#ifdef __linux__
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <sched.h>
#include <sys/socket.h>
#include "cpu_runtime.h"
#include "cpu_profile.h"
#include "frame_send_queue.h"
#include "relay_timing.h"
#include "accept_policy.h"
#include "cmd_trace.h"
static struct ScopeSendQueue send_queue;
static struct RelayTiming relay_timing;
static struct CommandTrace command_trace;
static volatile sig_atomic_t running=1;
static void stopping(int sig) { (void)sig; running=0; }
int main(void) {
    unsigned accept_every;
    if(!scope_accept_interval(getenv("SCOPE_ADC8_ACCEPT_EVERY"),&accept_every)) {
        fprintf(stderr,"SCOPE_ADC8_ACCEPT_EVERY must be 1 or 8\n");return 2;
    }
    signal(SIGTERM,stopping); signal(SIGINT,stopping); signal(SIGPIPE,SIG_IGN);
    init_crc(); adc_mode=true;
    int server=socket(AF_INET,SOCK_STREAM|SOCK_CLOEXEC,0), client=-1, fd=-1;
    Ready ready={.fd=-1}; int result=1, one=1;
    int timing_profile=-1;uint64_t frame_started=0,stage_started=0;
    int timing_tail=-1;
    struct ScopeAcceptPolicy accept_policy={.phase=0,.every=accept_every};
    uint64_t command_first_byte_ns=0;
    if (server<0) { perror("socket"); return 1; }
    struct sockaddr_in address={.sin_family=AF_INET,.sin_port=htons(8766),
                                .sin_addr={.s_addr=htonl(INADDR_LOOPBACK)}};
    if (setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&one,sizeof one)<0 ||
        bind(server,(struct sockaddr *)&address,sizeof address)<0 || listen(server,1)<0 ||
        fcntl(server,F_SETFL,O_NONBLOCK)<0) { perror("listen"); goto done; }
    fd=open("/dev/spidev0.0",O_RDWR|O_CLOEXEC);
    uint8_t mode=0,bits=8; uint32_t hz=32000000;
    if (fd<0 || flock(fd,LOCK_EX|LOCK_NB)<0 || ioctl(fd,SPI_IOC_WR_MODE,&mode)<0 ||
        ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 || ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0) {
        perror("SPI"); goto done;
    }
    if (ready_open(&ready,"/dev/gpiochip1",70)<0) { perror("READY"); goto done; }
    uint8_t tx[BLOCK],rx[BLOCK];
    struct spi_ioc_transfer transfer={.tx_buf=(uintptr_t)tx,.rx_buf=(uintptr_t)rx,
                                    .len=BLOCK,.speed_hz=hz,.bits_per_word=8};
    DualChecker checker={.period=32,.bits=14}; uint32_t command=0; 
    double previous_io=0,progress=now(),partial_since=0;
    uint8_t pc_command[BLOCK]; size_t pc_received=0;
    bool pending=false; uint32_t previous_tx=0;
    bool spi40_pending=false;
    bool cpu_pending=false;
    rt_reset(&relay_timing);relay_timing.accept_every=accept_every;rt_calibrate(&relay_timing);
    ct_reset(&command_trace);
    fprintf(stderr,"UNO Q stream: 127.0.0.1:8766, SPI 32 MHz, SCP1 dual ADC/control\n");
    while (running) {
        timing_tail=-1;
        const ScopeNativeProfile *entry=scope_native_find(checker.bits,checker.period);
        timing_profile=entry && !checker.mode?rt_profile(entry->bits,entry->channels,entry->ticks,entry->node_pairs):-1;
        if(timing_profile>=0){++relay_timing.profiles[timing_profile].iterations;frame_started=rt_now();}
        if (pending) { memcpy(tx,pc_command,BLOCK); pending=false; }
        else ping(tx,command & UINT32_C(0x7fffffff)); // Upper half reserved for PC requests.
        if(timing_profile>=0)stage_started=rt_now();
        // Register events before reading the first level: READY can already be
        // asserted when userspace starts. Consume that first credit only once.
        // All later transfers still require a fresh edge after the previous I/O.
        int ok=checker.have_sequence ? ready_event(&ready,now()+1,previous_io)
                                     : ready_initial(&ready,now()+10);
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_READY,stage_started,ended);timing_tail=rt_ready_edge(&relay_timing,timing_profile,stage_started,ready.accepted_edge_ns,ended,(uint64_t)(previous_io*1e9),checker.sequence);stage_started=ended;}
        if (ok<0) { if (running) perror("READY wait"); goto done; }
        if (!checker.have_sequence) {
            // PG13 is also the loader handoff. A queued startup rise can
            // precede SPI setup. Settle only the first credit, then verify
            // that READY is still asserted; packet validation stays strict.
            struct timespec settle={.tv_sec=0,.tv_nsec=20000000};
            while (nanosleep(&settle,&settle)<0 && errno==EINTR && running) {}
            struct gpio_v2_line_values level={.mask=1};
            if (ioctl(ready.fd,GPIO_V2_LINE_GET_VALUES_IOCTL,&level)<0) { perror("READY level");goto done; }
            if (!(level.bits&1)) continue;
            // Drain a rise queued during settling before consuming the initial
            // credit, so that it cannot authorize a second SPI transfer.
            if (ready_initial(&ready,now()+10)<0) { perror("READY initial");goto done; }
        }
        if(get16(tx+6)==6) {
            const ScopeNativeProfile *wanted=scope_native_find(tx[16],get32(tx+20));
            if(wanted && scope_cpu_profile(wanted->bits,wanted->channels,wanted->ticks,wanted->node_pairs)) {
                cpu_pending=true;
                if(scope_cpu_runtime(true)<0) {perror("CPU policy before acquisition");goto done;}
            }
        }
        if(get16(tx+6)==6 && tx[16]==8 &&
            ((get32(tx+20)&0xffffU)==100 || (get32(tx+20)&0xffffU)==112) &&
            (get32(tx+20)>>16)==3456) {
            spi40_pending=true;
            if(scope_cpu_runtime(true)<0) {perror("SPI40 CPU policy");goto done;}
            struct sched_param priority={.sched_priority=10};
            if(sched_setscheduler(0,SCHED_FIFO,&priority)<0) {perror("SPI40 scheduler");goto done;}
            hz=40000000U;
            if(ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0) {perror("SPI40 clock");goto done;}
            transfer.speed_hz=hz;high_rate_ready=true;
        }
        previous_io=now();
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_COMMAND_POLICY,stage_started,ended);stage_started=ended;}
        unsigned trace_tx_kind=get16(tx+6);
        if(trace_tx_kind==11 || trace_tx_kind==13)ct_spi(&command_trace,get32(tx+8),rt_now(),0);
        if (ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)!=BLOCK) { perror("SPI transfer"); goto done; }
        if(trace_tx_kind==11 || trace_tx_kind==13)ct_spi(&command_trace,get32(tx+8),rt_now(),1);
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_SPI,stage_started,ended);stage_started=ended;}
        DualChecker before=checker;
        if (!dual_feed(&checker,rx)) {
            fprintf(stderr,"Dual acquisition/control integrity failure at seq=%" PRIu32 "\n",get32(rx+8));
            fprintf(stderr,"kind=%u crc_received=%08" PRIx32 " crc_calculated=%08" PRIx32
                    " previous_seq=%" PRIu32 " expected_bits=%u expected_period=%" PRIu32
                    " expected_epoch=%" PRIu32 " expected_mode=%u\n",
                    get16(rx+6),get32(rx+988),crc32(rx,988),before.sequence,
                    before.bits,before.period,before.epoch,before.mode);
            fprintf(stderr,"Rejected frame (hex): ");
            for (unsigned i=0;i<BLOCK;++i) fprintf(stderr,"%02x",rx[i]);
            fputc('\n',stderr);
            goto done;
        }
        if(get16(rx+6)==12)ct_ack(&command_trace,get32(rx+16),rx[24],rx[25],get16(rx+26),get32(rx+28),get32(rx+32),rt_now());
        if(timing_tail>=0)rt_tail_frame(&relay_timing,timing_profile,timing_tail,get16(rx+6),get32(rx+8),get32(rx+72),get32(rx+88),get32(rx+92),get32(rx+112),get16(rx+64),get32(rx+76)>>1);
        const ScopeNativeProfile *profile=scope_native_find(checker.bits,checker.period);
        bool fast=profile && !checker.mode && scope_fast_transport(profile->bits,profile->channels,profile->ticks,profile->node_pairs);
        if(get16(rx+6)==7 && (rx[22]==2 || rx[22]==3)) {spi40_pending=false;cpu_pending=false;}
        bool spi40=spi40_pending || (profile && !checker.mode && scope_spi40(profile->bits,profile->channels,profile->ticks,profile->node_pairs));
        bool cpu=cpu_pending || (profile && !checker.mode && scope_cpu_profile(profile->bits,profile->channels,profile->ticks,profile->node_pairs));
        fast=fast || spi40 || cpu_pending; // Keep FIFO10 through the pending handoff.
        if(scope_cpu_runtime(cpu)<0) {perror("SPI40 CPU policy transition");goto done;}
        if(fast!=high_rate_ready || hz!=(spi40?40000000U:fast?38000000U:32000000U)) {
            struct sched_param priority={.sched_priority=fast?10:0};
            if(sched_setscheduler(0,fast?SCHED_FIFO:SCHED_OTHER,&priority)<0) {perror("profile scheduler");goto done;}
            struct sched_param actual={0};
            int policy=sched_getscheduler(0);
            if(sched_getparam(0,&actual)<0 || policy!=(fast?SCHED_FIFO:SCHED_OTHER) || actual.sched_priority!=(fast?10:0)) {
                fprintf(stderr,"profile scheduler did not apply\n");goto done;
            }
            hz=spi40?40000000U:fast?38000000U:32000000U;
            if(ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0) {perror("profile SPI clock");goto done;}
            transfer.speed_hz=hz;high_rate_ready=fast;
            fprintf(stderr,"V16 transport: SPI %u MHz, %s (policy=%d priority=%d), READY %s\n",hz/1000000U,fast?"FIFO10":"normal",policy,actual.sched_priority,fast?"spin50us":"poll");
        }
        previous_tx=get32(tx+8);
        ++command;
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_CHECK_POLICY,stage_started,ended);stage_started=ended;}
        // Accumulate one complete PC PING despite arbitrary TCP fragmentation.
        if (!before.have_sequence) fprintf(stderr,"SPI ready: first verified frame\n");
        // Invalid/incomplete commands close only the client, never touch the ADC.
        if (client>=0) {
            uint64_t socket_started=timing_profile>=0?rt_now():0;
            ssize_t received=recv(client,pc_command+pc_received,BLOCK-pc_received,MSG_DONTWAIT);
            int received_errno=errno;
            if(timing_profile>=0)rt_stage(&relay_timing,timing_profile,RT_RECV,socket_started,rt_now());
            errno=received_errno;
            bool close_client=false;
            if (received>0) {
                if (!pc_received) {partial_since=now();command_first_byte_ns=rt_now();}
                pc_received+=(size_t)received;
                if (pc_received==BLOCK) {
                    if (!dual_command(pc_command)) {
                        fprintf(stderr,"Invalid PC command; closing session\n");
                        close_client=true;
                    } else {
                        pending=true;
                        unsigned trace_kind=get16(pc_command+6);
                        if(trace_kind==11 || trace_kind==13)ct_command(&command_trace,get32(pc_command+8),trace_kind,get32(pc_command+16),trace_kind==11?pc_command[20]:0,trace_kind==13?get32(pc_command+20):0,trace_kind==13?get16(pc_command+24):0,command_first_byte_ns,rt_now());
                    }
                    pc_received=0;
                }
            } else if (!received || (errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR))
                close_client=true;
            if (pc_received && now()-partial_since>1) close_client=true;
            if (close_client) {
                close(client); client=-1; pc_received=0;
                fprintf(stderr,"PC closed or rejected; acquisition continues\n");
            }
        }
        // An abandoned PC request may still be in the SPI pipeline. Do not
        // hand its ACK to a new ordinary V8 session expecting sequential PINGs.
        int accept_eligible=profile && !checker.mode && scope_accept_profile(profile->bits,profile->channels,profile->ticks,profile->node_pairs);
        if(client<0 || !accept_eligible)accept_policy.phase=0;
        if (client<0 && (pending || (previous_tx & UINT32_C(0x80000000)) ||
                         (get32(rx+16) & UINT32_C(0x80000000)))) {
            if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_SOCKET,stage_started,ended);rt_stage(&relay_timing,timing_profile,RT_FRAME,frame_started,ended);timing_profile=-1;}
            continue;
        }
        int accept_due=scope_accept_due(&accept_policy,client>=0,accept_eligible);
        if(timing_profile>=0){++relay_timing.profiles[timing_profile].accept_poll_frames;
            if(accept_due)++relay_timing.profiles[timing_profile].accept_calls;
            else ++relay_timing.profiles[timing_profile].accept_skipped;}
        if(accept_due) {
            uint64_t accept_started=timing_profile>=0?rt_now():0;
            int incoming=accept(server,NULL,NULL);
            int accept_errno=errno;
            if(timing_profile>=0)rt_stage(&relay_timing,timing_profile,RT_ACCEPT,accept_started,rt_now());
            errno=accept_errno;
            if (incoming>=0) {
                if (client>=0) close(incoming); // Never replace an active PC session silently.
                else {
                    client=incoming; pc_received=0;scope_send_reset(&send_queue);
                    int send_buffer=65536;
                    setsockopt(client,SOL_SOCKET,SO_SNDBUF,&send_buffer,sizeof send_buffer);
                    setsockopt(client,IPPROTO_TCP,TCP_NODELAY,&one,sizeof one);
                    fprintf(stderr,"PC connected at seq=%" PRIu32 "\n",checker.sequence);
                }
            } else if (errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR) { perror("accept"); goto done; }
        }
        if (client>=0) {
            // Bound backpressure: on partial/full queue disconnect, keep draining ADC.
            // A partial frame is never followed by a different frame on that socket.
            ssize_t sent;
            uint64_t send_started=timing_profile>=0?rt_now():0;
            if(cpu || send_queue.count) {
                if(scope_send_frame(&send_queue,client,rx,send)<0)sent=-1;
                else sent=BLOCK;
            } else sent=send(client,rx,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL);
            int sent_errno=errno;
            if(timing_profile>=0)rt_stage(&relay_timing,timing_profile,RT_SEND,send_started,rt_now());
            if(get16(rx+6)==12)ct_enqueue(&command_trace,get32(rx+16),rt_now(),send_queue.count);
            errno=sent_errno;
            if (sent!=BLOCK) {
                fprintf(stderr,"PC disconnected or too slow; close session (sent=%zd)\n",sent);
                close(client); client=-1;
            }
        }
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_SOCKET,stage_started,ended);stage_started=ended;
            if(send_queue.count>relay_timing.profiles[timing_profile].socket_queue_peak)relay_timing.profiles[timing_profile].socket_queue_peak=send_queue.count;}
        if (now()-progress>=10) {
            fprintf(stderr,"valid=%" PRIu64 " pairs=%" PRIu64 " dropped=%" PRIu32 "\n",
                    checker.adc.valid_blocks,checker.adc.sample_pairs,checker.adc.dropped_nodes);
            progress=now();
        }
        if(timing_profile>=0){uint64_t ended=rt_now();rt_stage(&relay_timing,timing_profile,RT_HEARTBEAT,stage_started,ended);rt_stage(&relay_timing,timing_profile,RT_FRAME,frame_started,ended);++relay_timing.profiles[timing_profile].completed;timing_profile=-1;}
        if(!profile && !checker.mode && checker.period>=25 && checker.period<=65535){rt_emit(&relay_timing,stderr,"low_profile");ct_emit(&command_trace,stderr,"low_profile");}
    }
    result=0;
done:
    if(timing_profile>=0)rt_stage(&relay_timing,timing_profile,RT_FRAME,frame_started,rt_now());
    rt_emit(&relay_timing,stderr,"process_exit");
    ct_emit(&command_trace,stderr,"process_exit");
    if(scope_cpu_restore()<0) {perror("SPI40 CPU policy restore");result=1;}
    if (client>=0) close(client);
    if (ready.fd>=0) close(ready.fd);
    if (fd>=0) close(fd);
    close(server);
    return result;
}
#else
int main(void) { fprintf(stderr,"El relay requiere Linux.\n"); return 2; }
#endif
