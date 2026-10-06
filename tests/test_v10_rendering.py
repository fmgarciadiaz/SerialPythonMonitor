import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from collections import deque
from unittest.mock import patch
import numpy as np
from PyQt5 import QtWidgets
from monitor.historico.v10.app import SerialMonitorWindow,VISIBLE_SAMPLES_MAX,MAX_BUFFER_SAMPLES

class DisplayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.historico.v10.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):self.w.close()
 def test_recent_and_historical_windows_match(self):
  values=deque(range(1000))
  for start,end in [(0,20),(800,900),(999,1000),(500,500)]:
   np.testing.assert_array_equal(self.w._window_values(values,start,end),np.arange(start,end))
 def test_dense_steps_keep_peaks_without_false_gaps(self):
  x=np.arange(10000,dtype=float);y=np.zeros(10000);y[1234]=10;y[5678]=-7
  self.w.trace_mode='Escalón';xp,yp=self.w._display_trace(x,y,0,10000,100)
  self.assertLessEqual(len(xp),801);self.assertEqual(max(yp),10);self.assertEqual(min(yp),-7)
  self.assertFalse(np.isnan(yp).any());self.assertTrue(np.all(np.diff(xp)>=0))
  np.testing.assert_array_equal(y[[1234,5678]],[10,-7])
 def test_zoom_restores_all_step_vertices_and_real_gap_remains(self):
  self.w.trace_mode='Escalón';self.w.auto_gap_cut=True
  x=np.arange(20,dtype=float);y=np.arange(20,dtype=float)
  xp,yp=self.w._display_trace(x,y,0,20,100)
  self.assertEqual(len(xp),39)
  x[10:]+=100
  xp,yp=self.w._display_trace(x,y,0,120,2)
  self.assertTrue(np.isnan(yp).any())
 def test_horizontal_range_has_four_seconds_at_max_rate(self):
  self.assertEqual(VISIBLE_SAMPLES_MAX,250000);self.assertGreater(MAX_BUFFER_SAMPLES,2*VISIBLE_SAMPLES_MAX)
  self.assertEqual(self.w.dial_h_scale.maximum(),250000)
  self.assertEqual(self.w.dial_h_pos.minimum(),-250000)

 def test_detail_slider_restores_full_trace_in_stop_without_moving_capture(self):
  w=self.w;w.is_running=False;w.sample_counter=123
  w._update_curve_items(['V_IN'])
  x=np.arange(10000,dtype=float);y=np.sin(x/10);y[1234]=4
  w.plot_widget.setXRange(0,10000,padding=0)
  w._last_display_frame=(x,{'V_IN':y},('V_IN',))
  w.detail_slider.setValue(0)
  small=len(w.line_items['V_IN'].getData()[0])
  self.assertEqual(max(w.line_items['V_IN'].getData()[1]),4)
  w.detail_slider.setValue(100)
  full=len(w.line_items['V_IN'].getData()[0])
  self.assertEqual(full,19999);self.assertLess(small,full)
  self.assertEqual(w.detail_value_label.text(),'Completo')
  self.assertFalse(w.is_running);self.assertEqual(w.sample_counter,123)
  self.assertEqual(y[1234],4)
  self.assertTrue(w.temporal_settings.isAncestorOf(w.detail_slider))

class HistoryTests(unittest.TestCase):
 def test_wrap_oversize_batches_and_frozen_window(self):
  from monitor.historico.v10.history import SampleHistory
  h=SampleHistory(7);reference=deque(maxlen=7)
  for batch in ([1,2,3],[4,5,6,7,8],list(range(20)),[30,31]):
   h.extend(batch);reference.extend(batch)
   np.testing.assert_array_equal(h.window(0,len(h)),list(reference))
   self.assertEqual(h[-1],reference[-1]);self.assertEqual(h[0],reference[0])
  frozen=h.window(0,len(h));expected=frozen.copy();h.extend(range(100,120))
  np.testing.assert_array_equal(frozen,expected)
  np.testing.assert_array_equal(h[::-1],list(reversed(h)))
  h.clear();self.assertEqual(len(h),0)
 def test_batch_ingestion_retains_all_samples_and_missing_columns(self):
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.historico.v10.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.handle_batch([{'V_IN':1,'Tiempo (us)':16},{'V_IN':2,'Tiempo (us)':32,'extra':5}])
   self.assertEqual(w.sample_counter,2)
   np.testing.assert_array_equal(w.series['V_IN'].window(0,2),[1,2])
   np.testing.assert_array_equal(w.series['extra'].window(0,2),[0,5])
   np.testing.assert_array_equal(w.series['V_OUT'].window(0,2),[0,0])
  finally:w.close()

class WorkerStartupTests(unittest.TestCase):
 def test_previous_hardware_profile_is_not_published_during_connection(self):
  from monitor.historico.v10.app import OutputWorker
  from transport.unoq_acquisition import Configuration
  from unittest.mock import MagicMock
  worker=OutputWorker('q',0,config=Configuration(10,1000));batches=[]
  worker.batch_ready.connect(batches.append)
  class Receiver:
   def __init__(self,connection,collect,*args):self.collect=collect;self.config=Configuration(14,62500)
   def configure(self,config):
    self.collect([(16,16383,0,100)]) # profile left active by the previous client
    self.config=config;self.on_configuration(config)
   def select(self,*args):pass
   def generator(self,*args):self.last_generator_poll=__import__("time").monotonic()
   def pump(self):self.collect([(1000,1023,0,0)]);worker.stop()
   def close(self):pass
  import itertools
  with patch('monitor.historico.v10.app.Connection',return_value=MagicMock()),patch('monitor.historico.v10.app.OutputReceiver',Receiver),patch('monitor.historico.v10.app.time.monotonic',side_effect=itertools.count(step=.1).__next__):worker.run()
  self.assertEqual(len(batches),1);self.assertEqual(len(batches[0]),1)
  self.assertEqual(batches[0][0]['Tiempo (us)'],1000)
  self.assertEqual(batches[0][0]['V_IN'],3.3)
