"""File audio must refill concurrently without overrunning negotiated credits."""
import struct,unittest
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver

class WavPcmDeliveryTests(unittest.TestCase):
 def receiver(self,slots=30,free=None,started=True,count=48000):
  r=OutputReceiver(SimpleNamespace(socket=Mock(),read=lambda:b''),lambda _:None)
  r.wav_candidate=True;r.wav_codes=np.zeros(count,dtype='<u2');r.wav_session=123;r.wav_started=started
  r.wav_status=SimpleNamespace(session=123,free_blocks=slots if free is None else free,accepted=0,queue_slots=slots)
  return r
 def test_running_file_reserves_two_chunks_with_consecutive_offsets(self):
  r=self.receiver();r.service_wav();r.service_wav()
  frames=[call.args[0] for call in r.connection.socket.sendall.call_args_list]
  self.assertEqual(len(frames),2)
  self.assertEqual([struct.unpack_from('<I',f,20)[0] for f in frames],[0,480])
  self.assertEqual(r.wav_next_offset,960)
 def test_pending_chunks_never_exceed_reported_free_slots(self):
  for slots in (16,30):
   r=self.receiver(slots,free=1)
   for _ in range(5):r.service_wav()
   self.assertEqual(len(r.wav_inflight),1)
   self.assertEqual(r.wav_next_offset,480)
 def test_begin_and_stop_stay_serialized(self):
  r=self.receiver(started=False)
  r.service_wav();r.service_wav()
  self.assertEqual(len(r.wav_inflight),1)
  r.wav_request(3)
  self.assertIsNone(r.wav_codes)
  self.assertEqual(len(r.wav_inflight),1)
  self.assertNotEqual(next(iter(r.wav_inflight.values()))[1],13)
 def test_last_short_chunk_is_sent_once_with_exact_length(self):
  r=self.receiver(count=700)
  for _ in range(5):r.service_wav()
  frames=[call.args[0] for call in r.connection.socket.sendall.call_args_list]
  self.assertEqual([struct.unpack_from('<H',f,24)[0] for f in frames],[480,220])
  self.assertEqual(r.wav_next_offset,700)
