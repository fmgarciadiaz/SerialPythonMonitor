#pragma once
/* Private diagnostic counters. All durations use the relay's monotonic clock. */
struct ScopeTelemetry {
    uint64_t attempts,transfers,spi_failures,send_calls,would_block,interrupted,partial,send_errors,queue_full;
    unsigned backlog_peak,bits,mode;
    uint32_t period,epoch;
    int have_identity;
    double ready_max_s,spi_max_s,service_gap_max_s,last_spi_start;
};
#define SCOPE_DIAG_HISTORY 8U
static struct ScopeTelemetry scope_diag;
static struct ScopeTelemetry scope_diag_history[SCOPE_DIAG_HISTORY];
static unsigned scope_diag_history_next,scope_diag_history_count;
static uint64_t scope_diag_history_overwritten;
static void scope_diag_select(unsigned bits,unsigned mode,uint32_t period,uint32_t epoch) {
    if(scope_diag.have_identity && scope_diag.bits==bits && scope_diag.mode==mode &&
       scope_diag.period==period && scope_diag.epoch==epoch)return;
    if(scope_diag.have_identity) {
        scope_diag_history[scope_diag_history_next]=scope_diag;
        scope_diag_history_next=(scope_diag_history_next+1)%SCOPE_DIAG_HISTORY;
        if(scope_diag_history_count<SCOPE_DIAG_HISTORY)++scope_diag_history_count;
        else ++scope_diag_history_overwritten;
    }
    memset(&scope_diag,0,sizeof scope_diag);
    scope_diag.bits=bits;scope_diag.mode=mode;scope_diag.period=period;scope_diag.epoch=epoch;
    scope_diag.have_identity=1;
}
static void scope_diag_max(double *value,double candidate) {
    if(candidate>*value)*value=candidate;
}
static void scope_diag_ready(double start,double end) {
    scope_diag_max(&scope_diag.ready_max_s,end-start);
}
static void scope_diag_spi_begin(double start) {
    if(scope_diag.attempts)scope_diag_max(&scope_diag.service_gap_max_s,start-scope_diag.last_spi_start);
    scope_diag.last_spi_start=start;
}
static void scope_diag_spi_end(double end,int completed) {
    scope_diag_max(&scope_diag.spi_max_s,end-scope_diag.last_spi_start);
    ++scope_diag.attempts;
    if(completed)++scope_diag.transfers;else ++scope_diag.spi_failures;
}
static void scope_diag_backlog(unsigned count) {
    if(count>scope_diag.backlog_peak)scope_diag.backlog_peak=count;
}
static ssize_t scope_diag_send(int fd,const void *data,size_t size,int flags) {
    ssize_t result=send(fd,data,size,flags);
    int saved_errno=errno;
    ++scope_diag.send_calls;
    if(result<0) {
        if(saved_errno==EAGAIN || saved_errno==EWOULDBLOCK)++scope_diag.would_block;
        else if(saved_errno==EINTR)++scope_diag.interrupted;
        else ++scope_diag.send_errors;
    } else if((size_t)result<size)++scope_diag.partial;
    errno=saved_errno;
    return result;
}
static void scope_diag_print(const char *reason,const struct ScopeTelemetry *record) {
    int saved_errno=errno;
    fprintf(stderr,"V18_DIAG reason=%s bits=%u mode=%u period=%" PRIu32 " epoch=%" PRIu32 " attempts=%" PRIu64 " spi_failures=%" PRIu64 " transfers=%" PRIu64 " ready_max_us=%.1f spi_max_us=%.1f service_gap_max_us=%.1f backlog_peak=%u send_calls=%" PRIu64 " eagain=%" PRIu64 " eintr=%" PRIu64 " partial=%" PRIu64 " send_errors=%" PRIu64 " queue_full=%" PRIu64 "\n",
        reason,record->bits,record->mode,record->period,record->epoch,record->attempts,record->spi_failures,record->transfers,record->ready_max_s*1e6,record->spi_max_s*1e6,
        record->service_gap_max_s*1e6,record->backlog_peak,record->send_calls,
        record->would_block,record->interrupted,record->partial,record->send_errors,record->queue_full);
    errno=saved_errno;
}

static void scope_diag_report(const char *reason) {
    int saved_errno=errno;
    unsigned start=(scope_diag_history_next+SCOPE_DIAG_HISTORY-scope_diag_history_count)%SCOPE_DIAG_HISTORY;
    for(unsigned i=0;i<scope_diag_history_count;++i)
        scope_diag_print("prior_profile",&scope_diag_history[(start+i)%SCOPE_DIAG_HISTORY]);
    scope_diag_print(reason,&scope_diag);
    fprintf(stderr,"V18_DIAG history_overwritten=%" PRIu64 " attribution=pre_transfer_acknowledged_profile\n",scope_diag_history_overwritten);
    errno=saved_errno;
}
