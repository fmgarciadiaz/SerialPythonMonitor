import json,re,unittest
from unittest.mock import patch
from experimentos.fs_max_v18.prepare_audio_catalog import ROOT,OUT
from experimentos.fs_max_v18.probe_journal import source_manifest
from monitor.v18.receiver import unoq_native
from monitor.v18.receiver.unoq_acquisition import Configuration
class AudioCatalogTests(unittest.TestCase):
 def test_only_native_whitelists_change(self):
  before=json.loads((OUT/'source_manifest.json').read_text())
  for name,header in (('oscilloscope','sketch/native_profiles.h'),('relay','native_profiles.h')):
   expected={k[len(name)+1:]:v for k,v in before.items() if k.startswith(name+'/')};actual=source_manifest(OUT/name)
   self.assertEqual(set(expected),set(actual));self.assertEqual({k for k in actual if actual[k]!=expected[k]},{header})
 def test_no_ambiguous_identity_and_exact_wire_roundtrip(self):
  candidates=json.loads((OUT/'candidate_profiles.json').read_text());all_profiles=unoq_native.PROFILES+tuple(candidates)
  keys=[(p['bits'],160000000//p['ticks']) for p in all_profiles]
  self.assertEqual(len(keys),len(set(keys)))
  with patch.object(unoq_native,'PROFILES',all_profiles):
   for p in candidates:
    c=Configuration.from_wire(p['bits'],unoq_native.code(p))
    self.assertEqual((c.channels,c.period,c.node_pairs),(p['channels'],p['ticks'],p['node_pairs']))
    self.assertLess(abs(c.actual_rate/p['nominal_rate']-1),.0005)
    self.assertEqual(c.sampling_cycles,5)
 def test_hardware_limits_and_common_audio_anchors(self):
  ps=json.loads((OUT/'candidate_profiles.json').read_text())
  self.assertEqual(len(ps),17)
  for b in (8,10,12,14):self.assertEqual({p['nominal_rate'] for p in ps if p['bits']==b},{44100,48000,96000,192000})
  self.assertEqual([(p['nominal_rate'],p['channels']) for p in ps if p['bits']==16],[(96000,1)])
 def test_native_headers_match(self):
  self.assertEqual((OUT/'oscilloscope/sketch/native_profiles.h').read_bytes(),(OUT/'relay/native_profiles.h').read_bytes())
