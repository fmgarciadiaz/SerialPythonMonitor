"""Qualified additions keep existing profiles and Scan US auxiliaries unchanged."""
import json
from pathlib import Path
import unittest
from monitor.v18.radio_multiscan import scan_profiles
from monitor.v18.radio_output import acquisition_error
from monitor.v18.io.rf_batch import should_compact_adc8_ipc
from monitor.v18.receiver.unoq_acquisition import Configuration
ROOT=Path(__file__).resolve().parents[2]

class RateOnlyReleaseTests(unittest.TestCase):
 def test_existing_and_new_targets_use_the_same_auxiliaries(self):
  for bits,old_rate,new_rate,old_ticks,new_ticks,pairs,aux in (
    (8,1818181,1860465,88,86,3488,[(100,3456),(114,3456)]),
    (10,1311475,1333333,122,120,5568,[(128,5568),(140,2784)]),
    (14,909090,941176,176,170,5952,[(188,5952),(192,1984)])):
   for rate,ticks in ((old_rate,old_ticks),(new_rate,new_ticks)):
    with self.subTest(bits=bits,rate=rate):
     config=Configuration(bits,rate)
     self.assertEqual([(c.period,c.node_pairs) for c in scan_profiles(config)],[(ticks,pairs),*aux])
     self.assertIsNone(acquisition_error(config))
   if bits==8:self.assertTrue(should_compact_adc8_ipc(Configuration(bits,new_rate)))
 def test_new_profiles_have_exact_sustained_and_gui_evidence(self):
  for bits,rate in ((8,1860465),(10,1333333),(14,941176)):
   config=Configuration(bits,rate);p=config._native
   physical=json.loads((ROOT/p['evidence']).read_text())
   self.assertTrue(physical['ok']);self.assertTrue(physical['restoration']['hardware_restored'])
   cases=[c for c in physical['cases'] if (c['bits'],c['ticks'])==(bits,config.period)]
   self.assertEqual([c['seconds'] for c in cases],[60,120,120,120])
   self.assertTrue(all(c['ok'] and c['headroom_ok'] and c['status']['dropped']==c['status']['fatal']==0 for c in cases))
   gui=json.loads((ROOT/p['gui_evidence']).read_text())
   self.assertTrue(gui['ok']);self.assertTrue(gui['hardware_restored']);self.assertTrue(gui['visible_gui_ok'])
   self.assertTrue(p['combined_qualified']);self.assertTrue(p['isolated_headroom'])
