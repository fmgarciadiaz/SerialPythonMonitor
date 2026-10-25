"""Private ADC14 comparison using the SPI40/WORD pipeline; no new buffers."""
import json,shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'word14'
def prepare():
    for name in ('oscilloscope','relay'):shutil.copytree(EXP/'spi40_10_12'/name,OUT/name,dirs_exist_ok=True)
    for folder in (OUT/'oscilloscope/sketch',OUT/'relay'):
        p=folder/'native_profiles.h';s=p.read_text();pos=s.index('\n};',s.index('scope_native_profiles[]'));s=s[:pos]+'\n    {14, 1, 172, 5952},\n    {14, 1, 168, 5952},'+s[pos:];p.write_text(s)
        p=folder/'high_rate_profile.h';s=p.read_text().replace('return channels==1 && (','return channels==1 && ((bits==14 && pairs==5952 && (ticks==172 || ticks==168)) || ',1)
        start=s.index('static inline int scope_spi40(');pos=s.index('return ',start)
        s=s[:pos]+s[pos:].replace('return ','return (channels==1 && bits==14 && pairs==5952 && (ticks==188 || ticks==184 || ticks==180 || ticks==176 || ticks==172 || ticks==168)) || ',1);p.write_text(s)
    p=OUT/'relay/cpu_profile.h';s=p.read_text().replace('return ','return (channels==1 && bits==14 && pairs==5952 && (ticks==172 || ticks==168)) || ',1);p.write_text(s)
    p=OUT/'oscilloscope/sketch/sketch.ino';s=p.read_text();old='acquisition::bits==10?696U:576U';assert s.count(old)==1;p.write_text(s.replace(old,'acquisition::bits==10?696U:acquisition::bits==12?576U:496U'))
    profiles=[dict(bits=14,channels=1,ticks=t,node_pairs=5952,queue_slots=4,headroom=False,internal_only=True,validation='unmeasured') for t in (184,180,176,172,168)]
    (OUT/'candidate_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
if __name__=='__main__':prepare()
