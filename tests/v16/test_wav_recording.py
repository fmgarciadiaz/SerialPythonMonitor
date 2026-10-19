import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import io, unittest, wave
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.receiver.unoq_acquisition import Configuration

class WavRecordingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.v16.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):self.w.record_wave=None;self.w.close()
 def test_gate_and_csv_fallback(self):
  self.w.record_format_combo.setCurrentText('WAV')
  for bits,rate,allowed in ((14,40000,True),(8,1221374,False),(16,44101,True),(16,48004,True),(16,76226,True)):
   self.w.applied_configuration=Configuration(bits,rate);self.w._sync_record_availability()
   self.assertEqual(self.w.record_btn.isEnabled(),allowed)
  for bits in (8,10,12,14,16):
   for rate in (1000,5000,10000,20000,31250,40000):
    self.w.applied_configuration=Configuration(bits,rate);self.w._sync_record_availability()
    self.assertTrue(self.w.record_btn.isEnabled(),(bits,rate))
  self.w.demo_mode=True;self.w._sync_record_availability();self.assertFalse(self.w.record_btn.isEnabled())
  self.w.record_format_combo.setCurrentText('CSV');self.assertTrue(self.w.record_btn.isEnabled())
 def test_native_audio_file_and_discontinuity(self):
  profiles=[(bits,rate) for bits in (8,10,12,14,16) for rate in (1000,5000,10000,20000,31250,40000)]+[(16,44101),(16,48004),(16,76226)]
  for bits,rate in profiles:
   c=Configuration(bits,rate);self.w.applied_configuration=c
   stream=io.BytesIO();writer=wave.open(stream,'wb');writer.setparams((2,2,rate,0,'NONE','not compressed'))
   self.w.record_file=stream;self.w.record_wave=writer;self.w.record_previous=None;self.w.record_rows=0;self.w.record_dc_filter=None
   def batch(start,n):return [{'Muestra':i,'Tiempo (us)':i*c.dt_us,'CH1':1.65,'CH2':2.0} for i in range(start,start+n)]
   self.w._write_wave_batch(batch(0,64));self.w._write_wave_batch(batch(64,64))
   with self.assertRaisesRegex(ValueError,'discontinuidad'):self.w._write_wave_batch(batch(129,2))
   writer.close();self.w.record_wave=None;self.w.record_file=None;stream.seek(0)
   with wave.open(stream,'rb') as reader:
    self.assertEqual(reader.getframerate(),rate);self.assertEqual(reader.getnchannels(),2)
    self.assertEqual(reader.getsampwidth(),2);self.assertEqual(reader.getnframes(),128);self.assertEqual(len(reader.readframes(128)),512)
