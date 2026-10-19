import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from monitor.v17.radio_output import RadioDacSource
from monitor.v17.processing import BatchProcessor,ProcessingSettings
from monitor.v17.digital_filter import FilterConfig
from monitor.v17.receiver.unoq_acquisition import Configuration
class FilterOutputTests(unittest.TestCase):
 def test_empty_resampler_startup_does_not_fault_filter_or_source(self):
  config=Configuration(14,40000)
  settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=10000,filter=FilterConfig(source='RADIO',mode='bandstop',cutoff=49,upper=51))
  processor=BatchProcessor();source=RadioDacSource(input_source='FILTER')
  with patch('monitor.v17.processing.RadioStream') as stream:
   stream.return_value.resampler.output_count=0
   stream.return_value.demod.process.return_value=np.zeros(4)
   stream.return_value.resampler.process.return_value=np.empty(0)
   batch=SimpleNamespace(acquisition=config,columns={'CH1':np.zeros(4)})
   result=processor.process(batch,settings).processing
   source.feed_result(result);self.assertIsNone(source.error)
   stream.return_value.resampler.process.return_value=np.zeros(480)
   result=processor.process(batch,settings).processing
   source.feed_result(result);self.assertIsNone(source.error)
   self.assertEqual(source.diagnostics()['buffered_samples'],480)
 def test_routes_filtered_values_and_preserves_neutral_on_filter_change(self):
  source=RadioDacSource(1,buffer_seconds=0,input_source='FILTER')
  settings=ProcessingSettings(filter=FilterConfig(source='RADIO',mode='highpass'),radio_enabled=True)
  result=dict(settings=settings,audio=np.full(4,2.5),audio_filter=np.full(4,.2),audio_filter_offset=0.,radio_key=(1600000,550000,40000))
  source.feed_result(result)
  expected=round(1.85*4095/3.3)
  np.testing.assert_array_equal(source.try_codes(0,4),np.full(4,expected))
  source.feed_result(result)
  result['settings']=replace(settings,filter=replace(settings.filter,cutoff=200))
  source.feed_result(result)
  np.testing.assert_array_equal(source.try_codes(4,8),np.full(4,2048))
  self.assertEqual(source.retunes,1)
 def test_true_dc_reference_for_every_audio_filter_family(self):
  config=Configuration(14,40000)
  for mode in ('lowpass','highpass','bandpass','bandstop','bypass'):
   for design in ('Butterworth','Bessel','Chebyshev I','Chebyshev II','Elliptic'):
    with self.subTest(mode=mode,design=design):
     settings=ProcessingSettings(acquisition=config,radio_enabled=True,radio_frequency=10000,radio_gain=1.,filter=FilterConfig(source='RADIO',mode=mode,design=design,cutoff=49,upper=51))
     processor=BatchProcessor();batch=SimpleNamespace(acquisition=config,columns={'CH1':np.zeros(4096)})
     with patch('monitor.v17.processing.RadioStream') as stream:
      stream.return_value.resampler.output_count=0
      stream.return_value.demod.process.return_value=np.zeros(4096)
      stream.return_value.resampler.process.return_value=np.zeros(4096)
      result=processor.process(batch,settings).processing
     source=RadioDacSource(1,buffer_seconds=0,input_source='FILTER');source.feed_result(result)
     codes=source.try_codes(0,480)
     self.assertLessEqual(np.max(abs(codes.astype(int)-2048)),1)
 def test_missing_filter_is_explicit_error_not_raw_radio_fallback(self):
  source=RadioDacSource(input_source='FILTER')
  source.feed_result(dict(settings=ProcessingSettings(),audio=np.ones(3),radio_key=(1600000,550000,40000)))
  self.assertIn('fuente de FILTER',source.error)
 def test_ui_filter_source_and_preset_preserve_off(self):
  from PyQt6 import QtWidgets
  from monitor.v17.app import SerialMonitorWindow
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   generation=w._processing_generation
   w.filter_preset.setCurrentIndex(w.filter_preset.findData('reject_50'))
   self.assertEqual(w.filter_config.source,'OFF');self.assertEqual(w.filter_config.mode,'bandstop')
   self.assertEqual((w.filter_config.cutoff,w.filter_config.upper),(49,51))
   self.assertEqual(w._processing_generation,generation+1)
   w.filter_source.setCurrentText('RADIO')
   self.assertTrue(w.filter_cut.isEnabled());self.assertTrue(w.filter_upper.isEnabled())
   self.assertFalse(w.filter_design.model().item(w.filter_design.findData('RC')).isEnabled())
   w.radio_output_panel.input_source.setCurrentText('FILTER')
   w._acquisition_confirmed(14,599250);w.radio_frequency.setValue(20)
   w.serial_worker=Mock();w._wav_capable=True;w.output_pending=False
   w.wav_rate.model().item(w.wav_rate.findData(40000)).setEnabled(True)
   w.radio_output_panel.toggle();self.assertEqual(w.radio_output_panel.source.input_source,'FILTER')
   w.filter_source.setCurrentText('OFF');self.assertIsNone(w.radio_output_panel.source)
  finally:w.serial_worker=None;w.close();app.processEvents()
if __name__=='__main__':unittest.main()

class RadioVisibilityTests(unittest.TestCase):
 def test_enable_selects_radio_in_temporal_fft_and_heatmap(self):
  from PyQt6 import QtWidgets
  from monitor.v17.app import SerialMonitorWindow
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.radio_enabled.setChecked(True)
   self.assertTrue(w.selected_columns['RADIO'])
   self.assertEqual([combo.currentText() for combo in w.spectral.channels],['RADIO','Ninguno'])
   for mode in (0,1,2):
    w.spectral.set_mode(mode)
    self.assertTrue(w.graph_channel_actions['RADIO'].isChecked())
    self.assertIn('RADIO',[combo.currentText() for combo in w.spectral.channels])
   w.spectral.channels[0].setCurrentText('FILTER')
   w.radio_frequency.setValue(10)
   self.assertEqual(w.spectral.channels[0].currentText(),'FILTER')
   w.radio_enabled.setChecked(False)
   self.assertTrue(w.selected_columns['RADIO'])
  finally:w.close();app.processEvents()
