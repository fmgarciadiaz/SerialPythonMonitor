import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver


class FrameServiceScopeTests(unittest.TestCase):
    def test_only_qualified_radio_profile_services_between_adc_frames(self):
        for bits,rate,radio in ((10,1250000,True),(10,909090,True),(8,1600000,True),(12,1066666,True),(14,851063,True),(10,1250000,False)):
            with self.subTest(bits=bits,rate=rate,radio=radio):
                r=OutputReceiver(SimpleNamespace(socket=Mock()),lambda _:None)
                r.config=SimpleNamespace(bits=bits,rate=rate)
                r.wav_codes=SimpleNamespace(radio_audio=radio)
                r.decoder=SimpleNamespace(events=[]);r.service_wav=Mock()
                r._process_decoder_events()
                self.assertEqual(r.service_wav.call_count,int(bits==10 and rate==1250000 and radio))
