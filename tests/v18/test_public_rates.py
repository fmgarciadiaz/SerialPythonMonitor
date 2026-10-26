"""Public high-rate profiles require restored physical and combined evidence."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.radio_output import acquisition_error
ROOT=Path(__file__).resolve().parents[2]
class PublicRateTests(unittest.TestCase):
 def test_new_public_rates_have_sustained_and_combined_restored_evidence(self):
  for bits,rate,ticks in ((10,1311475,122),(12,1095890,146),(14,909090,176)):
   config=Configuration(bits,rate);p=config._native
   self.assertEqual((config.channels,config.period),(1,ticks))
   self.assertTrue(p['combined_qualified'])
   physical=json.loads((ROOT/p['evidence']).read_text())
   self.assertTrue(physical['ok']);self.assertTrue(physical['restoration']['hardware_restored'])
   cases=[row for row in physical['cases'] if row['bits']==bits]
   self.assertEqual([row['seconds'] for row in cases],[60,120,120,120])
   self.assertTrue(all(row['ok'] and row['headroom_ok'] for row in cases))
   gui=json.loads((ROOT/p['gui_evidence']).read_text())
   self.assertTrue(gui['ok']);self.assertTrue(gui['restoration']['hardware_restored'])
 def test_adc14_permission_is_specific_to_qualified_geometry(self):
  self.assertIsNone(acquisition_error(Configuration(14,909090)))
  for period,qualified in ((176,False),(180,True)):
   unknown=SimpleNamespace(bits=14,rate=160000000//period,channels=1,period=period,node_pairs=5952,_native={'combined_qualified':qualified})
   self.assertIsNotNone(acquisition_error(unknown))

 def test_new_permissions_require_exact_qualified_geometry(self):
  for bits,ticks,pairs in ((8,86,3488),(14,170,5952)):
   for qualified in (False,True):
    config=SimpleNamespace(bits=bits,channels=1,period=ticks,node_pairs=pairs,rate=160000000//ticks,_native={'combined_qualified':qualified})
    self.assertEqual(acquisition_error(config) is None,qualified)
   config.node_pairs-=1
   self.assertIsNotNone(acquisition_error(config))
