"""Relay-only bounded metadata trace for diagnosing ADC8 + DAC contention."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'trace8'
def prepare():
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'wordping'/name,OUT/name,dirs_exist_ok=True)
 shutil.copyfile(EXP/'wordping/candidate_profiles.json',OUT/'candidate_profiles.json')
 p=OUT/'relay/unoq_config_stream.c';s=p.read_text()
 marker='static struct ScopeSendQueue send_queue;'
 s=s.replace(marker,marker+'''
struct ScopeTrace {uint32_t seq,index,node,queue,peak,send,dropped;unsigned txkind,rxkind;double at;};
static struct ScopeTrace trace8[64];static unsigned trace8_next=0,trace8_used=0;
static void trace8_record(const uint8_t *tx,const uint8_t *rx) {
    trace8[trace8_next]=(struct ScopeTrace){get32(rx+8),get32(rx+52),get32(rx+72),
        get32(rx+88),get32(rx+92),get32(rx+108),get32(rx+56),get16(tx+6),get16(rx+6),now()};
    trace8_next=(trace8_next+1)%64;if(trace8_used<64)++trace8_used;
}
static void trace8_dump(void) {
    double previous=0;
    fprintf(stderr,"TRACE8 last %u physical frames (metadata only)\\n",trace8_used);
    for(unsigned i=0;i<trace8_used;++i) {
        const struct ScopeTrace *t=&trace8[(trace8_next+64-trace8_used+i)%64];
        fprintf(stderr,"TRACE8 seq=%"PRIu32" tx=%u rx=%u at=%.9f gap_us=%.3f index=%"PRIu32" node=%"PRIu32" queue=%"PRIu32" peak=%"PRIu32" send=%"PRIu32" dropped=%"PRIu32"\\n",
            t->seq,t->txkind,t->rxkind,t->at,previous?(t->at-previous)*1e6:0,
            t->index,t->node,t->queue,t->peak,t->send,t->dropped);
        previous=t->at;
    }
}
''',1)
 s=s.replace('        DualChecker before=checker;','        trace8_record(tx,rx);\n        DualChecker before=checker;',1)
 s=s.replace('            fprintf(stderr,"Rejected frame (hex): ");','            trace8_dump();\n            fprintf(stderr,"Rejected frame (hex): ");',1)
 # A slow host can close the socket without an integrity error. Preserve the
 # same bounded trace in that path too, without logging healthy transfers.
 s=s.replace('                fprintf(stderr,"PC disconnected or too slow;', '                trace8_dump();\n                fprintf(stderr,"PC disconnected or too slow;',1)
 p.write_text(s)
if __name__=='__main__':prepare()
