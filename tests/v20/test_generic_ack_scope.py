import json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from monitor.v20.receiver.unoq_acquisition import Configuration
from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
from tools.relay_wire_metrics_v19 import set_metrics_profile,observe_connection,PROFILE_ENV

class GenericAckScopeTests(unittest.TestCase):
    def test_generic_profile_requires_explicit_opt_in(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):set_metrics_profile(8,40000,configuration=Configuration)
            result=set_metrics_profile(8,40000,configuration=Configuration,allow_non_native=True)
            self.assertEqual(result[1],40000)
            self.assertEqual(json.loads(os.environ[PROFILE_ENV]),[8,40000])

    def test_generic_capture_cannot_claim_native_performance(self):
        with patch.dict(os.environ,{},clear=True),tempfile.TemporaryDirectory() as temp:
            set_metrics_profile(8,40000,configuration=Configuration,allow_non_native=True)
            original=lambda:b'';connection=SimpleNamespace(read=original,socket=None)
            path=Path(temp)/'metrics.json'
            with observe_connection(connection,path,receiver_class=OutputReceiver,configuration=Configuration,allow_non_native=True):
                self.assertEqual(connection.read(),b'')
            self.assertIs(connection.read,original)
            result=json.loads(path.read_text())
            self.assertFalse(result['native_counters_expected'])
            self.assertFalse(result['performance_acceptance_eligible'])
            self.assertEqual(result['profile'][1],40000)
