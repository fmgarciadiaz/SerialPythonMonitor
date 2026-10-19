import unittest,threading
from unittest.mock import Mock,patch
from types import SimpleNamespace
import numpy as np
from experimentos.radio14_refill_v17.radio_source import RadioDacSource
from monitor.v17.processing import ProcessingSettings
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver


class RefillTests(unittest.TestCase):
 def result(self,n=20000):
  return dict(settings=ProcessingSettings(radio_offset=0),audio=np.zeros(n),radio_key=(851063,20000,40000))

 def test_slow_loop_comparison_does_not_block_audio_or_stop(self):
  source=RadioDacSource(buffer_seconds=0);source.feed_result(self.result())
  entered=threading.Event();release=threading.Event()
  def observe(*_):entered.set();release.wait(2);return True
  with patch.object(source.loop_guard,'observe',side_effect=observe):
   worker=threading.Thread(target=source.observe_input,args=(np.zeros(100),851063));worker.start()
   self.assertTrue(entered.wait(1))
   consumer=threading.Thread(target=lambda:(source.try_codes(0,480),source.feed_result(self.result(480)),source.close()))
   consumer.start();consumer.join(.5)
   try:self.assertFalse(consumer.is_alive(),'correlation blocked audio/Stop')
   finally:release.set();worker.join(2);consumer.join(2)
   self.assertTrue(source.closed)

 def test_recovery_after_170ms_stays_within_confirmed_capacity(self):
  r=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
  source=RadioDacSource(buffer_seconds=0);source.feed_result(self.result())
  r.wav_codes=source;r.wav_session=1;r.wav_started=True;r.wav_candidate=True
  r.wav_status=SimpleNamespace(session=1,free_blocks=30,accepted=0,queue_slots=30)
  r.wav_chunk_tokens=0;r.wav_chunk_token_at=100
  with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.170):r.service_wav()
  self.assertEqual(len(r.wav_inflight),16)
  self.assertEqual(r.wav_next_offset,16*480)
  with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.340):r.service_wav()
  self.assertEqual(len(r.wav_inflight),30)
  r.wav_request(3);self.assertEqual(len(r.wav_inflight),1)
