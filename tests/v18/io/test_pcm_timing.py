import unittest
from unittest.mock import patch
import numpy as np
from monitor.v18.io.receiver_process import RemotePcmSource
from monitor.v18.radio_output import RadioDacSource
class PcmTimingTests(unittest.TestCase):
 def test_dac_snapshot_preserves_inflight_age_and_ack_offsets(self):
  from types import SimpleNamespace
  from monitor.v18.io.receiver_process import wav_delivery_snapshot
  receiver=SimpleNamespace(wav_inflight={1:(10.,13),2:(10.1,13)},wav_next_offset=1440,
   wav_status=SimpleNamespace(accepted=480,played=0,free_blocks=29))
  row=wav_delivery_snapshot(receiver,10.25)
  self.assertEqual(row['inflight'],2);self.assertAlmostEqual(row['oldest_inflight_ms'],250)
  self.assertEqual((row['next_offset'],row['accepted'],row['played']),(1440,480,0))
  source=RemotePcmSource(dict(session=1),lambda event:None)
  for _ in range(50):source.observe_transport('send_to_ack',.25)
  snapshot=source.transport_snapshot()
  self.assertEqual(snapshot['delivery_max_ms']['send_to_ack'],250)
  self.assertEqual(len(snapshot['slow_delivery']),16)
 def test_reply_breakdown_and_stale_replies_do_not_pollute_metrics(self):
  s=RemotePcmSource(dict(session=1,radio_audio=True),lambda e:None)
  with patch('monitor.v18.io.receiver_process.time.monotonic',return_value=10.):s.try_codes(0,480)
  timing=dict(parent_received_at=10.1,render_started_at=10.3,render_finished_at=10.35)
  with patch('monitor.v18.io.receiver_process.time.monotonic',return_value=10.4):
   self.assertFalse(s.accept(2,0,np.zeros(480,dtype=np.uint16),timing))
   self.assertEqual(s.stage_max_ms,{})
   self.assertTrue(s.accept(1,0,np.zeros(480,dtype=np.uint16),timing))
  snapshot=s.transport_snapshot()
  for name,expected in dict(request_to_parent=100,executor_wait=200,render=50,reply_to_child=50).items():
   self.assertAlmostEqual(snapshot['stage_max_ms'][name],expected)
  self.assertEqual(snapshot['last_reply_timing']['offset'],0)
  self.assertAlmostEqual(sum(snapshot['stage_max_ms'].values()),snapshot['roundtrip_max_ms'])
 def test_invalid_optional_timing_does_not_reject_valid_pcm(self):
  s=RemotePcmSource(dict(session=1),lambda e:None)
  s.try_codes(0,480)
  self.assertTrue(s.accept(1,0,np.zeros(480,dtype=np.uint16),dict(render_started_at=float('nan'))))
  self.assertEqual(s.stage_max_ms,{})
 def test_snapshot_distinguishes_pending_roundtrip_and_cached_prefix(self):
  events=[];s=RemotePcmSource(dict(session=1,radio_audio=True),events.append)
  with patch('monitor.v18.io.receiver_process.time.monotonic',return_value=10.):s.try_codes(0,480)
  self.assertEqual(events[0]['requested_at'],10.)
  with patch('monitor.v18.io.receiver_process.time.monotonic',return_value=10.25):
   self.assertAlmostEqual(s.transport_snapshot()['pending_age_ms'],250)
   s.accept(1,0,np.zeros(480,dtype=np.uint16))
   self.assertAlmostEqual(s.transport_snapshot()['roundtrip_max_ms'],250)
   self.assertEqual(s.transport_snapshot()['cached_samples'],480)
   self.assertEqual(len(s.try_codes(0,480)),480)
   self.assertIsNone(s.transport_snapshot()['pending_age_ms'])
 def test_underrun_keeps_child_time_separate_from_parent_notification(self):
  s=RadioDacSource(buffer_seconds=0)
  with patch('monitor.v18.radio_output.time.monotonic',return_value=20.):s.record_transport_underrun(dict(pending=(0,480),pending_age_ms=300),19.5)
  row=s.diagnostics()['transport_underrun']
  self.assertEqual(row['child_observed_at'],19.5);self.assertEqual(row['parent_observed_at'],20.)
  self.assertEqual(row['pending'],(0,480))
if __name__=='__main__':unittest.main()
