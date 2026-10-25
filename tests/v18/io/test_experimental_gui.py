"""No Q: exact private profile survives a real spawn without publishing files."""
import json,os,subprocess,sys,unittest
from pathlib import Path
from tools.gui_experimental_v18 import selected_profile
ROOT=Path(__file__).resolve().parents[3]
class ExperimentalGuiTests(unittest.TestCase):
 def test_unknown_or_mismatched_profile_rejected(self):
  with self.assertRaises(ValueError):selected_profile('../outside','10:122')
  with self.assertRaises(ValueError):selected_profile('spi40_10_12','8:1')
 def test_spawn_preserves_profile_and_factory_without_q(self):
  env=dict(os.environ,SCOPE_V18_GUI_RECIPE='spi40_10_12',SCOPE_V18_GUI_TARGET='10:122')
  result=subprocess.run([sys.executable,str(ROOT/'tools/gui_experimental_v18.py'),'--check-bootstrap'],
                        env=env,capture_output=True,text=True,timeout=30,check=True)
  self.assertEqual(json.loads(result.stdout),dict(bits=10,ticks=122,node_pairs=5568,factory='experimental_connection'))
if __name__=='__main__':unittest.main()
