/* Linux relay: preserve every SCP1 byte through USB/ADB to the PC.
 * Reuse the physically validated SPI/READY and validation implementation. */
#define main benchmark_main
#include "../../../diagnosticos/verificar_spi.c"
#undef main
#include "config_relay_protocol.h"
#ifdef __linux__
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <sys/socket.h>
static volatile sig_atomic_t running=1;
static void stopping(int sig) { (void)sig; running=0; }
int main(void) {
    signal(SIGTERM,stopping); signal(SIGINT,stopping); signal(SIGPIPE,SIG_IGN);
    init_crc(); adc_mode=true;
    int server=socket(AF_INET,SOCK_STREAM|SOCK_CLOEXEC,0), client=-1, fd=-1;
    Ready ready={.fd=-1}; int result=1, one=1;
    if (server<0) { perror("socket"); return 1; }
    struct sockaddr_in address={.sin_family=AF_INET,.sin_port=htons(8765),
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
    fprintf(stderr,"UNO Q stream: 127.0.0.1:8765, SPI 32 MHz, SCP1 dual ADC/control\n");
    while (running) {
        if (pending) { memcpy(tx,pc_command,BLOCK); pending=false; }
        else ping(tx,command & UINT32_C(0x7fffffff)); // Upper half reserved for PC requests.
        // usb_stream.py always resets the MCU before starting this relay.
        // Require a fresh READY edge, not the high level formerly used by the loader.
        int ok=ready_event(&ready,now()+1,previous_io);
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
        }
        previous_io=now();
        if (ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)!=BLOCK) { perror("SPI transfer"); goto done; }
        DualChecker before=checker;
        if (!dual_feed(&checker,rx)) {
            fprintf(stderr,"Dual acquisition/control integrity failure at seq=%" PRIu32 "\n",get32(rx+8));
            fprintf(stderr,"kind=%u crc_received=%08" PRIx32 " crc_calculated=%08" PRIx32
                    " previous_seq=%" PRIu32 " expected_bits=%u expected_period=%" PRIu32
                    " expected_epoch=%" PRIu32 " expected_mode=%u\n",
                    get16(rx+6),get32(rx+508),crc32(rx,508),before.sequence,
                    before.bits,before.period,before.epoch,before.mode);
            fprintf(stderr,"Rejected frame (hex): ");
            for (unsigned i=0;i<BLOCK;++i) fprintf(stderr,"%02x",rx[i]);
            fputc('\n',stderr);
            goto done;
        }
        previous_tx=get32(tx+8);
        ++command;
        // Accumulate one complete PC PING despite arbitrary TCP fragmentation.
        // Invalid/incomplete commands close only the client, never touch the ADC.
        if (client>=0) {
            ssize_t received=recv(client,pc_command+pc_received,BLOCK-pc_received,MSG_DONTWAIT);
            bool close_client=false;
            if (received>0) {
                if (!pc_received) partial_since=now();
                pc_received+=(size_t)received;
                if (pc_received==BLOCK) {
                    if (!dual_command(pc_command)) {
                        fprintf(stderr,"Invalid PC command; closing session\n");
                        close_client=true;
                    } else pending=true;
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
        if (client<0 && (pending || (previous_tx & UINT32_C(0x80000000)) ||
                         (get32(rx+16) & UINT32_C(0x80000000)))) continue;
        int incoming=accept(server,NULL,NULL);
        if (incoming>=0) {
            if (client>=0) close(incoming); // Never replace an active PC session silently.
            else {
                client=incoming; pc_received=0;
                int send_buffer=65536;
                setsockopt(client,SOL_SOCKET,SO_SNDBUF,&send_buffer,sizeof send_buffer);
                setsockopt(client,IPPROTO_TCP,TCP_NODELAY,&one,sizeof one);
                fprintf(stderr,"PC connected at seq=%" PRIu32 "\n",checker.sequence);
            }
        } else if (errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR) { perror("accept"); goto done; }
        if (client>=0) {
            // Bound backpressure: on partial/full queue disconnect, keep draining ADC.
            // A partial frame is never followed by a different frame on that socket.
            ssize_t sent=send(client,rx,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL);
            if (sent!=BLOCK) {
                fprintf(stderr,"PC disconnected or too slow; close session (sent=%zd)\n",sent);
                close(client); client=-1;
            }
        }
        if (now()-progress>=10) {
            fprintf(stderr,"valid=%" PRIu64 " pairs=%" PRIu64 " dropped=%" PRIu32 "\n",
                    checker.adc.valid_blocks,checker.adc.sample_pairs,checker.adc.dropped_nodes);
            progress=now();
        }
    }
    result=0;
done:
    if (client>=0) close(client);
    if (ready.fd>=0) close(ready.fd);
    if (fd>=0) close(fd);
    close(server);
    return result;
}
#else
int main(void) { fprintf(stderr,"El relay requiere Linux.\n"); return 2; }
#endif
