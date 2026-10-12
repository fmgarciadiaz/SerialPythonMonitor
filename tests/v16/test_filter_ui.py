import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PyQt6 import QtWidgets
import numpy as np
from monitor.v16.app import SerialMonitorWindow
class FilterUiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v16.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):self.w.close()
 def test_temporal_axis_label_updates_only_when_changed(self):
  with patch.object(self.w.plot_widget,'setLabel',wraps=self.w.plot_widget.setLabel) as setter:
   self.w._set_temporal_x_label('Etiqueta temporal de prueba')
   self.w._set_temporal_x_label('Etiqueta temporal de prueba')
   self.assertEqual(setter.call_count,1)
   self.w._set_temporal_x_label('Tiempo relativo en ventana (µs)')
   self.assertEqual(setter.call_count,2)
  axis=self.w.plot_widget.getAxis('bottom')
  self.assertEqual(axis.labelText,'Tiempo relativo en ventana (µs)')
  self.assertEqual(axis.labelStyle['color'],'#ffffff')
 def test_demo_and_filter_display(self):
  self.w.start_demo();self.w.demo_timer.stop();self.w._generate_demo_samples();self.w._generate_demo_samples()
  self.assertEqual(len(self.w.series['FILTER']),100)
  self.w.graph_channel_actions['CH2'].setChecked(False)
  self.w.graph_channel_actions['FILTER'].setChecked(True)
  self.assertEqual(self.w.selected_columns,{'CH1':True,'CH2':False,'FILTER':True})
  self.w.render_frame()
 def test_changed_filter_resets_history(self):
  batch=[{'CH1':1.65,'CH2':.5,'Muestra':i,'Tiempo (us)':i*25} for i in range(100)]
  self.w.handle_batch(batch);self.assertEqual(len(self.w.series['FILTER']),100)
  self.w.filter_source.setCurrentText('CH2');self.assertEqual(len(self.w.series['FILTER']),0)
  self.w.handle_batch(batch);np.testing.assert_allclose(np.asarray(self.w.series['FILTER']),.5,atol=1e-10)
 def test_spectral_choices_and_nyquist(self):
  for combo in self.w.spectral.channels:self.assertGreaterEqual(combo.findText('FILTER'),0)
  self.w.start_demo();self.w.demo_timer.stop()
  self.assertLessEqual(self.w.filter_cut.maximum(),1125)

 def test_frequency_controls_follow_mode(self):
  self.assertFalse(self.w.filter_cut.isEnabled());self.assertTrue(self.w.filter_upper.isEnabled())
  self.w.filter_mode.setCurrentIndex(self.w.filter_mode.findData('highpass'))
  self.assertTrue(self.w.filter_cut.isEnabled());self.assertFalse(self.w.filter_upper.isEnabled())
  self.assertEqual(self.w.filter_config.cutoff,self.w.filter_cut.value())
  self.w.filter_mode.setCurrentIndex(self.w.filter_mode.findData('bandpass'))
  self.assertTrue(self.w.filter_cut.isEnabled());self.assertTrue(self.w.filter_upper.isEnabled())
  self.w.filter_mode.setCurrentIndex(self.w.filter_mode.findData('bypass'))
  self.assertFalse(self.w.filter_cut.isEnabled());self.assertFalse(self.w.filter_upper.isEnabled())
 def test_eye_menu_and_icons(self):
  self.assertEqual(set(self.w.graph_channel_actions),{'CH1','CH2','FILTER'})
  self.assertFalse(hasattr(self.w,'graph_eye'))
  self.assertEqual(len(self.w.legend.items),3)
  for combo in (self.w.filter_mode,self.w.filter_design):
   for i in range(combo.count()):self.assertFalse(combo.itemIcon(i).isNull())

 def test_legend_sample_updates_persistent_selection(self):
  from unittest.mock import Mock
  from PyQt6 import QtCore
  self.w.start_demo();self.w.demo_timer.stop();self.w._generate_demo_samples()
  sample,label=self.w.legend.items[0]
  event=Mock();event.button.return_value=QtCore.Qt.MouseButton.LeftButton
  sample.mouseClickEvent(event)
  self.assertFalse(self.w.selected_columns['CH1']);self.w.render_frame()
  self.assertFalse(self.w.line_items['CH1'].isVisible())
  label.mouseClickEvent(event);self.assertTrue(self.w.selected_columns['CH1'])
 def test_dial_value_is_not_editable(self):
  for spin,label in self.w.filter_value_labels.items():
   self.assertTrue(spin.isHidden());self.assertTrue(label.text())
   self.assertEqual(self.w.filter_dials[spin].width(),54)

 def test_filter_and_trigger_share_tabs(self):
  self.assertEqual(self.w.trigger_filter_tabs.count(),2)
  self.assertIs(self.w.trigger_filter_tabs.widget(1),self.w.columns_panel)
  self.w.trigger_filter_tabs.setCurrentIndex(1)
  self.w.filter_mode.setCurrentIndex(self.w.filter_mode.findData('bandpass'))
  self.assertTrue(self.w.filter_upper.isEnabled())

 def test_transfer_filter_response_uses_derived_signal(self):
  w=self.w;s=w.spectral
  fs=40000;n=8192
  w.filter_upper.setValue(1000)
  t=np.arange(n)/fs
  w.handle_batch([{'CH1':float(1.65+np.sin(2*np.pi*1000*ti)), 'CH2':1.65,
                  'Muestra':i,'Tiempo (us)':i*25} for i,ti in enumerate(t)])
  s.mode=1;s.fft_mode.setCurrentText('Transfer')
  s.transfer_response.setCurrentText('FILTER')
  s._render_fft_analysis(w,fs,1024)
  result=s.statistics_by_channel['FILTER / CH1']
  index=np.argmin(abs(result['frequencies']-1000))
  self.assertAlmostEqual(result['gain_db'][index],-3.01,delta=.25)
  self.assertAlmostEqual(result['phase_deg'][index],-90,delta=4)
 def test_bode_filter_pair_disables_raw_calibration_and_clears_results(self):
  for panel in self.w.spectral.bode.panels:
   panel.result=[(100,0,0)]
   panel.response_channel.setCurrentText('FILTER')
   self.assertEqual(panel.pair(),('CH1','FILTER'))
   self.assertEqual(panel.result,[])
   self.assertFalse(panel.calibrated.isEnabled())
   self.assertEqual(panel.reference_for(0,self.w.applied_configuration),(None,None))

 def test_high_rates_are_offered_and_16bit_limit_remains(self):
  combo=self.w.config_rate_combo
  for rate in (200000,250000,333333):
   index=combo.findData(rate)
   self.assertGreaterEqual(index,0)
   self.assertNotIn('experimental',combo.itemText(index))
  from monitor.v16.receiver.unoq_acquisition import Configuration
  for rate in (200000,250000,333333):
   with self.assertRaises(ValueError):Configuration(16,rate)

 def test_numeric_hardware_blocks_keep_all_columns_and_continuity(self):
  from monitor.v16.numeric_batch import NumericBatch
  for start in (0,128):
   i=np.arange(start,start+128)
   b=NumericBatch(np.column_stack((i*25,np.full(128,8192),np.full(128,4096),i)),16383)
   self.w.handle_batch(b)
  self.assertEqual(len(self.w.series['FILTER']),256)
  np.testing.assert_array_equal(self.w.series['Muestra'][:],np.arange(256))
  np.testing.assert_array_equal(self.w.series['Tiempo (us)'][:],np.arange(256)*25)
  np.testing.assert_allclose(self.w.series['CH1'][:],8192*3.3/16383)
  np.testing.assert_allclose(self.w.series['FILTER'][:],8192*3.3/16383)
 def test_short_horizontal_window_uses_microseconds_and_roundtrips(self):
  self.w.current_dt_us=5
  self.w.x_axis_time_mode=True
  self.w.on_h_scale_changed(8)
  self.assertEqual(self.w.lbl_h_scale.suffix(),' µs')
  self.assertEqual(self.w.lbl_h_scale.value(),40)
  self.w._on_h_scale_input(100)
  self.assertEqual(self.w.h_scale,20)
  self.w.on_h_scale_changed(1000)
  self.assertEqual(self.w.lbl_h_scale.suffix(),' ms')

 def test_numeric_recording_keeps_original_channels(self):
  import io,wave,time
  from monitor.v16.numeric_batch import NumericBatch
  w=self.w;stream=io.BytesIO();w.record_file=stream
  w.record_wave=wave.open(stream,'wb');w.record_wave.setparams((2,2,40000,0,'NONE','not compressed'))
  w.record_previous=None;w.record_dc_filter=None;w.record_rows=0;w.record_last_flush_time=time.perf_counter()
  raw=np.array([[0,0,16383,0],[25,16383,0,1]],dtype=float)
  batch=NumericBatch(raw,16383)
  w._write_wave_batch(batch);w.record_wave.close();w.record_wave=None
  reader=wave.open(io.BytesIO(stream.getvalue()),'rb')
  np.testing.assert_array_equal(np.frombuffer(reader.readframes(2),dtype='<i2'),[-32768,32767,32767,-32768])
  reader.close();w.record_file=None

 def test_generator_50khz_controls(self):
  w=self.w
  for spin,dial in ((w.generator_frequency,w.generator_frequency_dial),(w.generator_final_frequency,w.generator_final_frequency_dial)):
   self.assertEqual(spin.maximum(),50000)
   dial.setValue(1000);self.assertEqual(spin.value(),50000)
   spin.setValue(40000);self.assertLess(dial.value(),1000)

 def test_ch1_fast_selector_channels_clock_and_mono_recording(self):
  import io,wave,time
  from monitor.v16.numeric_batch import NumericBatch,SampleClock
  from monitor.v16.receiver.unoq_acquisition import Configuration
  w=self.w
  for rate in (599250,661157):
   idx=w.config_rate_combo.findData(rate)
   self.assertGreaterEqual(idx,0)
   self.assertTrue(w.config_rate_combo.itemText(idx).endswith(' kHz (CH1)'))
  w._acquisition_confirmed(14,661157)
  self.assertAlmostEqual(w._horizontal_dt_us(),242/160)
  w._acquisition_confirmed(14,599250)
  self.assertFalse(w.graph_channel_actions['CH2'].isEnabled())
  ch2_index=w.meas_channel_combo.findText('CH2')
  self.assertTrue(ch2_index<0 or not w.meas_channel_combo.model().item(ch2_index).isEnabled())
  self.assertAlmostEqual(w._horizontal_dt_us(),267/160)
  clock=SampleClock(160000000)
  batch=NumericBatch([(0xffffff00,0,0,0),((0xffffff00+267)&0xffffffff,16383,0,1)],16383,clock,1)
  self.assertAlmostEqual(np.diff(batch.columns['Tiempo (us)'])[0],267/160)
  self.assertTrue(np.isnan(batch.columns['CH2']).all())
  stream=io.BytesIO();w.record_file=stream;w.record_wave=wave.open(stream,'wb')
  w.record_wave.setparams((1,2,599250,0,'NONE','not compressed'))
  w.record_previous=None;w.record_dc_filter=None;w.record_rows=0;w.record_last_flush_time=time.perf_counter()
  w._write_wave_batch(batch)
  next_batch=NumericBatch([((0xffffff00+534)&0xffffffff,8192,0,2),((0xffffff00+801)&0xffffffff,8192,0,3)],16383,clock,1)
  w._write_wave_batch(next_batch);w.record_wave.close();w.record_wave=None
  reader=wave.open(io.BytesIO(stream.getvalue()),'rb');self.assertEqual(reader.getnchannels(),1);self.assertEqual(reader.getnframes(),4);reader.close();w.record_file=None
  w._acquisition_confirmed(14,333333)
  self.assertTrue(w.graph_channel_actions['CH2'].isEnabled())


 def test_16bit_hides_unavailable_rates_and_restores_them(self):
  w=self.w;combo=w.config_rate_combo
  w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(16));w._destination_changed()
  for i in range(combo.count()):
   self.assertEqual(combo.view().isRowHidden(i),not combo.model().item(i).isEnabled())
  self.assertFalse(combo.view().isRowHidden(combo.findData(71428)))
  self.assertTrue(combo.view().isRowHidden(combo.findData(100000)))
  w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(14));w._destination_changed()
  self.assertFalse(combo.view().isRowHidden(combo.findData(661157)))
  self.assertTrue(combo.view().isRowHidden(combo.findData(1203007)))

 def test_rate_visibility_for_each_resolution(self):
  from monitor.v16.receiver.unoq_acquisition import Configuration
  w=self.w;combo=w.config_rate_combo
  for bits in (8,10,12,14,16):
   with self.subTest(bits=bits):
    w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(bits))
    for i in range(combo.count()):
     try:
      Configuration(bits,combo.itemData(i));valid=True
     except ValueError:
      valid=False
     self.assertEqual(not combo.view().isRowHidden(i),valid)
    self.assertFalse(combo.view().isRowHidden(combo.currentIndex()))

 def test_ch2_restored_after_single_channel_switch(self):
  w=self.w
  w.meas_channel_combo.setCurrentText('CH2');w.filter_source.setCurrentText('CH2')
  w.graph_channel_actions['CH2'].setChecked(True)
  w._acquisition_confirmed(14,599250)
  self.assertEqual(w.meas_channel_combo.findText('CH2'),-1)
  w._acquisition_confirmed(14,661157)
  w._acquisition_confirmed(14,333333)
  self.assertEqual(w.meas_channel_combo.currentText(),'CH2')
  self.assertEqual(w.active_meas_channel,'CH2')
  self.assertEqual(w.filter_source.currentText(),'CH2')
  self.assertTrue(w.graph_channel_actions['CH2'].isChecked())
  self.assertTrue(w.selected_columns['CH2'])

 def test_ch2_restored_after_single_channel_fft(self):
  w=self.w;w.spectral.set_mode(1)
  w.meas_channel_combo.setCurrentText('CH2')
  w.spectral.channels[0].setCurrentText('CH2')
  w._acquisition_confirmed(14,599250)
  w.spectral.render()
  w._acquisition_confirmed(14,333333)
  self.assertEqual(w.meas_channel_combo.currentText(),'CH2')
  self.assertEqual(w.active_meas_channel,'CH2')
  self.assertEqual(w.spectral.channels[0].currentText(),'CH2')
