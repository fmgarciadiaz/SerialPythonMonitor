"""Private TX-only cache comparison; RX cache ownership remains unchanged."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'txclean'
def prepare():
    for name in ('oscilloscope','relay'):shutil.copytree(EXP/name,OUT/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'candidate_profiles.json',OUT/'candidate_profiles.json')
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text()
    old='    cache_flush_invalidate(high_rate_transport()?active_tx:tx, BLOCK_BYTES);'
    assert s.count(old)==1
    s=s.replace(old,'''    // SPI DMA only reads TX. Keep clean lines resident after publishing them;
    // every frame is cache-line aligned and a whole number of cache lines.
    if(word_transport()) cache_maintain(active_tx,BLOCK_BYTES,LL_DCACHE_COMMAND_CLEAN_BY_ADDR);
    else cache_flush_invalidate(high_rate_transport()?active_tx:tx, BLOCK_BYTES);''')
    p.write_text(s)
if __name__=='__main__':prepare()
