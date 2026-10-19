"""Run after integration: user-entered intermediates and per-wave UI bounds."""
import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','minimal')
from unittest.mock import patch
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.app import QtWidgets,SerialMonitorWindow
class ExtendedGeneratorTests(unittest.TestCase):
 def test_contract_intermediates_and_boundaries(self):
  for wave,limit in ((0,200000),(1,150000),(2,50000),(3,50000),(4,50000)):
   for hz in (12345.678,limit):GeneratorConfig(wave=wave,frequency=round(hz*1000),final_frequency=round(hz*1000))
   with self.assertRaises(ValueError):GeneratorConfig(wave=wave,frequency=limit*1000+1)
 def test_ui_wave_ranges_and_intermediate_precision(self):
  app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
  try:
   for wave,limit in ((0,200000),(1,150000),(2,50000)):
    w.generator_wave.setCurrentIndex(wave);w._generator_availability()
    self.assertEqual(w.generator_frequency.maximum(),limit)
    self.assertEqual(w.generator_final_frequency.maximum(),limit)
    w.generator_frequency.setValue(12345.678);self.assertEqual(w.generator_frequency.value(),12345.678)
    w.generator_frequency_dial.setValue(1000);self.assertEqual(w.generator_frequency.value(),limit)
   w.generator_wave.setCurrentIndex(1);w.generator_frequency.setValue(123456)
   self.assertEqual(w._generator_config().frequency,123456000)
  finally:w.close();app.processEvents()
if __name__=='__main__':unittest.main()
