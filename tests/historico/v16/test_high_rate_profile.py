import subprocess,tempfile,unittest
from pathlib import Path
from monitor.historico.v16.receiver.unoq_acquisition import Configuration,UART_RATES
from monitor.historico.v16.receiver.unoq_native import PROFILES
ROOT=Path(__file__).resolve().parents[3]
class HighRateProfileTests(unittest.TestCase):
 def test_profile_is_single_channel_adc8_only(self):
  c=Configuration(8,1403508)
  self.assertEqual((c.period,c.node_pairs,c.channels,c.timestamp_hz),(114,3456,1,160000000))
  self.assertEqual(c.request_period,(3456<<16)|114)
  self.assertEqual(c.dt_us,.7125)
  self.assertNotIn(c.rate,UART_RATES)
  for bits in (10,12,14,16):
   with self.assertRaises(ValueError):Configuration(bits,c.rate)
 def test_scoped_policy_matches_only_new_profile(self):
  mc=ROOT/'arduino/historico/v16/oscilloscope/sketch/high_rate_profile.h'
  self.assertEqual(mc.read_bytes(),(ROOT/'arduino/historico/v16/relay/high_rate_profile.h').read_bytes())
  calls=''.join(f'if(scope_high_rate({p["bits"]},{p["channels"]},{p["ticks"]},{p["node_pairs"]})!={int(p["bits"]==8 and p["channels"]==1 and p["ticks"]==114 and p["node_pairs"]==3456)})return 1;\n' for p in PROFILES)
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'policy.c';exe=src.with_suffix('');src.write_text(f'#include "{mc}"\nint main(void){{{calls}return 0;}}')
   subprocess.run(['cc','-std=c11',str(src),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
if __name__=='__main__':unittest.main()
