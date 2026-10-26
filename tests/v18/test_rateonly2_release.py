"""Second rate additions retain the qualified geometry and old Scan auxiliaries."""
import json,unittest
from pathlib import Path
from types import SimpleNamespace
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.radio_multiscan import scan_profiles
from monitor.v18.radio_output import acquisition_error
from monitor.v18.io.rf_batch import should_compact_adc8_ipc
ROOT=Path(__file__).resolve().parents[2]
class RateOnly2ReleaseTests(unittest.TestCase):
 def test_new_targets_inherit_existing_auxiliaries(self):
  for bits,rate,ticks,pairs,aux in ((10,1355932,118,5568,[(128,5568),(140,2784)]),(12,1103448,145,7488,[(150,7488),(172,4608)]),(14,1000000,160,5952,[(188,5952),(192,1984)])):
   with self.subTest(bits=bits):
    config=Configuration(bits,rate)
    self.assertEqual([(c.period,c.node_pairs) for c in scan_profiles(config)],[(ticks,pairs),*aux])
    self.assertIsNone(acquisition_error(config))
    self.assertEqual(config._native['queue_slots'],8 if bits==8 else 4)
    self.assertEqual(should_compact_adc8_ipc(config),bits==8)
 def test_one_megahertz_is_not_a_new_legacy_rate_for_other_bits(self):
  self.assertEqual(Configuration(14,1000000).period,160)
  for bits in (8,10,12,16):
   with self.assertRaises(ValueError):Configuration(bits,1000000)
 def test_public_evidence_is_exact_and_restored(self):
  for bits,rate in ((10,1355932),(12,1103448),(14,1000000)):
   config=Configuration(bits,rate);p=config._native
   physical=json.loads((ROOT/p['evidence']).read_text())
   self.assertTrue(physical['ok']);self.assertTrue(physical['restoration']['hardware_restored'])
   cases=[c for c in physical['cases'] if (c['bits'],c['ticks'])==(bits,config.period)]
   self.assertEqual([c['seconds'] for c in cases],[60,120,120,120])
   self.assertTrue(all(c['ok'] and c['headroom_ok'] for c in cases))
   gui=json.loads((ROOT/p['gui_evidence']).read_text())
   self.assertTrue(gui['ok']);self.assertTrue(gui['visible_gui_ok']);self.assertTrue(gui['hardware_restored'])
   self.assertTrue(p['combined_qualified'])
 def test_new_radio_permissions_are_bound_to_exact_geometry(self):
  for bits,ticks,pairs in ((14,160,5952),):
   values=dict(bits=bits,channels=1,period=ticks,node_pairs=pairs,rate=160000000//ticks,_native={'combined_qualified':True})
   self.assertIsNone(acquisition_error(SimpleNamespace(**values)))
   for change in ({'node_pairs':pairs-1},{'channels':2},{'_native':{}}):
    self.assertIsNotNone(acquisition_error(SimpleNamespace(**dict(values,**change))))

 def test_failed_installed_adc8_target_is_not_exposed(self):
  with self.assertRaises(ValueError):Configuration(8,1882352)
  with self.assertRaises(ValueError):Configuration.from_wire(8,(3488<<16)|85)
  self.assertTrue(should_compact_adc8_ipc(Configuration(8,1860465)))
  bad=SimpleNamespace(bits=8,channels=1,period=85,node_pairs=3488,rate=1882352,_native={'combined_qualified':True})
  self.assertIsNotNone(acquisition_error(bad))
