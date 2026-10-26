import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets,QtCore
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.radio_fft_crop import columns,crop_arrays,frequency_at

class RadioCropMathTests(unittest.TestCase):
 def test_sorted_columns_remove_gaps_and_keep_sidebands(self):
  layout=columns([{'frequency':700000},{'frequency':500000}],1600000,8000)
  self.assertEqual([c.carrier for c in layout],[500000,700000])
  f=np.arange(0,800001,1000);y=f.copy()
  x,values=crop_arrays(f,y,layout)
  finite=np.isfinite(values)
  self.assertTrue(np.all(((values[finite]>=496000)&(values[finite]<=504000))|((values[finite]>=696000)&(values[finite]<=704000))))
  self.assertEqual(frequency_at(layout,.5),500000)
  self.assertIsNone(frequency_at(layout,1.04))
  self.assertTrue(np.all(np.diff(x)>=0));self.assertEqual(np.isnan(values).sum(),4)
 def test_upper_zone_alias_reverses_spectrum_but_labels_real_rf(self):
  layout=columns([{'frequency':1100000,'suggested_bandwidth':10000}],1600000,8000,True)
  f=np.arange(0,800001,1000);x,y=crop_arrays(f,f,layout)
  values=y[np.isfinite(y)]
  self.assertEqual(list(values),list(np.arange(505000,494999,-1000)))
  self.assertEqual(frequency_at(layout,0),1095000)
  self.assertEqual(frequency_at(layout,1),1105000)
 def test_empty_duplicate_or_out_of_band_candidates(self):
  self.assertFalse(columns([],1600000,8000))
  self.assertFalse(columns([{'frequency':799000}],1600000,8000))
  self.assertEqual(len(columns([{'frequency':500000},{'frequency':500000}],1600000,8000)),1)

class RadioCropGuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  self.patches=[patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[])]
  for p in self.patches:p.start()
  self.w=SerialMonitorWindow();self.w.applied_configuration=Configuration(8,1600000)
  self.d=self.w.spectral;self.d.channels[0].setCurrentText('CH1');self.d.channels[1].setCurrentText('Ninguno')
  self.d.set_mode(1);self.d.fft_mode.setCurrentText('Radio')
 def tearDown(self):
  self.w.close();self.app.processEvents()
  for p in reversed(self.patches):p.stop()
 def scan(self):
  self.w.radio_candidates=[dict(frequency=500000),dict(frequency=700000)]
  self.d.refresh_radio_overlay()
 def draw(self):
  f=np.linspace(0,800000,2049);v=np.sin(f/2000)
  self.d._draw_fft_arrays(self.w,1600000,[v,None],f,'Spectre')
  return f,v
 def test_disabled_without_scan_and_restores_full_axis(self):
  self.assertFalse(self.d.radio_crop.isEnabled());self.scan()
  self.assertTrue(self.d.radio_crop.isEnabled());self.d.radio_crop.setChecked(True);f,v=self.draw()
  self.assertTrue(self.d.radio_crop_active(0))
  cache=self.d._fft_trace_cache[0]
  self.assertLess(cache[1][-1],3)
  self.assertEqual(self.d.plots[0].getAxis('bottom').labelUnits,'')
  self.d.radio_crop.setChecked(False);self.draw()
  np.testing.assert_array_equal(self.d._fft_trace_cache[0][1],f)
  self.assertEqual(self.d.plots[0].getAxis('bottom').labelUnits,'Hz')
 def test_unchecking_restores_cached_full_spectrum_while_paused(self):
  self.scan();f,v=self.draw();self.d.radio_crop.setChecked(True)
  self.assertLess(self.d._fft_trace_cache[0][1][-1],3)
  self.d.radio_crop.setChecked(False)
  np.testing.assert_array_equal(self.d._fft_trace_cache[0][1],f)
 def test_click_column_tunes_real_station_and_gap_does_nothing(self):
  from types import SimpleNamespace
  self.scan();self.d.radio_crop.setChecked(True);self.draw()
  self.w.radio_frequency.setRange(1,800)
  view=self.d.plots[0].getViewBox()
  for x,expected in ((1.58,700),(1.1,700),(.1,500),(.9,500),(1.9,700),(1.04,700)):
   point=view.mapViewToScene(QtCore.QPointF(x,0))
   event=SimpleNamespace(button=lambda:QtCore.Qt.MouseButton.LeftButton,scenePos=lambda:point,accept=lambda:None)
   self.d._radio_fft_clicked(event)
   self.assertEqual(self.w.radio_frequency.value(),expected)
 def test_clearing_scan_unchecks_and_disables(self):
  self.scan();self.d.radio_crop.setChecked(True)
  self.w.radio_candidates=[];self.d.refresh_radio_overlay()
  self.assertFalse(self.d.radio_crop.isChecked());self.assertFalse(self.d.radio_crop.isEnabled())
 def test_log_setting_is_preserved_but_cut_axis_is_linear(self):
  self.d.log_frequency.setChecked(True);self.scan();self.d.radio_crop.setChecked(True);self.draw()
  self.assertFalse(self.d.plots[0].getAxis('bottom').logMode)
  self.d.radio_crop.setChecked(False);self.draw()
  self.assertTrue(self.d.log_frequency.isChecked());self.assertTrue(self.d.plots[0].getAxis('bottom').logMode)
 def test_labels_thin_and_return_on_zoom_or_resize_without_new_data(self):
  self.w.radio_candidates=[dict(frequency=100000+i*20000) for i in range(30)]
  self.d.refresh_radio_overlay();self.d.radio_crop.setChecked(True);self.draw()
  axis=self.d.plots[0].getAxis('bottom')
  full=axis.tickValues(0,32.4,300)[0][1]
  wide=axis.tickValues(0,32.4,2400)[0][1]
  zoomed=axis.tickValues(10.8,16.2,300)[0][1]
  self.assertLess(len(full),len(wide));self.assertEqual(len(wide),30)
  self.assertEqual(len(zoomed),5)
  self.assertTrue(all(10.8<=x<=16.2 for x in zoomed))
  self.assertEqual(axis.tickStrings(zoomed,1,1),['300,0','320,0','340,0','360,0','380,0'])
  self.d.radio_crop.setChecked(False)
  self.assertEqual(getattr(axis,'tick_rotation',0),0)
 def test_radio_plots_share_height_with_different_axis_labels(self):
  self.d.channels[1].setCurrentText('RADIO')
  self.scan();self.d.radio_crop.setChecked(True);self.draw()
  self.d.widget.resize(900,700);self.d.widget.show()
  for _ in range(5):self.app.processEvents()
  heights=[p.geometry().height() for p in self.d.plots]
  self.assertAlmostEqual(heights[0],heights[1],delta=2)
 def test_cursor_reports_real_frequency_and_separate_state(self):
  self.scan();self.d.radio_crop.setChecked(True);self.draw()
  c=self.w.scope_cursors;c.analysis_changed();c.attach(0,self.d.plots[0])
  c.states[0].x=.5;c.states[0].y=-20
  self.assertEqual(c.read(0),(500000,-20))
  self.assertEqual(c._analysis_key,(1,'Radio recortada'))
