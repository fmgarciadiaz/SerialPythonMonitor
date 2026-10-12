import unittest
from types import SimpleNamespace
from unittest.mock import create_autospec
import numpy as np
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.wav_source import seek_playback

class WavReceiverContractTests(unittest.TestCase):
    def test_seek_uses_real_receiver_interface(self):
        receiver=create_autospec(OutputReceiver,instance=True)
        receiver.wav_rate=20000
        receiver.wav_status=SimpleNamespace(played=1000)
        codes=np.zeros(300000,dtype=np.uint16)
        target=seek_playback(receiver,codes,0,10)
        self.assertEqual(target,201000)
        receiver.reset_wav_output.assert_called_once_with()
        self.assertEqual(receiver.wav_request.call_args.args[0],1)
        self.assertEqual(len(receiver.wav_request.call_args.args[1]),99000)
