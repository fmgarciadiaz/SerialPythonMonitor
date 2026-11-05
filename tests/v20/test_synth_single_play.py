import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.receiver.unoq_acquisition import Configuration


class SynthSinglePlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v20.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.render_timer.stop()
        self.w.generator_mode.setCurrentIndex(5)
        self.w._auto_apply_timer.stop()
        self.requests=[]
        self.worker=NS(request_wav=lambda *a:self.requests.append(a),request_wav_levels=lambda *a:None)
        self.w.serial_worker=self.worker
        self.w._wav_capable=True;self.w._wav_active=False
        self.p=self.w.fm_panel

    def tearDown(self):
        self.w.serial_worker=None
        self.w.close();self.qt.processEvents()

    def test_one_click_waits_for_configuration_and_survives_idle_poll(self):
        self.w.output_pending=True
        self.w.applied_configuration=Configuration(8,1860465)
        self.p.toggle()
        self.assertEqual(self.p._start_phase,'waiting');self.assertEqual(self.requests,[])
        self.w.output_pending=False;self.w.applied_configuration=Configuration(8,40000)
        self.p._continue_start()
        self.assertEqual(len(self.requests),1);self.assertEqual(self.requests[0][0],1)
        source=self.p.source
        self.p.status(NS(state=0))
        self.assertIs(self.p.source,source);self.assertEqual(self.p._start_phase,'preparing')
        self.assertTrue(self.w._wav_active)
        self.p.status(NS(state=1,accepted=480,played=0,rate=40000))
        self.p.status(NS(state=0))
        self.assertIs(self.p.source,source)
        self.p._continue_start();self.assertEqual(len(self.requests),1)
        self.p.status(NS(state=2,accepted=960,played=480,rate=40000))
        self.assertEqual(self.p._start_phase,'idle');self.assertEqual(self.p.play.text(),'Stop')

    def test_second_click_cancels_waiting_instead_of_queuing_play(self):
        self.w.output_pending=True
        self.p.toggle();self.p.toggle()
        self.assertEqual(self.p._start_phase,'idle');self.assertFalse(self.p._start_timer.isActive())
        self.w.output_pending=False;self.p._continue_start()
        self.assertEqual(self.requests,[])

    def test_one_click_waits_for_previous_audio_stop(self):
        self.w.output_pending=False;self.w.applied_configuration=Configuration(8,40000)
        self.w._wav_active=True
        self.p.toggle()
        self.assertEqual([r[0] for r in self.requests],[3])
        self.assertEqual(self.p._start_phase,'waiting')
        self.w._wav_active=False;self.p.status(NS(state=3))
        self.p._continue_start()
        self.assertEqual([r[0] for r in self.requests],[3,1])
        source=self.p.source;self.p.status(NS(state=3))
        self.assertIs(self.p.source,source)

    def test_disconnect_does_not_start_on_replacement_worker(self):
        self.w.output_pending=True;self.p.toggle()
        self.w.serial_worker=NS();self.p._continue_start()
        self.assertEqual(self.p._start_phase,'idle');self.assertEqual(self.requests,[])

    def test_cancel_preparation_sends_stop_once(self):
        self.w.output_pending=False;self.w.applied_configuration=Configuration(8,40000)
        self.p.toggle();self.p.toggle()
        self.assertEqual([r[0] for r in self.requests],[1,3])
        self.assertEqual(self.p._start_phase,'idle')

    def test_actual_button_and_owner_ack_keep_loading_until_play_confirmed(self):
        self.w.output_pending=False;self.w.applied_configuration=Configuration(14,40000)
        self.p.play.click()
        self.assertEqual([request[0] for request in self.requests],[1])
        source=self.p.source
        self.assertIn('cargando',self.w.generator_status.text())
        for state,accepted,played in ((0,0,0),(1,480,0),(2,960,480)):
            self.w._wav_confirmed(NS(state=state,rates_mask=7,rate=20000,
                                     accepted=accepted,played=played,total=10000,reason=0))
            self.assertIs(self.p.source,source)
        self.assertIn('Activo',self.w.generator_status.text())
        self.assertEqual(self.p.play.text(),'Stop')

    def test_request_failure_is_visible_on_generator_status(self):
        self.w.output_pending=False;self.w.applied_configuration=Configuration(14,40000)
        def fail(*args):raise RuntimeError('offline BEGIN failure')
        self.worker.request_wav=fail
        self.p.play.click()
        self.assertIn('offline BEGIN failure',self.w.generator_status.text())
        self.assertEqual(self.p._start_phase,'idle')
