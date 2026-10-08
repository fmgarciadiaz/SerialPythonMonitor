/* Verificador SCP1/v2 independiente: C11, sin bibliotecas externas.
 * --replay permite probar el mismo validador con tramas binarias por stdin.
 * Compilar en Linux: cc -O2 -std=c11 -Wall -Wextra -Werror verificar_spi.c -lm -o verificar_spi
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef __linux__
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <linux/gpio.h>
#include <poll.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <unistd.h>
#endif

enum { BLOCK = 992, HEADER = 16, PAYLOAD = 972, STATUS = 32, PATTERN = 940, VERSION = 3 };
static bool adc_mode = false;
static uint32_t crc_table[256];
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static unsigned get16(const uint8_t *p) { return (unsigned)p[0] | (unsigned)p[1]<<8; }
static void put32(uint8_t *p, uint32_t v) {
    for (unsigned i=0; i<4; ++i) p[i]=(uint8_t)(v>>(8*i));
}
static void init_crc(void) {
    for (unsigned i=0; i<256; ++i) {
        uint32_t c=i;
        for (unsigned j=0; j<8; ++j) c=(c>>1)^((c&1)?UINT32_C(0xedb88320):0);
        crc_table[i]=c;
    }
}
static uint32_t crc32(const uint8_t *p, size_t n) {
    uint32_t c=UINT32_MAX;
    for (size_t i=0; i<n; ++i) c=(c>>8)^crc_table[(c^p[i])&255];
    return c^UINT32_MAX;
}
static uint8_t pattern(uint32_t seq, unsigned i) {
    uint32_t seed=seq*UINT32_C(0x9e3779b1);
    return (uint8_t)((seed>>(8*(i&3)))^(i*17+0x5a));
}
static void ping(uint8_t *p, uint32_t seq) {
    memcpy(p,"SCP1",4); p[4]=VERSION; p[5]=0; p[6]=2; p[7]=0;
    put32(p+8,seq); put32(p+12,PAYLOAD);
    for (unsigned i=0; i<PAYLOAD; ++i) p[HEADER+i]=pattern(seq,i);
    put32(p+BLOCK-4,crc32(p,BLOCK-4));
}
typedef struct {
    uint64_t transfers, valid_blocks, bad_headers, bad_payloads, crc_errors;
    uint64_t missing_blocks, duplicates, out_of_order, ack_errors, counter_resets;
    uint64_t mcu_spi_errors, mcu_bad_commands, mcu_short_transfers;
    uint64_t mcu_timing_blocks, mcu_prepare_us_sum, mcu_check_us_sum;
    uint32_t mcu_prepare_us_max, mcu_check_us_max;
    uint32_t previous, first[3], last[3];
    int32_t last_driver_result, last_driver_error;
    bool have_previous, have_counters;
    uint64_t sample_pairs, sample_gaps, timestamp_errors, adc_errors;
    uint32_t previous_sample, previous_timestamp, dropped_nodes, acquisition_errors;
    bool have_sample;
} Checker;
static void feed(Checker *c, const uint8_t *p, size_t n, bool expect_ack, uint32_t ack) {
    ++c->transfers;
    if (n!=BLOCK) { ++c->bad_headers; return; }
    bool header=memcmp(p,"SCP1",4)==0 && get16(p+4)==VERSION && get16(p+6)==(adc_mode?3:1) && get32(p+12)==PAYLOAD;
    bool crc=get32(p+BLOCK-4)==crc32(p,BLOCK-4);
    c->bad_headers+=!header; c->crc_errors+=!crc;
    if (!header || !crc) return;
    uint32_t seq=get32(p+8);
    if (c->have_previous) {
        uint32_t delta=seq-c->previous;
        if (!delta) ++c->duplicates;
        else if (delta>=UINT32_C(0x80000000)) ++c->out_of_order;
        else { c->missing_blocks+=delta-1; c->previous=seq; }
    } else { c->previous=seq; c->have_previous=true; }
    if (expect_ack && get32(p+16)!=ack) ++c->ack_errors;
    uint32_t counters[3]={get32(p+20),get32(p+24),get32(p+28)};
    if (c->have_counters) {
        uint32_t d[3]; bool reset=false;
        for (unsigned i=0; i<3; ++i) { d[i]=counters[i]-c->last[i]; reset|=d[i]>=UINT32_C(0x80000000); }
        if (reset) ++c->counter_resets;
        else { c->mcu_spi_errors+=d[0]; c->mcu_bad_commands+=d[1]; c->mcu_short_transfers+=d[2]; }
    } else { memcpy(c->first,counters,sizeof counters); c->have_counters=true; }
    memcpy(c->last,counters,sizeof counters);
    c->last_driver_result=(int32_t)get32(p+32); c->last_driver_error=(int32_t)get32(p+36);
    uint32_t prep=get32(p+40), check=get32(p+44);
    ++c->mcu_timing_blocks; c->mcu_prepare_us_sum+=prep; c->mcu_check_us_sum+=check;
    if (prep>c->mcu_prepare_us_max) c->mcu_prepare_us_max=prep;
    if (check>c->mcu_check_us_max) c->mcu_check_us_max=check;
    if (adc_mode) {
        unsigned count=get16(p+64);
        uint32_t index=get32(p+52);
        c->dropped_nodes=get32(p+56); c->acquisition_errors=get32(p+60);
        if (get32(p+48)!=31250 || p[66]!=14 || p[67]!=2 || get32(p+68)!=32 ||
            count>113 || (!count && !get32(p+76)) || get32(p+76)>1 ||
            (count && (get32(p+72)*2048U!=index-index%2048 || count>2048-index%2048))) {
            ++c->bad_payloads; return;
        }
        for (unsigned i=80+count*8; i<BLOCK-4; ++i)
            if (p[i]) { ++c->bad_payloads; return; }
        if (get32(p+76)) ++c->adc_errors;
        for (unsigned i=0; i<count; ++i) {
            const uint8_t *sample=p+80+i*8;
            uint32_t timestamp=get32(sample), current=index+i;
            if (get16(sample+4)>16383 || get16(sample+6)>16383) ++c->adc_errors;
            if (c->have_sample) {
                uint32_t delta=current-c->previous_sample;
                if (!delta || delta>=UINT32_C(0x80000000)) ++c->adc_errors;
                else {
                    c->sample_gaps+=delta-1;
                    if (timestamp-c->previous_timestamp!=delta*32U) ++c->timestamp_errors;
                }
            }
            c->previous_sample=current; c->previous_timestamp=timestamp; c->have_sample=true;
            ++c->sample_pairs;
        }
    } else for (unsigned i=STATUS; i<PAYLOAD; ++i) {
        if (p[HEADER+i]!=pattern(seq,i)) { ++c->bad_payloads; return; }
    }
    ++c->valid_blocks;
}
static bool integrity(const Checker *c) {
    return c->valid_blocks && !(c->bad_headers || c->bad_payloads || c->crc_errors ||
        c->missing_blocks || c->duplicates || c->out_of_order || c->ack_errors ||
        c->sample_gaps || c->timestamp_errors || c->adc_errors || c->dropped_nodes ||
        c->acquisition_errors || (adc_mode && !c->sample_pairs) ||
        c->counter_resets || c->mcu_spi_errors || c->mcu_bad_commands || c->mcu_short_transfers);
}
static double now(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC,&ts)) { perror("clock_gettime"); exit(2); }
    return ts.tv_sec+ts.tv_nsec/1e9;
}
/* READY GPIO v2: initial high is one credit; each subsequent rising edge
 * grants exactly one transfer. Never reuse an old high after an SPI ioctl.
 * Events are queued before checking the initial level, avoiding missed edges.
 */
