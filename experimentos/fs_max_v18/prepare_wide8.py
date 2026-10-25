"""Private ADC8 node-size comparison, same total queued sample capacity."""
import json,shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'wide8'
def prepare():
    for name in ('oscilloscope','relay'):shutil.copytree(EXP/name,OUT/name,dirs_exist_ok=True)
    for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
        p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'));s=s[:pos]+'\n    {8, 1, 88, 6912},'+s[pos:];p.write_text(s)
        p=folder/'high_rate_profile.h';s=p.read_text().replace('return channels==1 && (','return channels==1 && ((bits==8 && ticks==88 && pairs==6912) || ',1)
        s=s.replace('return bits==8 && channels==1 &&','return (bits==8 && channels==1 && ticks==88 && pairs==6912) || (bits==8 && channels==1 &&',1).replace('&& pairs==3456;','&& pairs==3456);',1)
        s=s.replace('return scope_spi40(bits,channels,ticks,pairs)?8U:4U;','return pairs==3456 && scope_spi40(bits,channels,ticks,pairs)?8U:4U;');p.write_text(s)
    p=OUT/'relay/cpu_profile.h';s=p.read_text().replace('return ','return (bits==8 && channels==1 && ticks==88 && pairs==6912) || ',1);p.write_text(s)
    p=OUT/'relay/unoq_config_stream.c';s=p.read_text();start=s.index('        if(get16(tx+6)==6 && tx[16]==8 &&');end=s.index('            spi40_pending=true;',start)
    s=s[:start]+'''        const ScopeNativeProfile *requested=get16(tx+6)==6?scope_native_find(tx[16],get32(tx+20)):NULL;
        if(requested && scope_spi40(requested->bits,requested->channels,requested->ticks,requested->node_pairs)) {
'''+s[end:];p.write_text(s)
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text().replace('static_assert(3456U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES','static_assert(6912U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES');p.write_text(s)
    profile=dict(bits=8,channels=1,ticks=88,node_pairs=6912,queue_slots=4,headroom=False,internal_only=True,validation='unmeasured')
    (OUT/'candidate_profiles.json').write_text(json.dumps([profile],indent=2)+'\n')
    (OUT/'recipe.json').write_text(json.dumps(dict(name='wide8',queued_samples=4*6912,baseline_queued_samples=8*3456,new_buffers=False),indent=2)+'\n')
if __name__=='__main__':prepare()
