"""RADIO demodulates CH1 for every resolution and transport channel count."""
import unittest
from unittest.mock import patch,Mock
import numpy as np
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.radio_am import radio_input_supported,radio_tuning_max
from monitor.v17.processing import BatchProcessor,ProcessingSettings
from monitor.v17.numeric_batch import NumericBatch,SampleClock
CASES=((8,1600000),(10,1167883),(12,981595),(14,851063),
       (8,40000),(10,40000),(12,40000),(14,40000),(16,76226),(16,40000))
class RadioBitsTests(unittest.TestCase):
 def test_all_bits_and_dual_transport_recover_ch1_modulation(self):
  for bits,rate in CASES:
   with self.subTest(bits=bits,rate=rate):
    c=Configuration(bits,rate);self.assertTrue(radio_input_supported(c))
    frequency=min(20000,radio_tuning_max(c.actual_rate)*.7)
    owner=BatchProcessor();settings=ProcessingSettings(acquisition=c,radio_enabled=True,radio_frequency=frequency)
    count=max(2048,int(c.actual_rate*.03));audio=[];clock=SampleClock(c.timestamp_hz)
    for block in range(4):
     indices=block*count+np.arange(count,dtype=np.uint32);t=indices/c.actual_rate
     rf=1.65+.5*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*frequency*t)
     raw=np.zeros((count,4),np.uint32);raw[:,0]=(1000000+indices.astype(np.uint64)*c.period).astype(np.uint32)
     raw[:,1]=np.rint(rf*c.maximum/3.3).astype(np.uint32)
     raw[:,2]=c.maximum//2;raw[:,3]=indices
     batch=NumericBatch(raw,c.maximum,clock,c.channels);batch.acquisition=c
     result=owner.process(batch,settings).processing
     self.assertIsNone(result['radio_status']);audio.append(result['audio'])
    values=np.concatenate(audio)[800:];spectrum=np.abs(np.fft.rfft((values-values.mean())*np.hanning(len(values))))
    peak=np.fft.rfftfreq(len(values),1/40000)[np.argmax(spectrum)]
    self.assertAlmostEqual(peak,1000,delta=35)
 def test_insufficient_rf_rate_returns_status_without_constructing_demodulator(self):
  from types import SimpleNamespace
  c=Configuration(16,1000);self.assertFalse(radio_input_supported(c))
  batch=SimpleNamespace(acquisition=c,columns={})
  result=BatchProcessor().process(batch,ProcessingSettings(acquisition=c,radio_enabled=True)).processing
  self.assertIsNone(result['audio']);self.assertIn('20 kHz',result['radio_status'])
 def test_radio_plot_keeps_receiving_audio_across_resolution_changes(self):
  from PyQt6 import QtWidgets
  from monitor.v17.app import SerialMonitorWindow
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.trigger_checkbox.setChecked(False)
   for name,action in w.graph_channel_actions.items():action.setChecked(name=='RADIO')
   for bits,rate in CASES:
    with self.subTest(bits=bits,rate=rate):
     c=Configuration(bits,rate);w._acquisition_confirmed(bits,rate)
     frequency=min(20000,radio_tuning_max(c.actual_rate)*.7)
     w.radio_frequency.setValue(frequency/1000);w.radio_enabled.setChecked(True)
     owner=BatchProcessor();clock=SampleClock(c.timestamp_hz);count=max(2048,int(c.actual_rate*.03))
     for block in range(3):
      index=block*count+np.arange(count,dtype=np.uint32);t=index/c.actual_rate
      rf=1.65+.5*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*w.radio_frequency.value()*1000*t)
      raw=np.zeros((count,4),np.uint32)
      raw[:,0]=(1000000+index.astype(np.uint64)*c.period).astype(np.uint32)
      raw[:,1]=np.rint(rf*c.maximum/3.3).astype(np.uint32);raw[:,2]=c.maximum//2;raw[:,3]=index
      batch=NumericBatch(raw,c.maximum,clock,c.channels);batch.acquisition=c
      owner.process(batch,w._processing_settings());w.handle_batch(batch)
     self.assertIsNotNone(w.radio_stream)
     self.assertGreater(w.radio_stream.counter,100)
     w.render_frame()
     self.assertTrue(w.line_items['RADIO'].isVisible())
     self.assertGreater(len(w.line_items['RADIO'].getData()[1]),10)
  finally:w.close();app.processEvents()
 def test_profile_changes_clamp_tuning_and_output_mode_accepts_each_resolution(self):
  from PyQt6 import QtWidgets
  from monitor.v17.app import SerialMonitorWindow
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.generator_mode.setCurrentIndex(7);w._wav_capable=True
   w.wav_rate.model().item(w.wav_rate.findData(40000)).setEnabled(True)
   for bits,rate in CASES:
    with self.subTest(bits=bits,rate=rate):
     w._acquisition_confirmed(bits,rate);w.radio_frequency.setValue(600)
     self.assertLessEqual(w.radio_frequency.value()*1000,radio_tuning_max(w.applied_configuration.actual_rate))
     w.serial_worker=Mock();w.output_pending=False;w._auto_apply_timer.stop();w._wav_active=False
     w.radio_output_panel.toggle();source=w.radio_output_panel.source
     self.assertIsNotNone(source,w.radio_output_panel.state.text())
     w.serial_worker.request_wav.assert_called_once_with(1,source,40000)
     w.radio_output_panel.stop();w.serial_worker=None;w._wav_active=False
  finally:w.serial_worker=None;w.close();app.processEvents()
