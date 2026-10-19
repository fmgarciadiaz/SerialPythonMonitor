"""Prepare selected private rates; ADC10/12 active, ADC14/16 deferred."""
import json,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
TARGETS=[dict(bits=b,channels=1,ticks=t,node_pairs=n,headroom=False,validation='unmeasured',internal_only=True)
         for b,t,n in ((10,128,5568),(12,150,7488),(14,176,3968),(16,1050,3488))]
WARMUP=dict(bits=16,channels=1,ticks=2000,node_pairs=3488,headroom=False,validation='unmeasured',internal_only=True,purpose='Preparación ADC16 CH1')
def prepare(selected=(10,12)):
 targets=[p for p in TARGETS if p['bits'] in selected]
 profiles=([WARMUP] if 16 in selected else [])+targets
 for profile in targets:
  if profile['bits']!=16 and 2*profile['node_pairs']*4+2*992>2*8192*4:
   raise ValueError('ADC timestamp DMA overlaps SPI frame scratch')
 shutil.copytree(ROOT/'arduino/v17/oscilloscope',EXP/'oscilloscope',dirs_exist_ok=True)
 shutil.copytree(ROOT/'experimentos/otros_bits_cpu_relay_v17/relay',EXP/'relay',dirs_exist_ok=True)
 sketch=EXP/'oscilloscope/sketch'
 for name in ('wav_protocol.h','wav_dma.h','wav.h','crc32_fast.h','generator.h','wav_storage.h'):
  shutil.copyfile(ROOT/'experimentos/radio_dac_headroom_v17/oscilloscope/sketch'/name,sketch/name)
 # Preserve negotiated PCM capacity while retaining this experiment's CPU policy.
 shutil.copyfile(ROOT/'experimentos/radio_dac_headroom_v17/relay/config_relay_protocol.h',EXP/'relay/config_relay_protocol.h')
 if 16 in selected:
  shutil.copyfile(ROOT/'experimentos/adc16_ch1_format_v17/sample_packing.h',sketch/'sample_packing.h')
  p=sketch/'sketch.ino';s=p.read_text();old='acquisition::bits==12?576U:496U';assert old in s
  s=s.replace(old,'acquisition::bits==12?576U:acquisition::bits==14?496U:436U');p.write_text(s)
 for folder in (sketch,EXP/'relay'):
  p=folder/'native_profiles.h';s=p.read_text();end=s.index('\n};',s.index('scope_native_profiles[]'))
  rows=''.join(f'    {{{p["bits"]}, 1, {p["ticks"]}, {p["node_pairs"]}}},\n' for p in profiles)
  s=s[:end]+'\n    // Isolated unmeasured candidates; not public rates.\n'+rows+s[end:];p.write_text(s)
  p=folder/'high_rate_profile.h';s=p.read_text();clauses=' ||\n        '.join(f'(bits=={p["bits"]} && ticks=={p["ticks"]} && pairs=={p["node_pairs"]})' for p in targets if p['bits']!=16)
  s=s.replace('return channels==1 && (','return channels==1 && ('+clauses+' ||\n        ',1);p.write_text(s)
 p=EXP/'relay/cpu_profile.h';s=p.read_text();clauses=''.join(f'(bits=={p["bits"]} && ticks=={p["ticks"]} && pairs=={p["node_pairs"]}) ||\n        ' for p in targets)
 if 14 not in selected:s=s.replace(' ||\n        (bits==14 && ticks==188 && pairs==1984)','')
 s=s.replace('(bits==10 && ticks==137',clauses+'(bits==10 && ticks==137');p.write_text(s)
 (EXP/'candidate_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
 return targets
if __name__=='__main__':print(json.dumps(prepare(),indent=2))
