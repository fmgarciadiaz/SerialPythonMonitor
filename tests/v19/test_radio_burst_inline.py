import unittest
from unittest.mock import patch, Mock
import numpy as np
from types import SimpleNamespace
from tools.radio_burst_inline_v19 import inline_burst, selected_descriptor
from monitor.v19.io.receiver_process import RemotePcmSource
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver


class InlineBurstTests(unittest.TestCase):
    def test_play_pair_sends_at_most_two_then_recovers_remaining_credit(self):
        now=[10.]
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',side_effect=lambda:now[0]), \
             inline_burst(1,8,True,play_burst=2):
            source=RemotePcmSource(dict(session=9,rate=40000,radio_audio=True,
                credit_window=30,minimum_blocks=30,maximum_blocks=30,target_blocks=30),lambda _:None)
            receiver=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
            receiver.wav_candidate=True;receiver.wav_codes=source;receiver.wav_session=9;receiver.wav_rate=40000
            receiver.wav_started=True;receiver.wav_chunk_tokens=8.;receiver.wav_chunk_token_at=now[0]
            receiver.wav_status=SimpleNamespace(session=9,free_blocks=3,accepted=0,queue_slots=30)
            for points,total in ((960,2),(480,3)):
                receiver.service_wav();start,end=source.pending
                self.assertEqual(end-start,points)
                source.accept(9,start,np.zeros(points,dtype=np.uint16))
                receiver.service_wav()
                self.assertEqual(receiver.connection.socket.sendall.call_count,total)
                receiver.service_wav()
                self.assertEqual(receiver.connection.socket.sendall.call_count,total)
                now[0]+=.0061
            self.assertEqual(receiver.wav_next_offset,1440)
            self.assertEqual((source.chunk_burst,source.chunk_interval,source.target_blocks),(2,.006,30))

    def test_explicit_play_arm_caps_tokens_without_changing_reserve_or_refill_rate(self):
        now=[10.]
        with patch('monitor.v19.receiver.unoq_config_receiver.time.monotonic',side_effect=lambda:now[0]), \
             inline_burst(1,8,True,play_burst=1):
            source=RemotePcmSource(dict(session=9,rate=40000,radio_audio=True,
                credit_window=30,minimum_blocks=30,maximum_blocks=30,target_blocks=30),lambda _:None)
            receiver=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
            receiver.wav_candidate=True;receiver.wav_codes=source;receiver.wav_session=9;receiver.wav_rate=40000
            receiver.wav_started=True;receiver.wav_chunk_tokens=8.;receiver.wav_chunk_token_at=now[0]
            receiver.wav_status=SimpleNamespace(session=9,free_blocks=3,accepted=0,queue_slots=30)
            for expected in (1,2,3):
                receiver.service_wav()
                self.assertIsNotNone(source.pending,(expected,receiver.wav_next_offset,receiver.wav_chunk_tokens,receiver.wav_pending,source.ready))
                start=source.pending[0]
                self.assertTrue(source.accept(9,start,np.zeros(480,dtype=np.uint16)))
                receiver.service_wav()
                self.assertEqual(receiver.connection.socket.sendall.call_count,expected)
                receiver.service_wav()
                self.assertEqual(receiver.connection.socket.sendall.call_count,expected)
                now[0]+=.0061
            self.assertEqual(receiver.wav_next_offset,1440)
            self.assertEqual((source.chunk_burst,source.chunk_interval,source.target_blocks),(1,.006,30))
            self.assertEqual((source.credit_window,source.minimum_blocks,source.maximum_blocks),(30,30,30))
        with self.assertRaises(ValueError),inline_burst(4,8,False,play_burst=1):pass

    def test_one_block_prefill_preserves_reserves_then_restores_play(self):
        descriptor=dict(session=1,rate=40000,radio_audio=True,chunk_burst=8,
                        chunk_interval=.006,credit_window=30,minimum_blocks=30,
                        maximum_blocks=30,target_blocks=30,poll_interval=.04)
        with patch.object(OutputReceiver,'service_wav',lambda _:None),inline_burst(1,8,True):
            source=RemotePcmSource(descriptor,lambda _:None)
            receiver=SimpleNamespace(wav_codes=source,wav_started=False,wav_rate=40000)
            OutputReceiver.service_wav(receiver)
            self.assertEqual((source.chunk_burst,source.chunk_interval),(1,.008))
            self.assertEqual((source.credit_window,source.minimum_blocks,source.maximum_blocks,
                              source.target_blocks,source.poll_interval),(30,30,30,30,.04))
            receiver.wav_started=True;OutputReceiver.service_wav(receiver)
            self.assertEqual((source.chunk_burst,source.chunk_interval),(8,.006))
        self.assertEqual(descriptor['chunk_burst'],8)
        with self.assertRaises(ValueError),inline_burst(1,8):pass

    def test_query_interval_is_scoped_and_startup_restore_does_not_erase_it(self):
        normal=dict(session=1,rate=40000,radio_audio=True,credit_window=30,target_blocks=30,poll_interval=.04)
        self.assertEqual(selected_descriptor(dict(normal,radio_audio=False),4,8,30)['poll_interval'],.04)
        self.assertEqual(selected_descriptor(dict(normal,rate=20000),4,8,30)['poll_interval'],.04)
        with patch.object(OutputReceiver,'service_wav',lambda _:None),inline_burst(4,8,True,30):
            source=RemotePcmSource(normal,lambda _:None)
            receiver=SimpleNamespace(wav_codes=source,wav_started=True,wav_rate=40000)
            OutputReceiver.service_wav(receiver)
            self.assertEqual((source.chunk_burst,source.chunk_interval,source.poll_interval),(8,.006,.03))
            self.assertEqual((source.credit_window,source.target_blocks),(30,30))
        self.assertEqual(normal['poll_interval'],.04)

    def test_interval_changes_only_radio40_preserves_credit_and_reserve_fields(self):
        for radio, rate in ((True,40000),(False,40000),(True,20000)):
            original=dict(radio_audio=radio,rate=rate,chunk_burst=8,
                          chunk_interval=.006,credit_window=30,target_blocks=30)
            result=selected_descriptor(original,8,8)
            expected=dict(original)
            if radio and rate==40000:expected['chunk_interval']=.008
            self.assertEqual(result,expected)
            self.assertEqual(original['chunk_interval'],.006)

    def test_startup_only_restores_accepted_playing_cadence_and_service_on_exception(self):
        observations=[]
        def service(receiver):
            observations.append((receiver.wav_codes.chunk_burst,receiver.wav_codes.chunk_interval))
        with patch.object(OutputReceiver,'service_wav',service):
            with self.assertRaisesRegex(RuntimeError,'screen'):
                with inline_burst(4,8,startup_only=True):
                    source=RemotePcmSource(dict(session=1,rate=40000,radio_audio=True),lambda _:None)
                    receiver=SimpleNamespace(wav_codes=source,wav_started=False,wav_rate=40000)
                    OutputReceiver.service_wav(receiver)
                    receiver.wav_started=True
                    OutputReceiver.service_wav(receiver)
                    self.assertEqual(observations,[(4,.008),(8,.006)])
                    raise RuntimeError('screen')
            self.assertIs(OutputReceiver.service_wav,service)

    def test_descriptor_scope_and_input_immutability(self):
        for radio, rate in ((True, 40000), (False, 40000), (True, 20000)):
            descriptor = dict(session=1, rate=rate, radio_audio=radio,
                              chunk_burst=8, credit_window=30, minimum_blocks=30,
                              maximum_blocks=30, chunk_interval=.006)
            result = selected_descriptor(descriptor, 4)
            self.assertEqual(descriptor['chunk_burst'], 8)
            expected = dict(descriptor)
            if radio and rate == 40000:
                expected['chunk_burst'] = 4
            self.assertEqual(result, expected)

    def test_constructor_only_and_exception_restoration(self):
        original = RemotePcmSource.__init__
        decoder = OutputReceiver._process_decoder_events
        with self.assertRaisesRegex(RuntimeError, 'screen'):
            with inline_burst(4):
                source = RemotePcmSource(dict(session=1, rate=40000,
                                             radio_audio=True, chunk_burst=8), lambda _: None)
                self.assertEqual(source.chunk_burst, 4)
                self.assertTrue(OutputReceiver._radio_chunk_ack_refresh)
                self.assertIs(OutputReceiver._process_decoder_events, decoder)
                raise RuntimeError('screen')
        self.assertIs(RemotePcmSource.__init__, original)

    def test_invalid_burst_never_patches_constructor(self):
        original = RemotePcmSource.__init__
        with self.assertRaises(ValueError), inline_burst(2):
            pass
        self.assertIs(RemotePcmSource.__init__, original)


if __name__ == '__main__':
    unittest.main()
