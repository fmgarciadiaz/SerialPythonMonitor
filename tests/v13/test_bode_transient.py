import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from scipy.signal import lfilter,chirp
from monitor.historico.v13.bode_pulse import pulse_transfer

class TransientTransferTests(unittest.TestCase):
 def test_long_chirp_checks_only_post_stimulus_tail(self):
  fs=40000;onset=2000;t=np.arange(fs*5)/fs;tail=fs//2
  x=np.r_[np.zeros(onset),.5+.5*chirp(t,f0=20,f1=5000,t1=5,method='logarithmic',phi=-90),np.zeros(tail)]
  data=np.column_stack((np.arange(len(x))/fs,x,x))
  result=pulse_transfer(data,fs,onset,tail_samples=tail)
  valid=np.isfinite(result[:,1]);self.assertGreater(valid.sum(),100)
  np.testing.assert_allclose(result[valid,1:],0,atol=1e-10)
  # The early tail is allowed to contain a decaying circuit response.
  pole=np.exp(-1/fs/.05);data[:,2]=lfilter([1-pole],[1,-pole],x)
  filtered=pulse_transfer(data,fs,onset,tail_samples=tail)
  self.assertGreater(np.isfinite(filtered[:,1]).sum(),100)
  # A genuinely unfinished output is still rejected.
  data[-tail:,2]=.3
  with self.assertRaisesRegex(ValueError,'no terminó'):
   pulse_transfer(data,fs,onset,tail_samples=tail)
 def test_attenuated_output_preserves_gain_but_masks_noisy_phase(self):
  fs=40000;onset=2000;x=np.r_[np.zeros(onset),np.ones(4),np.zeros(20000)]
  # A strongly attenuated output must not invalidate the input reference.
  y=x*.0001
  result=pulse_transfer(np.column_stack((np.arange(len(x))/fs,x,y)),fs,onset)
  valid=np.isfinite(result[:,1]);self.assertGreater(valid.sum(),100)
  np.testing.assert_allclose(result[valid,1],-80,atol=1e-8)
  y=np.random.default_rng(9).normal(0,.005,len(x))
  result=pulse_transfer(np.column_stack((np.arange(len(x))/fs,x,y)),fs,onset)
  self.assertGreater(np.isfinite(result[:,1]).sum(),100)
  self.assertTrue(np.all(np.isnan(result[:,2])))
 def test_output_edge_before_input_does_not_contaminate_noise(self):
  fs=100000;onset=5000;n=55000;rng=np.random.default_rng(7)
  signals=rng.normal(0,.005,(n,2));signals[onset:onset+10,0]+=2
  signals[onset-1:onset+9,1]+=2
  result=pulse_transfer(np.column_stack((np.arange(n)/fs,signals)),fs,onset)
  valid=np.isfinite(result[:,1]);self.assertGreater(valid.sum(),.9*len(result))
  self.assertLess(abs(np.median(result[valid,1])),.2)
 def test_pulse_and_sweeps_recover_rc_gain_and_phase(self):
  fs=40000;onset=2000;tail=20000
  for mode in ('pulse','linear','logarithmic'):
   if mode=='pulse':wave=np.ones(4)
   else:
    t=np.arange(fs*2)/fs
    wave=.5+.5*chirp(t,f0=20,f1=2000,t1=2,method=mode,phi=-90)
   x=np.r_[np.zeros(onset),wave,np.zeros(tail)]
   pole=np.exp(-1/fs/.001);y=lfilter([1-pole],[1,-pole],x)
   data=np.column_stack((np.arange(len(x))/fs,1.65+x,1.65+y))
   result=pulse_transfer(data,fs,onset,20,2000)
   valid=np.isfinite(result[:,1]);self.assertGreater(valid.sum(),20)
   if mode!='pulse':self.assertGreater(valid.sum(),.8*len(result))
   omega=2*np.pi*result[valid,0]/fs;h=(1-pole)/(1-pole*np.exp(-1j*omega))
   np.testing.assert_allclose(result[valid,1],20*np.log10(abs(h)),atol=.001)
   np.testing.assert_allclose(result[valid,2],np.angle(h,deg=True),atol=.001)
 def test_gaps_and_unfinished_response_are_rejected(self):
  fs=40000;data=np.column_stack((np.arange(4000)/fs,np.r_[np.zeros(2000),np.ones(2000)],np.r_[np.zeros(2000),np.ones(2000)]))
  with self.assertRaisesRegex(ValueError,'no terminó'):pulse_transfer(data,fs,2000)
  data[100:,0]+=.01
  with self.assertRaisesRegex(ValueError,'Discontinuidad'):pulse_transfer(data,fs,2000)
 def test_input_spectral_zero_is_masked(self):
  fs=40000;x=np.r_[np.zeros(2000),np.ones(40),np.zeros(20000)]
  result=pulse_transfer(np.column_stack((np.arange(len(x))/fs,x,x)),fs,2000,20,2000)
  nearest=np.argmin(abs(result[:,0]-1000));self.assertTrue(np.isnan(result[nearest,1]))

class BodePanelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PyQt6 import QtWidgets
  cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def test_three_independent_panels_and_manual_start(self):
  from monitor.historico.v13.app import SerialMonitorWindow
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   b=w.spectral.bode;self.assertEqual([a.text() for a in w.spectral.bode_actions],['Bode tono','Bode pulso','Bode sweep'])
   from PyQt6 import QtWidgets
   self.assertIsInstance(b.tabs,QtWidgets.QStackedWidget)
   w.spectral.set_mode(3)
   for i in range(3):
    w.spectral.bode_actions[i].trigger();self.assertFalse(b.active)
    self.assertEqual(b.tabs.currentIndex(),i)
    self.assertEqual(w.spectral.mode,3)
    self.assertEqual(b.panels[i].start.value(),20)
    self.assertEqual(b.panels[i].end.value(),5000)
   pulse=b.panels[1];sweep=b.panels[2]
   self.assertEqual(pulse.button.text(),'Repetir');self.assertEqual(sweep.method.currentText(),'Chirp')
   self.assertIsNot(pulse.history,sweep.history)
  finally:w.close()
 def test_sweep_controls_unlock_after_capture_cancel_and_send_failure(self):
  from unittest.mock import Mock
  from monitor.historico.v13.app import SerialMonitorWindow
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.serial_worker=Mock();w.is_running=True;w._generator_state_known=True
   w._auto_apply_timer.stop();w.spectral.select_bode(2)
   p=w.spectral.bode.panels[2]
   for ending in ('capture','cancel','send_failure'):
    with self.subTest(ending=ending):
     w._generator_requested=None
     w.serial_worker.request_generator.side_effect=RuntimeError('fallo de envío') if ending=='send_failure' else None
     p.begin()
     if ending!='send_failure':
      self.assertTrue(p.active);self.assertFalse(p.method.isEnabled());self.assertFalse(p.duration.isEnabled())
      # A duplicate begin must not replace the saved enabled states.
      p.begin()
      if ending=='capture':
       fs=p.result_profile.rate;low=p.config.low*3.3/4095
       p.stage='capture';p.waiting=False;p.onset=2000
       length=round(fs*p.capture_seconds())
       x=np.r_[np.zeros(2000),np.ones(4),np.zeros(length-5)]
       p.buffer=list(zip(np.arange(len(x))/fs,low+x,low+x))
       p.last_timestamp=(len(x)-1)/fs
       p.batch([{'Tiempo (us)':round(len(x)/fs*1e6),'V_IN':low,'V_OUT':low}])
       self.assertTrue(p.result)
      else:p.cancel()
     self.assertFalse(p.active)
     for control in (p.method,p.duration,p.start,p.end,p.capture):self.assertTrue(control.isEnabled())
     p.method.setCurrentIndex(1-p.method.currentIndex())
     p.duration.setValue(1.5)
     self.assertEqual(p.duration.value(),1.5)
  finally:
   w.serial_worker=None;w.close()
 def test_analysis_selector_matches_generator_and_selects_all_modes(self):
  from monitor.historico.v13.app import SerialMonitorWindow
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   s=w.spectral
   self.assertEqual(s.group.title(),'ANÁLISIS')
   self.assertIs(type(s.mode_combo),type(w.generator_mode))
   for index in range(4):
    self.assertFalse(s.mode_combo.itemIcon(index).isNull())
    s.mode_combo.setCurrentIndex(index)
    self.assertEqual(s.mode,min(index,3))
    self.assertFalse(s.bode.active)
    self.assertEqual(s.secondary_label.text(),'Eje horizontal' if index==0 else 'Muestras' if index<3 else 'Método')
   s.set_mode(1);self.assertEqual(s.mode_combo.currentIndex(),1)
   s.select_bode(1);self.assertEqual(s.mode_combo.currentText(),'Bode')
   self.assertEqual(s.bode_method_combo.currentText(),'Pulso')
   s.bode_method_combo.setCurrentIndex(2);self.assertEqual(s.bode.tabs.currentIndex(),2)
  finally:w.close()

