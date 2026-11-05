import unittest
import json,os,tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock,patch
from monitor.v20.receiver import unoq_native as native
from monitor.v20.receiver.unoq_acquisition import Configuration
from tools.probe_working_v20_rates import diagnostic_profiles


class PrivateRateProfileTests(unittest.TestCase):
    def test_receiver_connection_keeps_private_profile_until_cleanup(self):
        from tools import private_v20_pair as pair
        original=native.PROFILES
        with tempfile.TemporaryDirectory() as temp:
            binding=Path(temp)/'report.json'
            binding.write_text(json.dumps(dict(private_profile=dict(bits=12,rate=1142857))))
            connection=Mock()
            @contextmanager
            def installed(*args,**kwargs):
                config=Configuration(12,1142857)
                self.assertEqual(config,Configuration.from_wire(12,config.request_period))
                yield connection
            @contextmanager
            def observed(*args,**kwargs):
                self.assertEqual(Configuration(12,1142857).period,140)
                yield
            with patch.dict(os.environ,{pair.ENV:str(binding)},clear=True),patch.object(pair,'installed_connection',installed),patch('tools.relay_wire_metrics_v19.observe_connection',observed):
                with pair.connection('fake-board') as actual:
                    self.assertIs(actual,connection)
                    self.assertIsNotNone(native.profile(12,1142857))
            self.assertIs(native.PROFILES,original)

    def test_candidates_roundtrip_and_restore_without_catalog_changes(self):
        original=native.PROFILES
        for bits,rates in ((10,(1379310,)),(12,(1111111,1126760,1142857))):
            with diagnostic_profiles(bits,rates):
                for rate in rates:
                    config=Configuration(bits,rate)
                    self.assertTrue(config._native['internal_only'])
                    self.assertEqual(config._native['queue_slots'],4)
                    self.assertEqual(Configuration.from_wire(bits,config.request_period),config)
            self.assertIs(native.PROFILES,original)

    def test_unknown_candidate_restores_on_rejection(self):
        original=native.PROFILES
        with self.assertRaises(ValueError):
            with diagnostic_profiles(14,(1012658,)):
                self.fail('Unsupported profile enabled')
        self.assertIs(native.PROFILES,original)

    def test_exception_restores_original_profiles(self):
        original=native.PROFILES
        with self.assertRaises(RuntimeError):
            with diagnostic_profiles(10,(1379310,)):
                raise RuntimeError('diagnostic failed')
        self.assertIs(native.PROFILES,original)
