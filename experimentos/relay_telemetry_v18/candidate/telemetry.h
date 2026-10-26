#pragma once
/* Private diagnostic counters. All durations use the relay's monotonic clock. */
struct ScopeTelemetry {
    uint64_t transfers,send_calls,would_block,interrupted,partial,send_errors,queue_full;
    unsigned backlog_peak;
    double ready_max_s,spi_max_s,service_gap_max_s,last_spi_start;
};
static struct ScopeTelemetry scope_diag;
static void scope_diag_max(double *value,double candidate) {
    if(candidate>*value)*value=candidate;
}
static void scope_diag_ready(double start,double end) {
    scope_diag_max(&scope_diag.ready_max_s,end-start);
}
static void scope_diag_spi_begin(double start) {
    if(scope_diag.transfers)scope_diag_max(&scope_diag.service_gap_max_s,start-scope_diag.last_spi_start);
    scope_diag.last_spi_start=start;
}
static void scope_diag_spi_end(double end) {
    scope_diag_max(&scope_diag.spi_max_s,end-scope_diag.last_spi_start);
    ++scope_diag.transfers;
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
static void scope_diag_report(const char *reason) {
    int saved_errno=errno;
    fprintf(stderr,"V18_DIAG reason=%s transfers=%" PRIu64 " ready_max_us=%.1f spi_max_us=%.1f service_gap_max_us=%.1f backlog_peak=%u send_calls=%" PRIu64 " eagain=%" PRIu64 " eintr=%" PRIu64 " partial=%" PRIu64 " send_errors=%" PRIu64 " queue_full=%" PRIu64 "\n",
        reason,scope_diag.transfers,scope_diag.ready_max_s*1e6,scope_diag.spi_max_s*1e6,
        scope_diag.service_gap_max_s*1e6,scope_diag.backlog_peak,scope_diag.send_calls,
        scope_diag.would_block,scope_diag.interrupted,scope_diag.partial,scope_diag.send_errors,scope_diag.queue_full);
    errno=saved_errno;
}
