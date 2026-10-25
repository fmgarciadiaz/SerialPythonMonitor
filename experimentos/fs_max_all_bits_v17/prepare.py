"""Private candidates based on current production; never changes public profiles."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
TARGETS=[dict(bits=b,channels=1,ticks=t,node_pairs=n,headroom=False,internal_only=True,validation='unmeasured') for b,t,n in ((8,98,3456),(10,124,5568),(12,146,7488),(14,176,5952),(16,1100,3488))]
WARMUP=dict(bits=16,channels=1,ticks=2000,node_pairs=3488,headroom=False,internal_only=True,validation='unmeasured',purpose='ADC16 CH1 format control')
def prepare():
 shutil.copytree(ROOT/'arduino/v17/oscilloscope',EXP/'oscilloscope',dirs_exist_ok=True)
 shutil.copytree(ROOT/'arduino/v17/relay',EXP/'relay',dirs_exist_ok=True)
 profiles=[WARMUP]+TARGETS
 for p in profiles:p['queue_slots']=8 if p['bits']==8 else 4
 for p in profiles:
  assert p['node_pairs']*8+1984<=65536
 sketch=EXP/'oscilloscope/sketch'
 p=sketch/'sample_packing.h';s=p.read_text();anchor='    for (unsigned i = 0; i < count; i += 4) {'
 branch='''    if (bits == 16) {
        for (unsigned i=0;i<count;++i) {
            dest[2*i]=uint8_t(samples[i].ch1);
            dest[2*i+1]=uint8_t(samples[i].ch1 >> 8);
        }
        return count*2U;
    }
'''
 assert s.count(anchor)==1;s=s.replace(anchor,branch+anchor);p.write_text(s)
 p=sketch/'sketch.ino';s=p.read_text();anchor='acquisition::bits==12?576U:496U';assert s.count(anchor)==1
 p.write_text(s.replace(anchor,'acquisition::bits==12?576U:acquisition::bits==14?496U:436U'))
 for folder in (sketch,EXP/'relay'):
  p=folder/'native_profiles.h';s=p.read_text();end=s.index('\n};',s.index('scope_native_profiles[]'))
  s=s[:end]+'\n// Private screening candidates.\n'+''.join(f'    {{{v["bits"]}, 1, {v["ticks"]}, {v["node_pairs"]}}},\n' for v in profiles)+s[end:];p.write_text(s)
  clauses=' || '.join(f'(bits=={v["bits"]} && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in TARGETS if v['bits']!=16)
  p=folder/'high_rate_profile.h';s=p.read_text().replace('return channels==1 && (','return channels==1 && ('+clauses+' || ',1)
  s=s.replace('(ticks==100 || ticks==112)','(ticks==98 || ticks==100 || ticks==112)');p.write_text(s)
 p=EXP/'relay/cpu_profile.h';s=p.read_text().replace('return ','return (channels==1 && ('+' || '.join(f'(bits=={v["bits"]} && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in profiles)+')) || ',1);p.write_text(s)
 (EXP/'candidate_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
if __name__=='__main__':prepare()
