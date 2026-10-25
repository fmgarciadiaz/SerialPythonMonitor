"""Split the relay-only trace into READY wait, physical ioctl, and other time."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'trace8time'
def prepare():
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'trace8'/name,OUT/name,dirs_exist_ok=True)
 shutil.copyfile(EXP/'trace8/candidate_profiles.json',OUT/'candidate_profiles.json')
 p=OUT/'relay/unoq_config_stream.c';s=p.read_text()
 s=s.replace('double at;','double at,wait_us,io_us;')
 s=s.replace('const uint8_t *tx,const uint8_t *rx) {','const uint8_t *tx,const uint8_t *rx,double began,double ready_at,double io_at,double done_at) {',1)
 s=s.replace('get16(tx+6),get16(rx+6),now()};','get16(tx+6),get16(rx+6),done_at,(ready_at-began)*1e6,(done_at-io_at)*1e6};',1)
 s=s.replace(' gap_us=%.3f index=', ' gap_us=%.3f wait_us=%.3f io_us=%.3f index=')
 s=s.replace('t->at-previous)*1e6:0,','t->at-previous)*1e6:0,t->wait_us,t->io_us,')
 s=s.replace('        int ok=checker.have_sequence ?', '        const double wait_began=now();\n        int ok=checker.have_sequence ?',1)
 s=s.replace('        if (ok<0)', '        const double ready_at=now();\n        if (ok<0)',1)
 s=s.replace('        trace8_record(tx,rx);','        const double io_done=now();\n        trace8_record(tx,rx,wait_began,ready_at,previous_io,io_done);',1)
 s=s.replace('static volatile sig_atomic_t','''static void trace8_summary(void) {
    if(trace8_used<2)return;
    double wait=0,io=0,gap=0,maxgap=0;unsigned data=0,audio=0,commands=0;
    for(unsigned i=0;i<trace8_used;++i) {
        const struct ScopeTrace *t=&trace8[(trace8_next+64-trace8_used+i)%64];
        wait+=t->wait_us;io+=t->io_us;
        data+=t->rxkind==20;audio+=t->rxkind==12;commands+=t->txkind==13;
        if(i) {
            const struct ScopeTrace *before=&trace8[(trace8_next+64-trace8_used+i-1)%64];
            double dt=(t->at-before->at)*1e6;gap+=dt;if(dt>maxgap)maxgap=dt;
        }
    }
    fprintf(stderr,"TRACE8_SUMMARY frames=%u data=%u audio=%u chunks=%u mean_gap_us=%.3f max_gap_us=%.3f mean_wait_us=%.3f mean_io_us=%.3f\\n",
        trace8_used,data,audio,commands,gap/(trace8_used-1),maxgap,wait/trace8_used,io/trace8_used);
}
static volatile sig_atomic_t''',1)
 s=s.replace('        if (now()-progress>=10) {','        if (now()-progress>=10) {\n            trace8_summary();',1)
 p.write_text(s)
if __name__=='__main__':prepare()
