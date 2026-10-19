import unittest
from unittest.mock import Mock,patch
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration

class TransitionTests(unittest.TestCase):
    def test_high_profile_switch_stages_without_publishing_intermediate(self):
        r=OutputReceiver(Mock(),Mock());r.mode=0;r.config=Configuration(10,1167883)
        target=Configuration(10,909090);seen=[];callback=Mock();r.on_configuration=callback
        def apply(config):
            seen.append(config);r.config=config;r.on_configuration(config);return True
        r._configure_once=apply;r.pump=Mock()
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',side_effect=[0,1]):r.configure(target)
        self.assertEqual(seen,[Configuration(14,40000),target])
        callback.assert_called_once_with(target)
    def test_same_profile_does_not_reconfigure(self):
        r=OutputReceiver(Mock(),Mock());r.mode=0;r.config=Configuration(10,1250000);r._configure_once=Mock()
        self.assertFalse(r.configure(r.config));r._configure_once.assert_not_called()

    def test_optimized_to_legacy_single_channel_also_stages(self):
        for origin,target in ((Configuration(14,833333),Configuration(14,599250)),
                              (Configuration(14,599250),Configuration(14,851063))):
            r=OutputReceiver(Mock(),Mock());r.mode=0;r.config=origin
            seen=[];callback=Mock();r.on_configuration=callback
            def apply(config):
                seen.append(config);r.config=config;r.on_configuration(config);return True
            r._configure_once=apply;r.pump=Mock()
            with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',side_effect=[0,1]):r.configure(target)
            self.assertEqual(seen,[Configuration(14,40000),target])
            callback.assert_called_once_with(target)
