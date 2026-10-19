import os,struct,zlib,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.receiver.unoq_generator import GeneratorConfig,generator_request,generator_reply
class DutyTests(unittest.TestCase):
 def test_wire_defaults_round_trip_and_capabilities(self):
  for duty in (1,25,50,75,99):
   c=GeneratorConfig(frequency=5000000,duty=duty)
   req=generator_request(0x80000001,c)
   self.assertEqual(req[36],0 if duty==50 else duty)
   p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,9,0,972)
   struct.pack_into('<I',p,16,0x80000001);p[20]=2;p[22]=1;p[23]=3
   p[24:44]=p[44:64]=c.pack();p[64]=p[65]=req[36]
   struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
   reply=generator_reply(p);self.assertEqual(reply.active,c);self.assertTrue(reply.duty_capable)
 def test_effective_duty_preserves_frequency_and_rounds_resolution(self):
  self.assertEqual(GeneratorConfig(frequency=5000000,duty=25).effective_duty,25)
  self.assertEqual(GeneratorConfig(frequency=50000000,duty=1).effective_duty,5)
  self.assertEqual(GeneratorConfig(frequency=50000000,duty=99).effective_duty,95)
  for values in ({'duty':0},{'duty':100},{'duty':25,'wave':1},{'duty':25,'mode':1}):
   with self.assertRaises(ValueError):GeneratorConfig(**values)
 def test_gui_dial_is_only_for_continuous_square_and_old_q_stays_at_50(self):
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   self.assertEqual(w.generator_duty.value(),50)
   self.assertFalse(w.generator_duty_box.isEnabled())
   w._duty_capable=True;w._generator_availability();w.generator_duty_dial.setValue(25)
   self.assertEqual(w._generator_config().duty,25)
   w.generator_wave.setCurrentIndex(2)
   self.assertTrue(w.generator_duty_box.isHidden());self.assertEqual(w._generator_config().duty,50)
   w.generator_mode.setCurrentIndex(5);w.generator_mode.setCurrentIndex(0);w.generator_wave.setCurrentIndex(0)
   self.assertFalse(w.generator_duty_dial.isHidden());self.assertFalse(w.generator_duty.isHidden())
  finally:w.close()

 def test_offset_dial_readout_and_visibility_for_every_wave(self):
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v16.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   w.generator_offset_slider.setValue(150)
   self.assertEqual(w.generator_offset.value(),1.5)
   self.assertIn('1',w.generator_offset_value.text())
   self.assertEqual(w.generator_offset_slider.size(),w.wav_amplitude_dial.size())
   for wave in range(4):
    w.generator_wave.setCurrentIndex(wave)
    self.assertTrue(w.generator_offset.isHidden())
    self.assertFalse(w.generator_offset_box.isHidden())
   w.generator_mode.setCurrentIndex(5);self.assertTrue(w.generator_offset_box.isHidden())
   w.generator_mode.setCurrentIndex(0);self.assertFalse(w.generator_offset_box.isHidden())
   from PyQt6 import QtCore,QtTest
   QtTest.QTest.mouseDClick(w.generator_offset_slider,QtCore.Qt.MouseButton.LeftButton,pos=QtCore.QPoint(55,40))
   QtTest.QTest.mouseRelease(w.generator_offset_slider,QtCore.Qt.MouseButton.LeftButton,pos=QtCore.QPoint(55,40))
   self.assertEqual(w.generator_offset.value(),1.65)
  finally:w.close()
