import json,unittest
from pathlib import Path
from monitor.v17.receiver.unoq_native import PROFILES
from monitor.v17.receiver.unoq_acquisition import Configuration
class AdditionalRatesTests(unittest.TestCase):
 def test_two_nearly_equal_intervals_before_first_high_rate(self):
  for bits in (8,10,12,14):
   high=min(160000000/p['ticks'] for p in PROFILES if p['bits']==bits and not p.get('purpose'))
   extra=sorted((160000000/p['ticks'] for p in PROFILES if p['bits']==bits and p.get('purpose')=='intermediate'))
   self.assertEqual(len(extra),2)
   gap=(high-40000)/3
   for i,rate in enumerate(extra,1):
    self.assertEqual(round(160000000/rate),round(160000000/(40000+gap*i)))
   for rate in extra:self.assertEqual(Configuration(bits,int(rate)).channels,2)
 def test_audio_nominal_rates_have_real_native_clock(self):
  audio=[p for p in PROFILES if p.get('purpose')=='audio']
  self.assertEqual({p['nominal_rate'] for p in audio},{44100,48000})
  for p in audio:
   c=Configuration(16,160000000//p['ticks'])
   self.assertEqual(c.timestamp_hz,160000000)
   self.assertLess(abs(c.actual_rate/p['nominal_rate']-1),.00011)
   self.assertEqual(Configuration.from_wire(16,c.request_period),c)
   for bits in (8,10,12,14):
    with self.assertRaises(ValueError):Configuration(bits,c.rate)
