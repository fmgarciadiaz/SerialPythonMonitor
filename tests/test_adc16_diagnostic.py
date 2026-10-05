"""The ADC diagnostic must save the hardware profile, never the receiver default."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from diagnosticos.verificar_adc16_62k5 import wait_configuration
from monitor.v12.receiver.unoq_acquisition import Configuration


class ObservedConfigurationTests(TestCase):
    def test_waits_for_sample_status_and_ignores_initial_default(self):
        receiver = SimpleNamespace(config=Configuration(), decoder=SimpleNamespace(config=None, status=None))
        hardware = Configuration(16, 50000)
        def pump():
            receiver.decoder.config = hardware
            receiver.decoder.status = {'bits': 16, 'rate': 50000}
        receiver.pump = pump
        self.assertEqual(wait_configuration(receiver), hardware)
        self.assertNotEqual(receiver.config, hardware)

    def test_restoration_waits_until_samples_match_requested_profile(self):
        wanted = Configuration(14, 125000)
        receiver = SimpleNamespace(decoder=SimpleNamespace(config=wanted, status={'bits': 16, 'rate': 62500}))
        calls = []
        def pump():
            calls.append(True)
            if len(calls) == 2:
                receiver.decoder.status = {'bits': 14, 'rate': 125000}
        receiver.pump = pump
        self.assertEqual(wait_configuration(receiver, wanted), wanted)
        self.assertEqual(len(calls), 2)

    def test_missing_real_status_times_out(self):
        receiver = SimpleNamespace(decoder=SimpleNamespace(config=None, status=None), pump=lambda: None)
        with patch('diagnosticos.verificar_adc16_62k5.time.monotonic', side_effect=[0, 0, 6]):
            with self.assertRaises(TimeoutError):
                wait_configuration(receiver)
