"""Catalogue presentation with private in-memory profiles; never Q."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver import unoq_native
from monitor.v18 import app as app_module,rate_catalog
ROOT=Path(__file__).resolve().parents[3]
class RateCatalogGuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  path=ROOT/'experimentos/fs_max_v18';private=json.loads((path/'catalog/candidate_profiles.json').read_text())
  self.profiles=unoq_native.PROFILES+tuple(dict(p,internal_only=False,purpose='audio' if p.get('nominal_rate') else 'intermediate',validation='60s') for p in private)
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'catalog.json';self.path.write_text((path/'audio_catalog/catalog.proposed.json').read_text())
  self.patches=[patch.object(unoq_native,'PROFILES',self.profiles),patch.object(app_module,'RATES',tuple(sorted(set(app_module.RATES)|{160000000//p['ticks'] for p in private}))),patch.object(rate_catalog,'_PATH',self.path),patch('monitor.v18.app.usb_devices',return_value=[]),patch('monitor.v18.app.list_ports.comports',return_value=[])]
  for p in self.patches:p.start()
  self.window=SerialMonitorWindow()
 def tearDown(self):
  self.window.close();self.app.processEvents()
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_audio_labels_and_actual_rate_tooltips(self):
  w=self.window
  for bits in (8,10,12,14,16):
   w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(bits))
   for rate in (44101,48004,95980):
    i=w.config_rate_combo.findData(rate);self.assertGreaterEqual(i,0)
    self.assertFalse(w.config_rate_combo.view().isRowHidden(i))
    self.assertNotIn('≈',w.config_rate_combo.itemText(i))
    self.assertIn('Tasa real:',w.config_rate_combo.itemData(i,3))
   i=w.config_rate_combo.findData(192076)
   self.assertEqual(w.config_rate_combo.view().isRowHidden(i),bits==16)
 def test_maximum_tooltip_separates_current_audio_from_historical_headroom(self):
  w=self.window;w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(8))
  i=w.config_rate_combo.findData(1860465);tooltip=w.config_rate_combo.itemData(i,3)
  self.assertIn('RADIO/A0: prueba funcional de 120 s',tooltip)
  self.assertIn('Dibujo visible: comprobado',tooltip)
  self.assertIn('Holgura con RADIO/A0: sin medición registrada',tooltip)
  self.assertNotIn('margen validado',tooltip)
 def test_historical_rate_is_accessible_and_not_hidden_while_selected(self):
  w=self.window;w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(8))
  i=w.config_rate_combo.findData(1600000);self.assertTrue(w.config_rate_combo.view().isRowHidden(i))
  w._show_all_rates=True;w._destination_changed();self.assertFalse(w.config_rate_combo.view().isRowHidden(i))
  w.config_rate_combo.setCurrentIndex(i);w._show_all_rates=False;w._destination_changed()
  self.assertFalse(w.config_rate_combo.view().isRowHidden(i));self.assertEqual(w.config_rate_combo.currentData(),1600000)
 def test_single_audio_96_only_for_16_bits_and_uniform_upper_extension(self):
  from monitor.v18.receiver.unoq_acquisition import Configuration
  self.assertEqual(Configuration(16,95980).channels,1)
  for bits in (8,10,12,14):self.assertEqual(Configuration(bits,95980).channels,2)
  with self.assertRaises(ValueError):Configuration(16,192076)

 def test_audio_wav_recording_uses_actual_integer_rate_and_channel_count(self):
  import io,wave,time,numpy as np
  from monitor.v18.receiver.unoq_acquisition import Configuration
  from monitor.v18.numeric_batch import NumericBatch,SampleClock
  from types import SimpleNamespace
  for bits,rate in ((8,44101),(10,48004),(12,95980),(14,192076),(16,95980)):
   config=Configuration(bits,rate);n=128
   raw=np.zeros((n,4),dtype=np.uint32);raw[:,0]=np.arange(n)*config.period
   raw[:,1]=raw[:,2]=config.maximum//2;raw[:,3]=np.arange(n)
   batch=NumericBatch(raw,config.maximum,SampleClock(config.timestamp_hz),config.channels)
   sink=io.BytesIO();writer=wave.open(sink,'wb');writer.setparams((config.channels,2,config.rate,0,'NONE','not compressed'))
   owner=SimpleNamespace(applied_configuration=config,record_wave=writer,record_previous=None,record_dc_filter=None,record_rows=0,record_last_flush_time=time.perf_counter(),record_file=sink)
   SerialMonitorWindow._write_wave_batch(owner,batch);writer.close()
   with wave.open(io.BytesIO(sink.getvalue()),'rb') as reader:
    self.assertEqual(reader.getframerate(),config.rate)
    self.assertEqual(reader.getnchannels(),config.channels)
    self.assertEqual(reader.getnframes(),n)
   self.window.applied_configuration=config
   self.assertTrue(self.window._wav_recording_allowed())
