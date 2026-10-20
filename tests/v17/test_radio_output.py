import unittest
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.processing import ProcessingSettings

class RadioOutputSourceTests(unittest.TestCase):
 def test_delivery_trace_distinguishes_transport_stall_with_host_audio(self):
  with patch('monitor.v17.radio_output.time.monotonic',return_value=10.):
   s=RadioDacSource(1,buffer_seconds=0)
   s.feed_result(self.result(np.ones(960)*.1))
   s.try_codes(0,480)
  with patch('monitor.v17.radio_output.time.monotonic',return_value=10.2):
   s.observe_transport('read',.15)
   s.observe_status(SimpleNamespace(state=4,played=0,accepted=480))
   d=s.diagnostics()
  self.assertEqual(d['rate'],40000)
  self.assertEqual(d['buffered_samples'],480)
  self.assertEqual(d['delivery']['transport_max_ms']['read'],150)
  self.assertEqual([e['kind'] for e in d['delivery']['events']],['read','dac_underrun'])
  self.assertEqual(d['delivery']['events'][-1]['remaining_samples'],480)
  self.assertAlmostEqual(d['delivery']['feed_age_ms'],200)
 def test_delivery_trace_bounds_events_and_counts_missing_audio(self):
  s=RadioDacSource(1,buffer_seconds=0)
  s.feed_result(self.result(np.ones(480)*.1));s.try_codes(0,480)
  self.assertIsNone(s.try_codes(480,960))
  for _ in range(100):s.observe_transport('read',.05)
  d=s.diagnostics()['delivery']
  self.assertEqual(d['audio_waits'],1)
  self.assertEqual(len(d['events']),64)
 def result(self,values,frequency=550000,rate=40000,generation=0):
  return dict(audio=np.asarray(values,dtype=float)+1.65,radio_key=(1403508,frequency,rate),
      generation=generation,settings=ProcessingSettings(radio_enabled=True,radio_offset=1.65,generation=generation))
 def test_scan_fades_reach_neutral_without_abrupt_steps(self):
  s=RadioDacSource(1,buffer_seconds=0)
  s.feed_result(self.result(np.ones(2400)*.5))
  s.fade_in()
  up=s.try_codes(0,960).astype(int)
  self.assertEqual(up[0],2048)
  self.assertLessEqual(np.max(abs(np.diff(up))),2)
  end=s.fade_out()
  self.assertEqual(end,1760)
  down=s.try_codes(960,1920).astype(int)
  self.assertEqual(down[-1],2048)
  self.assertTrue(np.all(down[800:]==2048))
  self.assertLessEqual(np.max(abs(np.diff(down))),2)
 def test_audio_queue_owns_input_without_duplicate_copy(self):
  s=RadioDacSource(1,buffer_seconds=0)
  result=self.result([.1,.2,.3,.4]);s.feed_result(result)
  result['audio'][:]=0
  codes=s.try_codes(0,4)
  np.testing.assert_array_equal(codes,np.rint((np.array([.1,.2,.3,.4])+1.65)*4095/3.3).astype('<u2'))
 def test_order_buffering_volume_and_existing_wav_levels_are_independent(self):
  s=RadioDacSource(1,buffer_seconds=0);self.assertIsNone(s.try_codes(0,4))
  s.observe_status(SimpleNamespace(played=480,accepted=960))
  self.assertEqual((s.played,s.accepted),(480,960))
  s.feed_result(self.result([-.5,0,.5,1]))
  codes=s.try_codes(0,4,(0,0))
  np.testing.assert_array_equal(codes,np.rint(np.array([1.15,1.65,2.15,2.65])*4095/3.3).astype('<u2'))
  s.set_volume(0);s.feed_result(self.result([1]*8));s.try_codes(4,8)
  np.testing.assert_array_equal(s.try_codes(8,12),np.full(4,2048,dtype='<u2'))
  self.assertIsNone(s.try_codes(12,16))
 def test_retune_never_replays_old_audio(self):
  s=RadioDacSource(1,buffer_seconds=0);s.feed_result(self.result([1]*4));s.feed_result(self.result([-.5]*4,frequency=600000))
  self.assertEqual(s.retunes,1)
  np.testing.assert_array_equal(s.try_codes(0,4),np.full(4,2048,dtype='<u2'))
  np.testing.assert_array_equal(s.try_codes(4,8),np.full(4,round(1.15*4095/3.3),dtype='<u2'))
  s.close();s.feed_result(self.result([1]*10));self.assertIsNone(s.try_codes(4,8))
 def test_retune_bridges_last_output_and_fades_new_station_across_chunks(self):
  for reserve in (0,1920):
   with self.subTest(reserve=reserve):
    s=RadioDacSource(1,buffer_seconds=0)
    s.feed_result(self.result(np.full(480+reserve,.6)))
    previous=int(s.try_codes(0,480)[-1])
    s.feed_result(self.result(np.full(2000,-.6),frequency=600000))
    available=s.diagnostics()['buffered_samples']
    self.assertEqual(available,reserve+2000)
    # Fragment the transition to verify that it does not restart per chunk.
    a=s.try_codes(480,617).astype(int)
    b=s.try_codes(617,480+available).astype(int)
    out=np.r_[a,b]
    self.assertEqual(out[0],previous)
    self.assertLessEqual(np.max(np.abs(np.diff(out))),5)
    self.assertEqual(out[-1],round(1.05*4095/3.3))
    self.assertEqual(s.retunes,1)
 def test_requires_demodulated_40k_without_resampling_and_bounds(self):
  s=RadioDacSource(1,buffer_seconds=0);s.feed_result(self.result(np.ones(4800)*.2,rate=48000))
  self.assertIn('40 kHz',s.error);self.assertIsNone(s.try_codes(0,480))
  s=RadioDacSource(1,buffer_seconds=0);s.feed_result(self.result(np.zeros(50000)));self.assertIn('buffer',s.error)
 def test_prefill_absorbs_processing_stalls_and_retune_preserves_reserve(self):
  s=RadioDacSource(1)
  s.feed_result(self.result(np.ones(19000)*.2));self.assertIsNone(s.try_codes(0,480))
  s.feed_result(self.result(np.ones(1000)*.2));self.assertIsNotNone(s.try_codes(0,480))
  s.feed_result(self.result(np.ones(480)*-.2,frequency=575000))
  # No audio from the old station is replayed; neutral keeps its time reserve.
  for start in range(480,19680,480):
   self.assertIsNotNone(s.try_codes(start,start+480))
  self.assertEqual(s.retunes,1)
 def test_credit_polling_is_bounded_and_releases_audio_after_status(self):
  from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
  socket=Mock();r=OutputReceiver(SimpleNamespace(socket=socket,read=lambda:b''),lambda _:None)
  s=RadioDacSource(1,buffer_seconds=0);s.feed_result(self.result(np.ones(960)*.1))
  r.wav_candidate=True;r.wav_codes=s;r.wav_session=123;r.wav_started=True
  r.wav_status=SimpleNamespace(session=123,free_blocks=0,accepted=7680)
  r.wav_next_offset=7680
  with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100):r.service_wav()
  self.assertEqual(socket.sendall.call_count,1);self.assertAlmostEqual(r.wav_poll_at,100.04)
  r.wav_pending=None;r.wav_inflight.clear()
  with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.01):r.service_wav()
  self.assertEqual(socket.sendall.call_count,1)
  # A fresh credit permits immediate refill without waiting for the next query.
  r.wav_status.free_blocks=2;r.wav_next_offset=0;r.wav_status.accepted=0
  with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=100.04):r.service_wav()
  self.assertGreater(socket.sendall.call_count,1)
 def test_radio_credit_window_reserves_only_confirmed_free_slots_and_stop(self):
  from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
  socket=Mock();r=OutputReceiver(SimpleNamespace(socket=socket,read=lambda:b''),lambda _:None)
  source=RadioDacSource(1,buffer_seconds=0);source.chunk_interval=0
  source.feed_result(self.result(np.zeros(8000)))
  r.wav_candidate=True;r.wav_codes=source;r.wav_session=123;r.wav_started=True
  r.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
  r.service_wav();r.service_wav()
  self.assertEqual(len(r.wav_inflight),16)
  r.wav_status.free_blocks=3;r.service_wav()
  self.assertEqual(socket.sendall.call_count,16)
  r.wav_request(3);self.assertEqual(len(r.wav_inflight),1)
  self.assertIsNone(r.wav_codes)
 def test_radio_chunks_are_paced_without_losing_credit_or_position(self):
  from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
  socket=Mock();r=OutputReceiver(SimpleNamespace(socket=socket,read=lambda:b''),lambda _:None)
  source=RadioDacSource(1,buffer_seconds=0);source.feed_result(self.result(np.zeros(10000)))
  r.wav_codes=source;r.wav_session=123;r.wav_started=True
  r.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
  for instant,expected in ((100,1),(100.003,1),(100.007,2),(100.05,9)):
   with patch('monitor.v17.receiver.unoq_config_receiver.time.monotonic',return_value=instant):r.service_wav()
   self.assertEqual(socket.sendall.call_count,expected)
   self.assertEqual(r.wav_next_offset,480*expected)
 def test_worker_feeds_exact_current_dsp_audio_before_gui_delivery(self):
  from monitor.v17.app import OutputWorker
  from monitor.v17.receiver.unoq_switch import Mode
  settings=ProcessingSettings(generation=2,radio_enabled=True)
  w=OutputWorker('offline',Mode.SPI,processing_settings=settings)
  source=RadioDacSource(1,buffer_seconds=0);w.set_radio_output_source(source)
  for generation in (1,2):
   result=self.result([.4]*4,generation=generation)
   from dataclasses import replace
   result['settings']=replace(result['settings'],continuity_epoch=1 if generation==1 else 0)
   f=Future();f.set_result(SimpleNamespace(processing=result,radio_output_session=w._radio_output_session))
   w._processed(f)
  self.assertEqual(len(source.try_codes(0,4)),4)
  self.assertIsNone(source.try_codes(4,8))

