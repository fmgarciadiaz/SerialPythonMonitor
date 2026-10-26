"""Private ADC16 staircase keeps conversion/packing and production untouched."""
import json,unittest
from pathlib import Path
from unittest.mock import patch
from monitor.v18.receiver import unoq_native
from monitor.v18.receiver.unoq_acquisition import Configuration
from experimentos.fs_max_v18.prepare_adc16 import OUT,ROOT,PROFILES
class Adc16Tests(unittest.TestCase):
 def test_same_clock_oversampling_packers_and_adc_storage(self):
  for name in ('acquisition.h','sample_packing.h','acquisition_storage.h','sketch.ino'):
   self.assertEqual((ROOT/'arduino/v18/oscilloscope/sketch'/name).read_bytes(),(OUT/'oscilloscope/sketch'/name).read_bytes())
 def test_both_channel_counts_roundtrip_exact_wire_geometry(self):
  with patch.object(unoq_native,'PROFILES',unoq_native.PROFILES+tuple(PROFILES)):
   for profile in PROFILES:
    config=Configuration.from_wire(16,unoq_native.code(profile))
    self.assertEqual((config.bits,config.channels,config.period,config.node_pairs),(16,profile['channels'],profile['ticks'],profile['node_pairs']))
    self.assertEqual(config.maximum,65535)
    self.assertEqual(config.sampling_cycles,5)
 def test_source_changes_are_only_explicit_profile_whitelists(self):
  # This historical experiment is checked against its recorded baseline,
  # not against later, intentionally extended production profile tables.
  from experimentos.fs_max_v18.probe_journal import source_manifest
  baseline=json.loads((OUT/'source_manifest.json').read_text())
  for name in ('oscilloscope','relay'):
   expected={key[len(name)+1:]:value for key,value in baseline.items() if key.startswith(name+'/')}
   actual=source_manifest(OUT/name)
   self.assertEqual(set(actual),set(expected))
   changed={key for key in actual if actual[key]!=expected[key]}
   self.assertTrue(changed<=({'sketch/native_profiles.h'} if name=='oscilloscope' else {'native_profiles.h'}))