#ifdef __linux__
typedef struct { int fd; uint32_t sequence; } Ready;
static int ready_open(Ready *r, const char *chip, uint32_t offset) {
    int fd=open(chip,O_RDONLY|O_CLOEXEC);
    if (fd<0) return -1;
    struct gpio_v2_line_request request={0};
    request.offsets[0]=offset; request.num_lines=1; request.event_buffer_size=16;
    request.config.flags=GPIO_V2_LINE_FLAG_INPUT | GPIO_V2_LINE_FLAG_EDGE_RISING | GPIO_V2_LINE_FLAG_BIAS_PULL_DOWN;
    snprintf(request.consumer,sizeof request.consumer,"scope-spi-ready");
    int result=ioctl(fd,GPIO_V2_GET_LINE_IOCTL,&request), saved=errno;
    close(fd); errno=saved;
    if (result<0) return -1;
    r->fd=request.fd; r->sequence=0;
    if (fcntl(r->fd,F_SETFL,O_NONBLOCK)<0) { saved=errno; close(r->fd); errno=saved; return -1; }
    return 0;
}
static int ready_event(Ready *r, double deadline, double after) {
    for (;;) {
        double left=deadline-now();
        if (left<=0) { errno=ETIMEDOUT; return -1; }
        struct pollfd p={r->fd,POLLIN,0};
        int result=poll(&p,1,(int)ceil(left*1000));
        if (result<0 && errno==EINTR) continue;
        if (result<=0) { if (!result) errno=ETIMEDOUT; return -1; }
        if (!(p.revents&POLLIN)) { errno=EIO; return -1; }
        struct gpio_v2_line_event event;
        ssize_t n=read(r->fd,&event,sizeof event);
        if (n<0 && (errno==EAGAIN || errno==EINTR)) continue;
        if (n!=sizeof event) { if (n>=0) errno=EIO; return -1; }
        if (event.id!=GPIO_V2_LINE_EVENT_RISING_EDGE || event.line_seqno!=r->sequence+1) {
            errno=EOVERFLOW; return -1;
        }
        r->sequence=event.line_seqno;
        if (event.timestamp_ns/1e9 < after) continue; // Delayed initial edge is not a new credit.
        return 0;
    }
}
static int ready_initial(Ready *r, double deadline) {
    struct gpio_v2_line_values values={.mask=1};
    if (ioctl(r->fd,GPIO_V2_LINE_GET_VALUES_IOCTL,&values)<0) return -1;
    if (!(values.bits&1) && ready_event(r,deadline,0)<0) return -1;
    // MCU keeps READY high until a transfer: drain only the initial edge
    // BEFORE the first SPI ioctl, so it cannot become a second credit.
    for (;;) {
        struct gpio_v2_line_event event;
        ssize_t n=read(r->fd,&event,sizeof event);
        if (n<0 && errno==EINTR) continue;
        if (n<0 && errno==EAGAIN) return 0;
        if (n!=sizeof event) { if (n>=0) errno=EIO; return -1; }
        if (event.id!=GPIO_V2_LINE_EVENT_RISING_EDGE || event.line_seqno!=r->sequence+1) {
            errno=EOVERFLOW; return -1;
        }
        r->sequence=event.line_seqno;
    }
}
#endif
typedef struct { double prepare, exchange, check, gap, ioctl_s, ioctl_max, ready_wait, ready_max; } Timing;
static void report(const Checker *c, double elapsed, const Timing *t, uint32_t hz,
                   uint32_t configured, double gap, double minimum, int error, const char *ready_chip) {
    double rate=(adc_mode?c->sample_pairs*8.0:c->valid_blocks*(double)PATTERN)/(elapsed>0?elapsed:1e-9);
    printf("{\n  \"implementation\": \"c\", \"protocol_version\": %d,\n",VERSION);
#define COUNT(name) printf("  \"" #name "\": %" PRIu64 ",\n",(uint64_t)c->name)
    COUNT(transfers); COUNT(valid_blocks); COUNT(bad_headers); COUNT(bad_payloads); COUNT(crc_errors);
    COUNT(missing_blocks); COUNT(duplicates); COUNT(out_of_order); COUNT(ack_errors); COUNT(counter_resets);
    COUNT(mcu_spi_errors); COUNT(mcu_bad_commands); COUNT(mcu_short_transfers);
    COUNT(sample_pairs); COUNT(sample_gaps); COUNT(timestamp_errors); COUNT(adc_errors);
    COUNT(dropped_nodes); COUNT(acquisition_errors);
    COUNT(mcu_prepare_us_max); COUNT(mcu_check_us_max);
#undef COUNT
    printf("  \"previous\": ");
    if (c->have_previous) printf("%" PRIu32,c->previous); else printf("null");
    printf(",\n  \"first_counters\": ");
    if (c->have_counters) printf("[%" PRIu32 ",%" PRIu32 ",%" PRIu32 "]",c->first[0],c->first[1],c->first[2]);
    else printf("null");
    printf(",\n  \"last_counters\": ");
    if (c->have_counters) printf("[%" PRIu32 ",%" PRIu32 ",%" PRIu32 "]",c->last[0],c->last[1],c->last[2]);
    else printf("null");
    printf(",\n  \"last_driver_result\": ");
    if (c->have_counters) printf("%" PRId32,c->last_driver_result); else printf("null");
    printf(",\n  \"last_driver_error\": ");
    if (c->have_counters) printf("%" PRId32,c->last_driver_error); else printf("null");
    double blocks=c->mcu_timing_blocks?c->mcu_timing_blocks:1;
    printf(",\n  \"mcu_prepare_us_mean\": %.6f, \"mcu_check_us_mean\": %.6f,\n",
           c->mcu_prepare_us_sum/blocks,c->mcu_check_us_sum/blocks);
    printf("  \"elapsed_s\": %.9f, \"wire_bytes\": %" PRIu64 ", \"wire_Bps\": %.3f,\n",
           elapsed,c->transfers*BLOCK,c->transfers*BLOCK/(elapsed>0?elapsed:1e-9));
    printf("  \"verified_pattern_bytes\": %" PRIu64 ", \"verified_pattern_Bps\": %.3f,\n",adc_mode?0:c->valid_blocks*PATTERN,adc_mode?0:rate);
    printf("  \"adc_mode\": %s, \"verified_sample_Bps\": %.3f, \"sample_pairs_per_second\": %.3f,\n",
           adc_mode?"true":"false",adc_mode?rate:0, c->sample_pairs/(elapsed>0?elapsed:1e-9));
    printf("  \"block_bytes\": %d, \"pattern_bytes_per_block\": %d, \"requested_hz\": %" PRIu32 ", \"configured_hz\": %" PRIu32 ",\n",BLOCK,adc_mode?0:PATTERN,hz,configured);
    printf("  \"gap_us\": %.3f, \"minimum_verified_Bps\": %.3f, \"error_errno\": %d,\n",gap,minimum,error);
    printf("  \"timing_s\": {\"prepare\": %.9f, \"exchange\": %.9f, \"check\": %.9f, \"gap\": %.9f, \"ioctl\": %.9f, \"ioctl_max\": %.9f},\n",
           t->prepare,t->exchange,t->check,t->gap,t->ioctl_s,t->ioctl_max);
    printf("  \"ready_enabled\": %s, \"ready_wait_s\": %.9f, \"ready_wait_max_s\": %.9f,\n",
           ready_chip?"true":"false",t->ready_wait,t->ready_max);
    printf("  \"integrity_pass\": %s, \"throughput_pass\": %s, \"pass\": %s\n}\n",
           integrity(c)?"true":"false",rate>=minimum?"true":"false",
           integrity(c)&&rate>=minimum&&!error?"true":"false");
    fflush(stdout);
}
static double number(const char *s) {
    char *end; errno=0; double v=strtod(s,&end);
    if (errno || end==s || *end || !isfinite(v)) { fprintf(stderr,"Número inválido: %s\n",s); exit(2); }
    return v;
}
int main(int argc, char **argv) {
    uint32_t hz=1000000, configured=0;
    double seconds=10, gap=1000, minimum=750000;
    const char *device="/dev/spidev0.0", *ready_chip=NULL;
    uint32_t ready_line=70;
    bool replay=false;
    init_crc();
    for (int i=1; i<argc; ++i) {
        if (!strcmp(argv[i],"--adc")) { adc_mode=true; minimum=240000; continue; }
        if (!strcmp(argv[i],"--replay")) { replay=true; continue; }
        if (i+1>=argc) { fprintf(stderr,"Falta valor: %s\n",argv[i]); return 2; }
        const char *option=argv[i++], *value=argv[i];
        if (!strcmp(option,"--device")) device=value;
        else if (!strcmp(option,"--ready-chip")) ready_chip=value;
        else if (!strcmp(option,"--ready-line")) {
            double v=number(value);
            if (v<0 || v>UINT32_MAX || v!=(uint32_t)v) return 2;
            ready_line=(uint32_t)v;
        }
        else if (!strcmp(option,"--hz")) {
            double v=number(value);
            if (v<1 || v>UINT32_MAX || v!=(uint32_t)v) return 2;
            hz=(uint32_t)v;
        } else if (!strcmp(option,"--seconds")) seconds=number(value);
        else if (!strcmp(option,"--gap-us")) gap=number(value);
        else if (!strcmp(option,"--min-payload-bps")) minimum=number(value);
        else { fprintf(stderr,"Opción desconocida: %s\n",option); return 2; }
    }
    if (seconds<=0 || gap<0 || gap>1e9 || minimum<=0 || (ready_chip && (gap!=0 || replay))) return 2;
    Checker checker={0}; Timing timing={0};
    uint8_t tx[BLOCK], rx[BLOCK]; uint32_t command=0;
    bool expect_ack=false; int error=0;
    double started=now();
    if (replay) {
        size_t n;
        while ((n=fread(rx,1,BLOCK,stdin))>0) {
            feed(&checker,rx,n,expect_ack,command-1); ++command; expect_ack=true;
        }
        if (ferror(stdin)) error=EIO;
    } else {
#ifdef __linux__
        int fd=open(device,O_RDWR|O_CLOEXEC);
        if (fd<0) { perror("open SPI"); return 2; }
        uint8_t mode=0, bits=8;
        if (flock(fd,LOCK_EX|LOCK_NB)<0 || ioctl(fd,SPI_IOC_WR_MODE,&mode)<0 ||
            ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 || ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&hz)<0 ||
            ioctl(fd,SPI_IOC_RD_MAX_SPEED_HZ,&configured)<0) { perror("configure SPI"); close(fd); return 2; }
        Ready ready={.fd=-1};
        if (ready_chip && ready_open(&ready,ready_chip,ready_line)<0) {
            perror("request READY input"); close(fd); return 2;
        }
        struct spi_ioc_transfer transfer={0};
        transfer.tx_buf=(uintptr_t)tx; transfer.rx_buf=(uintptr_t)rx;
        transfer.len=BLOCK; transfer.speed_hz=hz; transfer.bits_per_word=8;
        started=now(); double progress=started, previous_io_start=0; bool draining=false;
        for (;;) {
            double before=now(); ping(tx,command); double prepared=now();
            memset(rx,0,sizeof rx);
            double waited=0;
            if (ready_chip) {
                double waiting=now();
                int ok=expect_ack ? ready_event(&ready,waiting+1.0,previous_io_start) : ready_initial(&ready,waiting+1.0);
                waited=now()-waiting;
                timing.ready_wait+=waited;
                if (waited>timing.ready_max) timing.ready_max=waited;
                if (ok<0) { error=errno; break; }
            }
            double io_start=now(); previous_io_start=io_start;
            int ret=ioctl(fd,SPI_IOC_MESSAGE(1),&transfer);
            int saved_errno=errno;
            double exchanged=now(), io_time=exchanged-io_start;
            timing.ioctl_s+=io_time;
            if (io_time>timing.ioctl_max) timing.ioctl_max=io_time;
            timing.prepare+=prepared-before; timing.exchange+=exchanged-prepared-waited;
            if (ret<0) { error=saved_errno; break; }
            if (ret!=BLOCK) { error=EIO; break; }
            feed(&checker,rx,BLOCK,expect_ack,command-1);
            double checked=now(); timing.check+=checked-exchanged;
            ++command; expect_ack=true;
            if (draining) break;
            if (gap>0) {
                struct timespec delay={(time_t)(gap/1e6),(long)(fmod(gap,1e6)*1000)};
                while (nanosleep(&delay,&delay)<0 && errno==EINTR) {}
            }
            double current=now(); timing.gap+=current-checked;
            if (current-progress>=10) {
                fprintf(stderr,"progress: transfers=%" PRIu64 " valid=%" PRIu64 " elapsed=%.1f\n",checker.transfers,checker.valid_blocks,current-started);
                progress=current;
            }
            draining=current-started>=seconds;
        }
        if (ready.fd>=0) close(ready.fd);
        close(fd);
#else
        (void)device; (void)tx; (void)ping; (void)ready_line;
        fprintf(stderr,"SPI físico requiere Linux. Usar --replay para pruebas locales.\n"); return 2;
#endif
    }
    double elapsed=now()-started;
    report(&checker,elapsed,&timing,hz,configured,gap,minimum,error,ready_chip);
    return integrity(&checker) && !error && (replay || (adc_mode?checker.sample_pairs*8.0:checker.valid_blocks*(double)PATTERN)/elapsed>=minimum)?0:1;
}