class RadioOutputUiTests(unittest.TestCase):
 def test_separate_mode_mirrors_tuning_and_uses_radio_without_changing_adc(self):
  from PyQt6 import QtWidgets
  from monitor.v17.app import SerialMonitorWindow
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w._acquisition_confirmed(14,599250);w.radio_frequency.setValue(20)
   w.generator_mode.setCurrentIndex(7)
   self.assertEqual(w.generator_mode.currentText(),'Radio')
   self.assertEqual(w.generator_mode.itemText(6),'Radio Test')
   self.assertTrue(w.radio_test_panel.isHidden());self.assertFalse(w.radio_output_panel.isHidden())
   self.assertTrue(w.wav_amplitude_box.isHidden());self.assertTrue(w.generator_offset_box.isHidden())
   worker=Mock();w.serial_worker=worker;w._wav_capable=True;w.output_pending=False
   w.wav_rate.model().item(w.wav_rate.findData(40000)).setEnabled(True)
   from monitor.v17.receiver.unoq_acquisition import Configuration
   valid_config=w.applied_configuration
   w.applied_configuration=SimpleNamespace(rate=1600001,actual_rate=1600001,bits=8,channels=1)
   w.radio_output_panel.toggle();self.assertIsNone(w.radio_output_panel.source)
   worker.request_wav.assert_not_called()
   w.applied_configuration=valid_config
   w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(48000))
   w.radio_output_panel.toggle();self.assertIsNone(w.radio_output_panel.source)
   worker.request_wav.assert_not_called()
   w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(40000))
   before=w.applied_configuration
   w.radio_output_panel.toggle()
   self.assertTrue(w.radio_enabled.isChecked(),w.radio_output_panel.state.text());self.assertEqual(w.applied_configuration,before)
   source=w.radio_output_panel.source;self.assertIsInstance(source,RadioDacSource)
   worker.set_radio_output_source.assert_called_with(source);worker.request_wav.assert_called_once_with(1,source,40000)
   w.radio_frequency.setValue(25);self.assertIn('25',w.radio_output_panel.frequency.text())
   w.radio_output_panel.volume.setValue(0);self.assertEqual(w.radio_gain.value(),2)
   w.radio_output_rate.setCurrentIndex(w.radio_output_rate.findData(48000));self.assertIsNone(w.radio_output_panel.source)
   worker.request_wav.assert_called_with(3)
   w.serial_worker=None;w._wav_active=False
  finally:w.serial_worker=None;w.close();app.processEvents()
