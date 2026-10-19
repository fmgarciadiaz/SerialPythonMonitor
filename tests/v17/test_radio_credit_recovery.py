"""Delayed ACK recovery must retain conservative DAC credit accounting."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver


class RadioCreditRecoveryTests(unittest.TestCase):
    def receiver(self, slots=30):
        r=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
        s=RadioDacSource(1,buffer_seconds=0)
        s.feed_result(dict(audio=np.zeros(20000),radio_key=(1250000,20000,40000),
                           settings=ProcessingSettings(radio_offset=0)))
        r.wav_codes=s;r.wav_session=123;r.wav_started=True;r.wav_candidate=True
        r.wav_status=SimpleNamespace(session=123,free_blocks=slots,accepted=0,queue_slots=slots)
        r.wav_chunk_tokens=0;r.wav_chunk_token_at=100
        return r,s

    def test_delayed_acks_allow_recovery_burst_but_never_overbook(self):
        r,s=self.receiver()
        # Four delayed pump turns, no ACK: 96 ms allows eight chunks each turn.
        for instant,expected in ((100.096,8),(100.192,16),(100.288,24),(100.384,30)):
            with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=instant):
                r.service_wav()
            self.assertEqual(len(r.wav_inflight),expected)
            self.assertEqual(r.wav_next_offset,expected*480)
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.480):
            r.service_wav()
        self.assertEqual(r.connection.socket.sendall.call_count,30)
        # One ACK reports 29 available, but the other 29 sends reserve all of them.
        del r.wav_inflight[next(iter(r.wav_inflight))]
        r.wav_pending=next((key,item[0]) for key,item in r.wav_inflight.items())
        r.wav_status.accepted=480;r.wav_status.free_blocks=29
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.5):
            r.service_wav()
        self.assertEqual(r.connection.socket.sendall.call_count,30)
        r.wav_request(3)
        self.assertIsNone(r.wav_codes)
        self.assertEqual(len(r.wav_inflight),1)
        self.assertNotEqual(next(iter(r.wav_inflight.values()))[1],13)

    def test_legacy_capacity_and_non_radio_keep_sixteen_limit(self):
        for slots,radio in ((16,True),(30,False)):
            r,s=self.receiver(slots)
            s.chunk_interval=0;s.radio_audio=radio
            r.service_wav();r.service_wav()
            self.assertEqual(len(r.wav_inflight),16)
            self.assertEqual(r.wav_next_offset,16*480)
