import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from experimentos.radio_frame_service_v17.receiver import service_each_frame


class FrameServiceTests(unittest.TestCase):
    def receiver(self):
        r=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
        source=RadioDacSource(buffer_seconds=0)
        source.feed_result(dict(settings=ProcessingSettings(radio_offset=0),audio=np.zeros(20000),radio_key=(1250000,20000,40000)))
        r.wav_codes=source;r.wav_started=True;r.wav_session=123;r.wav_candidate=True
        r.wav_status=SimpleNamespace(session=123,queue_slots=30,free_blocks=30,accepted=0)
        r.decoder=SimpleNamespace(events=[])
        r.wav_chunk_tokens=0;r.wav_chunk_token_at=100.
        return r

    def test_adc_only_frames_refill_at_existing_pacing_and_capacity(self):
        r=self.receiver()
        for i in range(1,40):
            with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100+i*.0061):service_each_frame(r)
        self.assertEqual(len(r.wav_inflight),30)
        self.assertEqual(r.wav_next_offset,30*480)
        self.assertEqual(r.connection.socket.sendall.call_count,30)

    def test_pending_control_stays_serialized_and_stop_cannot_restart(self):
        r=self.receiver();r.wav_request(0)
        with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.1):service_each_frame(r)
        self.assertEqual(r.connection.socket.sendall.call_count,1)
        r.wav_request(3);service_each_frame(r)
        self.assertIsNone(r.wav_codes)
        self.assertEqual(r.connection.socket.sendall.call_count,2)
