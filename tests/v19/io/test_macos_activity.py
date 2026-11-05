"""Real scoped activity lifecycle; no Q and no persistent preference changes."""
import sys,unittest
from tools.macos_activity_v18 import MacActivity
class MacActivityTests(unittest.TestCase):
 def test_context_releases_token_and_close_is_idempotent(self):
  with MacActivity('user') as activity:
   self.assertEqual(activity.active,sys.platform=='darwin')
  self.assertFalse(activity.active)
  activity.close()
  self.assertFalse(activity.active)
 def test_unknown_mode_rejected(self):
  with self.assertRaises(ValueError):MacActivity('global-disable')
if __name__=='__main__':unittest.main()
