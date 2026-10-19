"""Prevent the physical timestamp-DMA/SPI frame corruption found with N8064."""
import json,re,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
class ScratchBoundTests(unittest.TestCase):
 def test_every_private_pipelined_node_leaves_both_frame_buffers(self):
  sketch=HERE/'oscilloscope/sketch'
  source=(sketch/'sketch.ino').read_text()
  slots=int(re.search(r'FRAME_SLOTS=(\d+)',source).group(1))
  maximum=int(re.search(r'#define SCOPE_NATIVE_MAX_SINGLE (\d+)U',(sketch/'native_profiles.h').read_text()).group(1))
  arena=maximum*2*4;scratch=(slots-1)*992
  profiles=json.loads((HERE/'candidate_profiles.json').read_text())
  for profile in profiles:
   if profile['bits']==16:continue
   with self.subTest(bits=profile['bits'],node=profile['node_pairs']):
    self.assertLessEqual(profile['node_pairs']*2*4+scratch,arena)
  self.assertGreater(8064*2*4+scratch,arena)
  p=next(v for v in profiles if v['bits']==12)
  self.assertEqual(p['node_pairs']%576,0)
if __name__=='__main__':unittest.main()
