"""Use all 872 payload bytes per ADC8 frame; private 3488-sample nodes."""
import json,shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'full8'
def prepare():
    for name in ('oscilloscope','relay'):shutil.copytree(EXP/name,OUT/name,dirs_exist_ok=True)
    for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
        p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'));s=s[:pos]+'\n    {8, 1, 88, 3488},'+s[pos:];p.write_text(s)
        p=folder/'high_rate_profile.h';s=p.read_text().replace('return channels==1 && (','return channels==1 && ((bits==8 && ticks==88 && pairs==3488) || ',1)
        start=s.index('static inline int scope_spi40(');pos=s.index('return ',start)
        s=s[:pos]+s[pos:].replace('return ','return (bits==8 && channels==1 && ticks==88 && pairs==3488) || (',1)
        a=s.index('static inline int scope_spi40(');b=s.index('\n}',a);part=s[a:b].replace('&& pairs==3456;','&& pairs==3456);');s=s[:a]+part+s[b:];p.write_text(s)
    p=OUT/'oscilloscope/sketch/acquisition_storage.h';s=p.read_text();s=s.replace('3456U','3488U').replace('3456-sample','3488-sample');p.write_text(s)
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text().replace('static_assert(3456U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES','static_assert(3488U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES')
    old='const unsigned count=min(864U,unsigned(acquisition::node_pairs()-offset));';assert s.count(old)==1;s=s.replace(old,'const unsigned capacity=acquisition::node_pairs()==3488?872U:864U;\n                const unsigned count=min(capacity,unsigned(acquisition::node_pairs()-offset));');p.write_text(s)
    p=OUT/'relay/cpu_profile.h';s=p.read_text().replace('return ','return (bits==8 && channels==1 && ticks==88 && pairs==3488) || ',1);p.write_text(s)
    p=OUT/'relay/unoq_config_stream.c';s=p.read_text();a=s.index('        if(get16(tx+6)==6 && tx[16]==8 &&');b=s.index('            spi40_pending=true;',a)
    s=s[:a]+'''        const ScopeNativeProfile *requested=get16(tx+6)==6?scope_native_find(tx[16],get32(tx+20)):NULL;
        if(requested && scope_spi40(requested->bits,requested->channels,requested->ticks,requested->node_pairs)) {
'''+s[b:];p.write_text(s)
    (OUT/'candidate_profiles.json').write_text(json.dumps([dict(bits=8,channels=1,ticks=88,node_pairs=3488,queue_slots=8,headroom=False,internal_only=True,validation='unmeasured')],indent=2)+'\n')
if __name__=='__main__':prepare()
