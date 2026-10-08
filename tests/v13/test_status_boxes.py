import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PyQt6 import QtWidgets
from monitor.historico.v13.app import SerialMonitorWindow

class StatusBoxTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
 def setUp(self):
  with patch('monitor.historico.v13.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
 def tearDown(self):self.w.close()
 def test_connection_and_generator_messages_reach_uniform_top_boxes(self):
  w=self.w;w.status_label.setText('Activo · SPI · 14 bits · 40 kHz')
  w.generator_status.setText('Preparando audio mono para reproducción')
  self.assertEqual(w.acquisition_status_box.value.text(),'Activo')
  self.assertIn('40 kHz',w.acquisition_status_box.toolTip())
  self.assertEqual(w.generator_status_box.value.text(),w.generator_status.text())
  self.assertTrue(w.status_label.isHidden());self.assertTrue(w.generator_status.isHidden())
  self.assertEqual([box.height() for box in (w.acquisition_status_box,w.generator_status_box,w.analysis_status_box)],[34]*3)
 def test_bode_state_and_coverage_are_centralized_without_inactive_messages(self):
  w=self.w;w.spectral.select_bode(2);p=w.spectral.bode.panels[2]
  p.result=[(20,0,0),(5000,-3,-30)];p.draw();p.status.setText('Captura completa')
  self.assertEqual(w.analysis_status_box.value.text(),'Bode Chirp · Captura completa')
  self.assertIn('Ganancia: 2/2',w.analysis_status_box.toolTip())
  self.assertTrue(p.status.isHidden());self.assertTrue(p.coverage.isHidden())
  w.spectral.bode.panels[0].status.setText('Error de otro panel')
  self.assertNotIn('Error',w.analysis_status_box.value.text())
 def test_wav_layout_does_not_restore_side_status(self):
  w=self.w
  for index in (4,0,2):
   w.generator_mode.setCurrentIndex(index)
   self.assertTrue(w.generator_status.isHidden())
   self.assertEqual(w.generator_panel.layout().indexOf(w.generator_status),-1)
 def test_fft_and_trigger_waiting_states_are_preserved(self):
  w=self.w;w.spectral.set_mode(1);w.spectral.info.setText('Esperando frecuencia de adquisición…')
  self.assertIn('Esperando',w.analysis_status_box.value.text())
  self.assertTrue(w.spectral.info.isHidden())
  w.trigger_enabled=True;w.is_running=True
  w.trigger_status_label.setText('● Esperando disparo (Normal)…')
  self.assertEqual(w.acquisition_status_box.value.text(),'Esperando trigger')
