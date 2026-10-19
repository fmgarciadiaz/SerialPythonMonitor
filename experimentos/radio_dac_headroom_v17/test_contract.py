"""Run ownership/guard tests against current V17 baseline and isolated candidate."""
import unittest,subprocess
from pathlib import Path
from tests.v13.test_wav_firmware import WavFirmwareTests,STUB
ROOT=Path(__file__).resolve().parents[2]
class BaselineWavTests(WavFirmwareTests):
 optimization='-O2'
 sketch=ROOT/'experimentos/radio_dac_headroom_v17/baseline_sketch'
 def run_cpp(self,code):
  source=self.folder/'wav.cpp';exe=self.folder/'wav'
  source.write_text('#include "generator_protocol.h"\n'+STUB+code)
  subprocess.run(['c++',self.optimization,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(self.sketch),str(source),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
def suite():
 result=unittest.TestSuite()
 from experimentos.radio_dac_headroom_v17.test_ring import RingTests
 for cls in (BaselineWavTests,RingTests):result.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
 return result
if __name__=='__main__':raise SystemExit(not unittest.TextTestRunner().run(suite()).wasSuccessful())
