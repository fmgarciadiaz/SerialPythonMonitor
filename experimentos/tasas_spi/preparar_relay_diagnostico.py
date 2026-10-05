"""Generate an isolated relay with RAM-only timing; never edits production sources."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
source = (ROOT/'relay/unoq_config_stream.c').read_text()
metrics = r'''
typedef struct {
    uint64_t frames, samples, idle, ready_hist[7], spi_hist[7], process_hist[7], cycle_hist[7];
    double ready_sum, spi_sum, process_sum, cycle_sum;
    double ready_max, spi_max, process_max, cycle_max;
    uint32_t period, epoch, dropped, fatal;
} RelayTiming;
static RelayTiming timings[16];
static unsigned timing_count;
static void measure(double seconds, double *sum, double *maximum, uint64_t hist[7]) {
    double us=seconds*1e6; unsigned i=0;
    const double limits[6]={100,250,420,1000,5000,16000};
    while(i<6 && us>limits[i]) ++i;
    ++hist[i]; *sum+=us; if(us>*maximum) *maximum=us;
}
static void dump_timings(void) {
    for(unsigned i=0;i<timing_count;++i) {
        RelayTiming *t=&timings[i];
        fprintf(stderr,"TIMING {\"period_us\":%u,\"epoch\":%u,\"frames\":%" PRIu64
            ",\"samples\":%" PRIu64 ",\"idle\":%" PRIu64 ",\"dropped\":%u,\"fatal\":%u",
            t->period,t->epoch,t->frames,t->samples,t->idle,t->dropped,t->fatal);
        const char *names[4]={"ready","spi","process","cycle"};
        double sums[4]={t->ready_sum,t->spi_sum,t->process_sum,t->cycle_sum};
        double maxima[4]={t->ready_max,t->spi_max,t->process_max,t->cycle_max};
        uint64_t *hist[4]={t->ready_hist,t->spi_hist,t->process_hist,t->cycle_hist};
        for(unsigned j=0;j<4;++j) {
            fprintf(stderr,",\"%s_mean_us\":%.3f,\"%s_max_us\":%.3f,\"%s_hist\":[",
                names[j],sums[j]/t->frames,names[j],maxima[j],names[j]);
            for(unsigned k=0;k<7;++k) fprintf(stderr,"%s%" PRIu64,k?",":"",hist[j][k]);
            fputc(']',stderr);
        }
        fprintf(stderr,"}\n");
    }
}
static void record_timing(const uint8_t *rx,double start,double spi_start,double spi_end,double end) {
    if(get16(rx+6)!=3) return;
    uint32_t period=get32(rx+68),epoch=get32(rx+76)>>1;
    if(!timing_count || timings[timing_count-1].period!=period || timings[timing_count-1].epoch!=epoch) {
        if(timing_count==16) return;
        timings[timing_count].period=period;timings[timing_count].epoch=epoch;++timing_count;
    }
    RelayTiming *t=&timings[timing_count-1]; ++t->frames;
    unsigned count=get16(rx+64);t->samples+=count;if(!count)++t->idle;
    t->dropped=get32(rx+56);t->fatal=get32(rx+60);
    measure(spi_start-start,&t->ready_sum,&t->ready_max,t->ready_hist);
    measure(spi_end-spi_start,&t->spi_sum,&t->spi_max,t->spi_hist);
    measure(end-spi_end,&t->process_sum,&t->process_max,t->process_hist);
    measure(end-start,&t->cycle_sum,&t->cycle_max,t->cycle_hist);
}
'''
source=source.replace('int main(void) {',metrics+'\nint main(void) {',1)
source=source.replace('while (running) {','while (running) {\n        double timing_start=now();',1)
source=source.replace('DualChecker before=checker;', 'double timing_spi_end=now();\n        DualChecker before=checker;')
source=source.replace('if (!dual_feed(&checker,rx)) {','if (!dual_feed(&checker,rx)) {\n            record_timing(rx,timing_start,previous_io,timing_spi_end,now());')
source=source.replace('if (now()-progress>=10) {','record_timing(rx,timing_start,previous_io,timing_spi_end,now());\n        if (now()-progress>=10) {')
# Successful-frame timing includes socket processing; rejection ends at validation.
source=source.replace('if (now()-progress>=10) {','if (false && now()-progress>=10) {')
source=source.replace('done:\n','done:\n    dump_timings();\n',1)
output=ROOT/'relay/unoq_timing_stream.c'
output.write_text(source)
print(output)
