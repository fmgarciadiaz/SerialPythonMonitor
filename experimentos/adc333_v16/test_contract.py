"""Run from repository root: python -m unittest experimentos.adc333_v16.test_contract."""
from pathlib import Path
import importlib.util,sys,struct,zlib,unittest,tempfile,subprocess
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
from monitor.v16.receiver.unoq_acquisition import Configuration as Stable
name='adc333_contract_test'
spec=importlib.util.spec_from_file_location(name,EXP/'acquisition.py');acq=importlib.util.module_from_spec(spec);sys.modules[name]=acq;spec.loader.exec_module(acq)
from tests.v16.test_compact_protocol import packet,seal
class ContractTests(unittest.TestCase):
 def test_stable_stays_unchanged(self):
  with self.assertRaises(ValueError):Stable(14,333333)
  for filename in ('acquisition.h','node_validation.h'):
   self.assertEqual((EXP/'arduino/v16/oscilloscope/sketch'/filename).read_bytes(),(ROOT/'arduino/v16/oscilloscope/sketch'/filename).read_bytes())
 def test_period_and_bit_contract(self):
  self.assertEqual(acq.Configuration(14,333333).period,3)
  self.assertEqual(acq.Configuration(14,333333).sampling_us,.72)
  with self.assertRaises(ValueError):acq.Configuration(16,333333)
  for period in (0,3,4,5,7,9):
   p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,7,0,972)
   struct.pack_into('<IBBBBIII',p,16,0x80000001,14,14,2,0,period,period,1);p=seal(p)
   if period in (3,4,5):self.assertEqual(acq.acquisition_reply(p).active.period,period)
   else:
    with self.assertRaises(ValueError):acq.acquisition_reply(p)
 def test_c_relay_accepts_new_command_and_samples(self):
  header=EXP/'arduino/v16/relay/config_relay_protocol.h';base=header.with_name('base_verifier.c')
  source=f'''#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(void){{ uint8_t p[BLOCK];init_crc();while(fread(p,1,BLOCK,stdin)==BLOCK){{DualChecker d={{.period=3,.bits=14}};printf("%d\\n",get16(p+6)==6?dual_command(p):dual_feed(&d,p));}}}}'''
  p=bytearray(packet(t0=100));struct.pack_into('<I',p,48,333333);struct.pack_into('<I',p,68,3)
  invalid=bytearray(p);struct.pack_into('<H',invalid,84+113*4,16384)
  request=acq.acquisition_request(0x80000001,acq.Configuration(14,333333))
  bad=bytearray(p);struct.pack_into('<I',bad,68,7)
  with tempfile.TemporaryDirectory() as directory:
   src=Path(directory)/'test.c';exe=src.with_suffix('');src.write_text(source)
   subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror',str(src),'-lm','-o',str(exe)],check=True,capture_output=True)
   output=subprocess.run([str(exe)],input=request+seal(p)+seal(invalid)+seal(bad),capture_output=True,check=True).stdout
   self.assertEqual(output,b'1\n1\n0\n0\n')
if __name__=='__main__':unittest.main()
