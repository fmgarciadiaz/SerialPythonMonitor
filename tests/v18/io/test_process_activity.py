import unittest
from unittest.mock import patch
from monitor.v18.process_activity import acquisition_activity_mode


class ProcessActivityTests(unittest.TestCase):
    def test_defaults_and_explicit_overrides_are_scoped_by_process(self):
        with patch.dict('os.environ',{},clear=True):
            with patch('monitor.v18.process_activity.sys.platform','darwin'):
                self.assertEqual(acquisition_activity_mode('parent'),'user')
                self.assertEqual(acquisition_activity_mode('receiver'),'user')
            with patch('monitor.v18.process_activity.sys.platform','linux'):
                self.assertEqual(acquisition_activity_mode('parent'),'off')
        with patch.dict('os.environ',{'MONITOR_V18_PARENT_ACTIVITY':'off','MONITOR_V18_RECEIVER_ACTIVITY':'user'}):
            self.assertEqual(acquisition_activity_mode('parent'),'off')
            self.assertEqual(acquisition_activity_mode('receiver'),'user')
        with self.assertRaises(ValueError):acquisition_activity_mode('other')
