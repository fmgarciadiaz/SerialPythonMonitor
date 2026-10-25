"""Isolated SPI40/WORD comparison for ADC10/12; never edits baseline sources."""
import json,shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent
OUT=EXP/'spi40_10_12'
def prepare():
    for name in ('oscilloscope','relay'):
        shutil.copytree(EXP/name,OUT/name,dirs_exist_ok=True)
    extra='(channels==1 && ((bits==10 && pairs==5568 && (ticks==128 || ticks==126 || ticks==124 || ticks==122)) || (bits==12 && pairs==7488 && (ticks==150 || ticks==148 || ticks==146))))'
    for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
        p=folder/'high_rate_profile.h';s=p.read_text();start=s.index('static inline int scope_spi40(');end=s.index('\n}',start)
        part=s[start:end];part=part.replace('return bits==8',f'return {extra} || (bits==8').replace('pairs==3456;','pairs==3456);');s=s[:start]+part+s[end:]
        s=s.replace('return scope_spi40(bits,channels,ticks,pairs)?8U:4U;','return bits==8 && scope_spi40(bits,channels,ticks,pairs)?8U:4U;')
        p.write_text(s)
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text()
    s=s.replace('static_assert(3456U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES', 'static_assert(7488U*2U*sizeof(uint32_t)+(FRAME_SLOTS-1U)*BLOCK_BYTES')
    old='const unsigned count=min(864U,unsigned(acquisition::node_pairs()-offset));'
    assert s.count(old)==1
    s=s.replace(old,'const unsigned capacity=acquisition::bits==8?864U:acquisition::bits==10?696U:576U;\n                const unsigned count=min(capacity,unsigned(acquisition::node_pairs()-offset));')
    p.write_text(s)
    p=OUT/'relay/unoq_config_stream.c';s=p.read_text();start=s.index('        if(get16(tx+6)==6 && tx[16]==8 &&');end=s.index('            spi40_pending=true;',start)
    s=s[:start]+'''        const ScopeNativeProfile *requested=get16(tx+6)==6?scope_native_find(tx[16],get32(tx+20)):NULL;
        if(requested && scope_spi40(requested->bits,requested->channels,requested->ticks,requested->node_pairs)) {
'''+s[end:];p.write_text(s)
    shutil.copyfile(EXP/'candidate_profiles.json',OUT/'candidate_profiles.json')
    (OUT/'recipe.json').write_text(json.dumps(dict(name='spi40_10_12',base='fs_max_v18',spi_mhz=40,dma_bytes=4,max_scratch_node_pairs=7488,queue_slots_other_bits=4),indent=2)+'\n')
if __name__=='__main__':prepare()
