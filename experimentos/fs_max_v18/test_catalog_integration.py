import json,unittest
from unittest.mock import patch
from experimentos.fs_max_v18.prepare_catalog import ROOT,OUT
from experimentos.fs_max_v18.probe_journal import source_manifest
from monitor.v18.receiver import unoq_native
from monitor.v18.receiver.unoq_acquisition import Configuration
class CatalogIntegrationTests(unittest.TestCase):
 def test_every_new_profile_roundtrips_without_ambiguity(self):
  ps=json.loads((OUT/'candidate_profiles.json').read_text());all_profiles=unoq_native.PROFILES+tuple(ps)
  self.assertEqual(len(all_profiles),len({(p['bits'],160000000//p['ticks']) for p in all_profiles}))
  with patch.object(unoq_native,'PROFILES',all_profiles):
   for p in ps:
    c=Configuration.from_wire(p['bits'],unoq_native.code(p));self.assertEqual((c.channels,c.period,c.node_pairs),(p['channels'],p['ticks'],p['node_pairs']))
 def test_integrated_policies_are_the_bridge_policies(self):
  for name in ('oscilloscope','relay'):
   actual=source_manifest(OUT/name);bridges=source_manifest(OUT.parent/'catalog_bridges'/name)
   self.assertEqual(set(actual),set(bridges))
   allowed='sketch/native_profiles.h' if name=='oscilloscope' else 'native_profiles.h'
   self.assertEqual({k for k in actual if actual[k]!=bridges[k]},{allowed})
 def test_native_table_is_identical_on_both_sides(self):
  self.assertEqual((OUT/'oscilloscope/sketch/native_profiles.h').read_bytes(),(OUT/'relay/native_profiles.h').read_bytes())
