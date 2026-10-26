import unittest
import hashlib,json
from experimentos.fs_max_v18.prepare_rateonly import ROOT,OUT,PROFILES
from monitor.v18.q_support.board import source_files
from pathlib import Path

class RateOnlyTests(unittest.TestCase):
 def test_only_explicit_profile_headers_differ(self):
  for base,copy in ((ROOT/'arduino/v18/oscilloscope',OUT/'oscilloscope'),(ROOT/'arduino/v18/relay',OUT/'relay')):
   recorded=json.loads((OUT/'source_manifest.json').read_text())
   original={Path(key[len(base.name)+1:]):value for key,value in recorded.items() if key.startswith(base.name+'/')}
   candidate={p.relative_to(copy):p.read_bytes() for p in source_files(copy)}
   self.assertEqual(set(original),set(candidate))
   changed={str(p) for p in original if original[p]!=hashlib.sha256(candidate[p]).hexdigest()}
   prefix='sketch/' if base.name=='oscilloscope' else ''
   expected={prefix+'native_profiles.h',prefix+'high_rate_profile.h'} | ({'cpu_profile.h'} if base.name=='relay' else set())
   self.assertEqual(changed,expected)
   old=original[next(p for p in original if str(p)==prefix+'high_rate_profile.h')]
   new=candidate[next(p for p in candidate if str(p)==prefix+'high_rate_profile.h')].decode()
   guard=' || '.join(f'(bits=={v["bits"]} && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES)
   guard8=' || '.join(f'ticks=={v["ticks"]}' for v in PROFILES if v['bits']==8)
   new=new.replace('return channels==1 && ('+guard+' || ','return channels==1 && (',1)
   new=new.replace(f'    return (bits==8 && channels==1 && pairs==3488 && ({guard8})) || (bits==8 && channels==1','    return (bits==8 && channels==1',1)
   self.assertEqual(hashlib.sha256(new.encode()).hexdigest(),old)
 def test_cpu_policy_extended_only_for_new_profiles(self):
  old=json.loads((OUT/'source_manifest.json').read_text())['relay/cpu_profile.h']
  new=(OUT/'relay/cpu_profile.h').read_text()
  guard=' || '.join(f'(bits=={v["bits"]} && channels==1 && ticks=={v["ticks"]} && pairs=={v["node_pairs"]})' for v in PROFILES if v['bits']!=8)
  self.assertEqual(hashlib.sha256(new.replace('    return '+guard+' || ','    return ',1).encode()).hexdigest(),old)
 def test_existing_geometry_preserved(self):
  import json
  public=json.loads((ROOT/'monitor/v18/receiver/native_profiles.json').read_text())
  for b in (8,10,12,14):
   latest=next(p for p in public if p['bits']==b and p.get('channels',1)==1 and p['ticks']=={8:88,10:122,12:146,14:176}[b])
   for p in (p for p in PROFILES if p['bits']==b):
    self.assertEqual(p['node_pairs'],latest['node_pairs'])
    self.assertEqual(p['queue_slots'],latest['queue_slots'])
    self.assertLess(p['ticks'],latest['ticks'])
 def test_private_gui_retains_profile_geometry_and_ipc(self):
  from tools.gui_experimental_v18 import selected_profile
  for b,t in ((8,84),(10,116),(12,144),(14,170)):
   profile=selected_profile('rateonly',f'{b}:{t}')
   expected=next(p for p in PROFILES if p['bits']==b and p['ticks']==t)
   for field in ('bits','ticks','node_pairs','queue_slots'):
    self.assertEqual(profile[field],expected[field])
   self.assertEqual(profile.get('compact_adc8_ipc',False),b==8)
   self.assertFalse(profile['internal_only'])
