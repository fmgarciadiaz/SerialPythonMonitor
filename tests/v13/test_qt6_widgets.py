"""Qt6-specific regressions that exercise real controls and rendering."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt6'
import unittest
from unittest.mock import patch
from PyQt6 import QtWidgets, QtGui, QtCore, QtTest
import pyqtgraph as pg
from monitor.v13.app import SerialMonitorWindow, OutputWorker, TimedBatch
from monitor.v13.qt_environment import prepare_platform_plugins

class Qt6WidgetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare_platform_plugins()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setStyle('Fusion')

    def setUp(self):
        with patch('monitor.v13.app.usb_devices', return_value=[]):
            self.window = SerialMonitorWindow()

    def tearDown(self):
        self.window.close()

    def test_single_connection_button_and_preparation_position(self):
        w = self.window
        w.show()
        self.app.processEvents()
        self.assertFalse(hasattr(w, 'autoload_checkbox'))
        self.assertFalse(hasattr(w, 'stop_serial_btn'))
        self.assertTrue(w.prepare_q_button.isVisible())
        self.assertEqual(w.prepare_q_button.geometry().y(), w.connect_button.geometry().y())
        for state, text in [('disconnected', 'Conectar'), ('connecting', 'Conectando…'), ('connected', 'Desconectar')]:
            w._set_connect_state(state)
            self.assertEqual(w.connect_button.text().strip(), text)
            self.assertFalse(w.connect_button.icon().isNull())
        w.demo_mode = True
        w._set_connect_state('connected')
        w.connect_button.click()
        self.assertFalse(w.demo_mode)
        self.assertEqual(w.connection_state, 'disconnected')

    def test_audio_amplitude_dial_updates_during_play(self):
        from unittest.mock import Mock
        w = self.window
        w.generator_mode.setCurrentIndex(4)
        w.show()
        self.app.processEvents()
        self.assertTrue(w.wav_amplitude_dial.isVisible())
        self.assertFalse(w.generator_amplitude.isVisible())
        w.serial_worker = Mock()
        w._wav_active = True
        w.wav_amplitude_dial.setValue(100)
        self.assertEqual(w.generator_amplitude.value(), 1)
        w.serial_worker.request_wav_levels.assert_called_with(1, 1.65)
        w.serial_worker.request_wav.assert_not_called()
        self.assertTrue(w._wav_active)
        w.serial_worker = None
        w._wav_active = False

    def test_run_restores_trigger_state_before_single(self):
        w = self.window
        for initial in (False, True):
            w.trigger_checkbox.setChecked(initial)
            w.arm_single_shot()
            self.assertTrue(w.trigger_checkbox.isChecked())
            w.arm_single_shot()
            w.run_stop_btn.setChecked(True)
            w.toggle_run_stop()
            self.assertEqual(w.trigger_checkbox.isChecked(), initial)
            self.assertEqual(w.trigger_enabled, initial)

    def test_backend_checkbox_and_channel_actions(self):
        w = self.window
        self.assertEqual(pg.Qt.QT_LIB, 'PyQt6')
        w.chk_auto_gap.setChecked(False)
        self.assertFalse(w.auto_gap_cut)
        w.chk_auto_gap.setChecked(True)
        self.assertTrue(w.auto_gap_cut)
        menu = w.channel_color_buttons['V_IN'].menu()
        self.assertIsInstance(menu.actions()[0], QtGui.QAction)
        menu.actions()[1].trigger()
        self.assertEqual(w.channel_colors['V_IN'], menu.actions()[1].data())
        self.assertEqual(sum(action.isChecked() for action in menu.actions()), 1)

    def test_custom_paint_and_time_controls(self):
        w = self.window
        w.resize(1500, 900)
        w.show()
        self.app.processEvents()
        self.assertFalse(w.grab().isNull())
        self.assertFalse(w.generator_wave.grab().isNull())
        w._acquisition_confirmed(16, 62500)
        w._on_xaxis_toggle(True)
        self.assertEqual(w.lbl_h_scale.decimals(), 1)
        self.assertEqual(w.lbl_h_scale.suffix(), ' ms')
        self.assertEqual(w.run_stop_btn.height(), 34)
        self.assertEqual(w.status_label.height(), 34)

    def test_worker_object_signal_queues_complete_batch_to_gui_and_csv(self):
        import csv
        import tempfile
        import threading
        from pathlib import Path
        w = self.window
        worker = OutputWorker(None, 0)
        delivered = []
        def consume(batch):
            delivered.append((batch, QtCore.QThread.currentThread()))
            w.handle_batch(batch)
        worker.batch_ready.connect(consume, QtCore.Qt.ConnectionType.QueuedConnection)
        published = []
        def produce():
            batch = TimedBatch([{'Muestra': i+1, 'Tiempo (us)': i*8,
                                'ADC_IN': i+100, 'V_IN': .5, 'ADC_OUT': i+200, 'V_OUT': 1.0}
                               for i in range(113)])
            published.append(batch)
            worker.batch_ready.emit(batch)
        w.demo_mode = True
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'queued.csv'
            with patch.object(w, '_create_log_filename', return_value=path):
                w.start_recording()
            thread = threading.Thread(target=produce)
            thread.start(); thread.join()
            for _ in range(100):
                if delivered:
                    break
                QtTest.QTest.qWait(10)
            w.stop_recording()
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(len(delivered), 1)
        self.assertIs(delivered[0][0], published[0])
        self.assertEqual(delivered[0][1], w.thread())
        self.assertGreater(published[0].published_at, 0)
        self.assertEqual(w.timed_batch_count, 1)
        self.assertEqual(w.sample_counter, 113)
        self.assertEqual(len(rows), 113)
        self.assertEqual(int(rows[-1]['Tiempo_us']), 896)
        self.assertEqual(int(rows[-1]['ADC_IN']), 212)

    def test_wav_buttons_follow_confirmed_playback(self):
        from monitor.v13.receiver.unoq_wav import Status,State
        w=self.window;w.generator_mode.setCurrentIndex(4)
        self.assertEqual(w.wav_play.width(),34)
        self.assertFalse(w.wav_play.icon().isNull())
        self.assertFalse(hasattr(w, "wav_stop"))
        w._wav_confirmed(Status(0x80000001,123,State.PLAYING,0,10,2000,480,3000,20000))
        self.assertTrue(w.wav_play.isEnabled())
        self.assertEqual(w.wav_play.toolTip(), "Detener WAV")
        w._wav_confirmed(Status(0x80000002,123,State.DONE,0,16,3000,3000,3000,20000))
        self.assertEqual(w.wav_play.toolTip(), "Reproducir WAV")

    def test_wav_selection_validates_and_displays_source_format(self):
        import tempfile
        from pathlib import Path
        import numpy as np
        from scipy.io import wavfile
        w = self.window
        w.generator_mode.setCurrentIndex(4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stereo.wav'
            wavfile.write(path,44100,np.zeros((4410,2),dtype=np.int16))
            with patch('monitor.v13.app.QtWidgets.QFileDialog.getOpenFileName',return_value=(str(path),'WAV')):
                w._choose_wav()
            self.assertTrue(w.wav_play.isEnabled())
            self.assertIn('44.1 kHz',w.generator_status.text())
            self.assertIn('16 bits',w.generator_status.text())
            self.assertIn('2 canales',w.generator_status.text())
            path.write_bytes(b'not a wav')
            with patch('monitor.v13.app.QtWidgets.QFileDialog.getOpenFileName',return_value=(str(path),'WAV')):
                w._choose_wav()
            self.assertFalse(w.wav_play.isEnabled())
            self.assertIn('WAV inválido',w.generator_status.text())
    def test_wav_locks_configuration_and_starts_run(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        w = self.window
        w.generator_mode.setCurrentIndex(4)
        w.wav_path='source.wav'
        w._wav_preparing=True
        w._sync_wav_transport()
        self.assertFalse(w.config_rate_combo.isEnabled())
        self.assertFalse(w.config_bits_combo.isEnabled())
        w._set_output_pending(False)
        self.assertFalse(w.config_rate_combo.isEnabled())
        worker=Mock()
        w.serial_worker=worker
        w._wav_target_worker=worker
        w.run_stop_btn.setChecked(False)
        w.toggle_run_stop()
        w.single_shot_armed=True
        w._wav_ready(SimpleNamespace(original_rate=44100,channels=2,duration=1,codes=[2048]))
        self.assertTrue(w.is_running)
        self.assertTrue(w.run_stop_btn.isChecked())
        self.assertFalse(w.single_shot_armed)
        w._wav_preparing=False
        w._wav_active=False
        w._sync_wav_transport()
        self.assertTrue(w.config_rate_combo.isEnabled())
        w.serial_worker=None

    def test_wav_rate_selector_tracks_firmware_capability_and_locks(self):
        from monitor.v13.receiver.unoq_wav import Status,State
        w=self.window
        w._wav_confirmed(Status(0x80000001,0,State.IDLE,0,16,0,0,0,20000,7))
        self.assertTrue(w.wav_rate.model().item(2).isEnabled())
        w._wav_active=True
        w._sync_wav_transport()
        self.assertFalse(w.wav_rate.isEnabled())
        w.wav_rate.setCurrentIndex(2)
        w._wav_confirmed(Status(0x80000002,0,State.IDLE,0,16,0,0,0,20000,1))
        self.assertEqual(w.wav_rate.currentData(),20000)
        self.assertFalse(w.wav_rate.model().item(1).isEnabled())
        self.assertFalse(w.wav_rate.model().item(2).isEnabled())

    def test_wav_rejects_unvalidated_adc125_combination(self):
        from unittest.mock import Mock
        from monitor.v13.receiver.unoq_acquisition import Configuration
        w=self.window
        w.wav_path='source.wav'
        w.serial_worker=Mock()
        w._wav_capable=True
        w.applied_configuration=Configuration(14,125000)
        w._play_wav()
        self.assertIn('100 kHz',w.generator_status.text())
        self.assertFalse(w._wav_preparing)
        w.serial_worker.request_wav.assert_not_called()
        w.serial_worker=None

    def test_finite_generator_modes_wait_for_disparar(self):
        from unittest.mock import Mock
        w=self.window
        worker=Mock()
        w.serial_worker=worker
        for mode in (1,2,3):
            worker.reset_mock()
            w.generator_mode.setCurrentIndex(mode)
            w.generator_duration.setValue(3)
            self.assertFalse(w._generator_timer.isActive())
            QtTest.QTest.qWait(300)
            worker.request_generator.assert_not_called()
            w.generator_restart.click()
            worker.request_generator.assert_called_once()
        w.serial_worker=None
