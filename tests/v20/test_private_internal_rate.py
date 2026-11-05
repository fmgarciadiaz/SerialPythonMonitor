import unittest
from types import SimpleNamespace as NS
from tools.gui_private_v20 import enable_internal_2m,enable_internal_audio_2m


class PrivateInternalRateTests(unittest.TestCase):
    def test_only_private_2m_is_added_and_restoration_is_exact(self):
        rates=(40000,1860465);supported=lambda b,r:r in rates
        catalog=lambda b:{40000}
        module=NS(RATES=rates,_configuration_supported=supported,catalog_rates=catalog)
        undo=enable_internal_2m(module,8,2000000)
        self.assertTrue(module._configuration_supported(8,2000000))
        self.assertFalse(module._configuration_supported(10,2000000))
        self.assertIn(2000000,module.RATES);self.assertIn(2000000,module.catalog_rates(8))
        self.assertNotIn(2000000,module.catalog_rates(10))
        undo()
        self.assertIs(module.RATES,rates);self.assertIs(module._configuration_supported,supported)
        self.assertIs(module.catalog_rates,catalog)

    def test_other_internal_profiles_cannot_be_enabled(self):
        for bits,rate in ((8,2051282),(10,2000000),(8,1860465)):
            with self.assertRaises(ValueError):enable_internal_2m(NS(),bits,rate)

    def test_audio_trial_only_relaxes_exact_tuple_and_restores_both_guards(self):
        from monitor.v20 import radio_output,radio_output_panel
        from monitor.v20.receiver.unoq_acquisition import Configuration
        before=(radio_output.acquisition_error,radio_output_panel.acquisition_error)
        candidate=Configuration(8,2000000)
        self.assertIsNone(before[0](candidate))  # Now exposed as an exact experimental V20 option.
        undo=enable_internal_audio_2m()
        try:
            for module in (radio_output,radio_output_panel):
                self.assertIsNone(module.acquisition_error(candidate))
                other=Configuration(8,2051282)
                self.assertEqual(module.acquisition_error(other),before[0](other))
        finally:undo()
        self.assertIs(radio_output.acquisition_error,before[0])
        self.assertIs(radio_output_panel.acquisition_error,before[1])