class BodeRenderingTests(unittest.TestCase):
 def test_dense_envelope_keeps_extrema_and_missing_bands(self):
  from monitor.historico.v13.bode import render_envelope
  x=np.arange(100000);y=np.zeros(len(x));y[12345]=42;y[45678]=-30;y[70000]=np.nan
  xx,yy=render_envelope(x,y)
  self.assertLessEqual(len(xx),4096)
  self.assertEqual(np.nanmax(yy),42);self.assertEqual(np.nanmin(yy),-30)
  self.assertTrue(np.isnan(yy).any());self.assertTrue(np.all(np.diff(xx)>0))
  self.assertEqual(y[12345],42);self.assertTrue(np.isnan(y[70000]))
 def test_sparse_tone_points_are_unchanged(self):
  from monitor.historico.v13.bode import render_envelope
  x=np.arange(25);y=np.sin(x);xx,yy=render_envelope(x,y)
  np.testing.assert_array_equal(xx,x);np.testing.assert_array_equal(yy,y)

class WavToBodeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PyQt6 import QtWidgets
  cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def test_all_bode_methods_can_start_with_idle_wav_selected(self):
  from unittest.mock import Mock
  from monitor.historico.v13.app import SerialMonitorWindow
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.generator_mode.setCurrentIndex(4)
   w.serial_worker=Mock();w.is_running=True;w._generator_state_known=True
   w._auto_apply_timer.stop();w._pulse_us_capable=True
   for index in range(3):
    with self.subTest(index=index):
     w._generator_requested=None
     w.spectral.select_bode(index);p=w.spectral.bode.panels[index]
     p.begin();self.assertTrue(p.active,p.status.text())
     self.assertNotEqual(p.config.mode,4)
     self.assertGreater(p.config.high-p.config.low,10) if index==0 else self.assertGreater(p.pulse_config.high-p.pulse_config.low,10)
     p.cancel()
  finally:w.serial_worker=None;w.close()
 def test_active_or_preparing_audio_is_not_mistaken_for_pending_acquisition(self):
  from unittest.mock import Mock
  from monitor.historico.v13.app import SerialMonitorWindow
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.generator_mode.setCurrentIndex(4);w.serial_worker=Mock();w._generator_state_known=True
   for state in ('_wav_active','_wav_preparing'):
    setattr(w,state,True)
    for index in range(3):
     w.spectral.select_bode(index);p=w.spectral.bode.panels[index]
     p.begin();self.assertFalse(p.active);self.assertIn('Detener la reproducción Wav',p.status.text())
    setattr(w,state,False)
   w.serial_worker.request_generator.assert_not_called()
  finally:w.serial_worker=None;w.close()
