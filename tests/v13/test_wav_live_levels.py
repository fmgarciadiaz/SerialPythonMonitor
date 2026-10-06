import unittest
import numpy as np
from monitor.v13.receiver.unoq_config_receiver import OutputReceiver

class LiveWavLevelsTests(unittest.TestCase):
    def test_level_update_preserves_source_and_zero_can_be_raised(self):
        receiver = OutputReceiver(None, lambda batch: None)
        receiver.wav_codes = np.array([0, 4095] * 240, dtype='<u2')
        receiver.wav_codes.setflags(write=False)
        original = receiver.wav_codes.copy()
        receiver.set_wav_levels(0, 1.65)
        self.assertTrue(np.all(np.abs(receiver._wav_chunk_codes(0,480).astype(int)-2048)<=1))
        receiver.set_wav_levels(2, 1.65)
        ramp = receiver._wav_chunk_codes(0,480)
        self.assertLess(abs(int(ramp[0])-2048), 2)
        self.assertGreater(int(ramp[-1]), 3200)
        full = receiver._wav_chunk_codes(0,480)
        self.assertAlmostEqual(int(full.max())-int(full.min()), 2*4095/3.3, delta=2)
        np.testing.assert_array_equal(original,receiver.wav_codes)
        self.assertTrue(np.all(full<=4095))

    def test_levels_reject_out_of_range_offset(self):
        receiver = OutputReceiver(None, lambda batch: None)
        with self.assertRaises(ValueError):receiver.set_wav_levels(3, .2)

    def test_reconnection_stops_failed_session_before_reusing_dac(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from monitor.v13.receiver import unoq_wav as wav
        receiver = OutputReceiver(None, lambda batch: None)
        requests = []
        def request(op=0):
            requests.append(op)
            receiver.wav_pending = True
        def pump():
            receiver.wav_pending = None
            receiver.wav_status = SimpleNamespace(state=wav.State.UNDERRUN if requests[-1]==0 else wav.State.IDLE, session=123, reason=0)
        receiver.wav_request = request
        receiver.pump = pump
        receiver.reset_wav_output()
        self.assertEqual(requests, [0,3])
        self.assertEqual(receiver.wav_session,123)
        self.assertEqual(receiver.wav_status.state,wav.State.IDLE)

    def test_disconnect_stops_wav_before_disabling_generator(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from monitor.v13.receiver.unoq_switch import Phase
        receiver = OutputReceiver(None, lambda batch: None, running=lambda: False)
        receiver.wav_candidate = True
        history = []
        receiver.reset_wav_output = lambda: history.append('stop wav')
        def generator(config):
            history.append('disable generator')
            self.assertEqual((config.enabled,config.low,config.high),(0,0,0))
            self.assertTrue(receiver.running())
            return SimpleNamespace(phase=Phase.APPLIED, active=config)
        receiver.generator = generator
        receiver.shutdown_output()
        self.assertEqual(history,['stop wav','disable generator'])
        self.assertFalse(receiver.running())
