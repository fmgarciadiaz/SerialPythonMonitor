"""Streaming recording regressions using real Qt controls and WAV readers."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
from PyQt6 import QtWidgets
from monitor.v13.app import SerialMonitorWindow
from monitor.v13.qt_environment import prepare_platform_plugins
from monitor.v13.receiver.unoq_acquisition import Configuration


class WaveRecordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare_platform_plugins()
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v13.app.usb_devices', return_value=[]):
            self.w = SerialMonitorWindow()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'capture.wav'
        self.w.serial_worker = MagicMock()
        self.w.applied_configuration = Configuration(14, 125000)
        self.w.record_format_combo.setCurrentText('WAV')
        self.w.record_dc_checkbox.setChecked(False)
        with patch.object(self.w, '_create_log_filename', return_value=self.path):
            self.w.start_recording()

    def tearDown(self):
        self.w.serial_worker = None
        self.w.close()
        self.temp.cleanup()

    def batch(self, start, count):
        return [{'Muestra': (start+i) & 0xffffffff, 'Tiempo (us)': ((start+i)*8) & 0xffffffff,
                 'ADC_IN': 0, 'ADC_OUT': 16383, 'V_IN': 0, 'V_OUT': 3.3} for i in range(count)]

    def read(self):
        with wave.open(str(self.path), 'rb') as stream:
            params = stream.getparams()
            samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, 2)
        return params, samples

    def test_stereo_endpoints_raw_rate_and_wrap_across_batches(self):
        self.assertFalse(self.w.record_format_combo.isEnabled())
        self.w.handle_batch(self.batch(0xfffffffe, 2))
        self.w.handle_batch(self.batch(0x100000000, 3))
        self.w.stop_recording()
        params, samples = self.read()
        self.assertEqual((params.nchannels, params.sampwidth, params.framerate, params.nframes), (2, 2, 125000, 5))
        np.testing.assert_array_equal(samples, np.tile([-32768, 32767], (5, 1)))
        self.assertTrue(self.w.record_format_combo.isEnabled())

    def test_gap_stops_without_writing_bad_batch_and_finalizes(self):
        self.w.handle_batch(self.batch(0, 2))
        with patch.object(QtWidgets.QMessageBox, 'critical') as critical:
            self.w.handle_batch(self.batch(3, 2))
        critical.assert_called_once()
        self.assertFalse(self.w.recording)
        self.assertIn('discontinuidad', self.w.record_status_label.text())
        self.assertEqual(self.read()[0].nframes, 2)

    def test_gap_within_batch_is_rejected(self):
        batch = self.batch(0, 3)
        batch[2]['Tiempo (us)'] += 8
        with patch.object(QtWidgets.QMessageBox, 'critical'):
            self.w.handle_batch(batch)
        self.assertEqual(self.read()[0].nframes, 0)

    def test_configuration_change_finalizes_existing_rate(self):
        self.w.handle_batch(self.batch(0, 4))
        self.w._acquisition_confirmed(16, 62500)
        self.assertFalse(self.w.recording)
        params, _ = self.read()
        self.assertEqual((params.framerate, params.nframes), (125000, 4))

    def test_write_error_closes_and_finalizes(self):
        self.w.handle_batch(self.batch(0, 2))
        with patch.object(self.w.record_wave, 'writeframesraw', side_effect=OSError('disco lleno')):
            with patch.object(QtWidgets.QMessageBox, 'critical'):
                self.w.handle_batch(self.batch(2, 2))
        self.assertFalse(self.w.recording)
        self.assertEqual(self.read()[0].nframes, 2)
        self.assertIsNone(self.w.record_file)

    def test_record_limit_finalizes_header(self):
        self.w.handle_batch(self.batch(0, 2))
        with patch('monitor.v13.app.time.perf_counter', return_value=self.w.record_start_time+30):
            self.w.handle_batch(self.batch(2, 2))
        self.assertFalse(self.w.recording)
        self.assertEqual(self.read()[0].nframes, 2)

    def test_demo_wav_declined_before_creating_file(self):
        self.w.stop_recording()
        self.path.unlink()
        self.w.demo_mode = True
        with patch.object(QtWidgets.QMessageBox, 'warning') as warning:
            self.w.start_recording()
        warning.assert_called_once()
        self.assertFalse(self.w.recording)
        self.assertFalse(self.path.exists())

    def test_window_close_finalizes(self):
        self.w.handle_batch(self.batch(0, 2))
        self.w.serial_worker = None
        self.w.close()
        self.assertEqual(self.read()[0].nframes, 2)

    def test_invalid_adc_rejected(self):
        batch = self.batch(0, 2)
        batch[0]['ADC_IN'] = 16384
        with patch.object(QtWidgets.QMessageBox, 'critical'):
            self.w.handle_batch(batch)
        self.assertFalse(self.w.recording)
        self.assertEqual(self.read()[0].nframes, 0)

    def test_idle_format_label_and_shared_numbering(self):
        self.w.stop_recording()
        self.w.record_format_combo.setCurrentText('CSV')
        self.w.record_format_combo.setCurrentText('WAV')
        self.assertEqual(self.w.record_status_label.text(), 'WAV: listo | máximo 30.0 s')
        with patch('monitor.v13.app.ROOT', Path(self.temp.name)):
            first = self.w._create_log_filename()
            self.assertTrue(first.name.endswith('_14bit_125kHz.wav'))
            self.assertNotIn('_001', first.name)
            first.with_suffix('.csv').touch()
            second = self.w._create_log_filename()
            self.assertTrue(second.name.endswith('_2.wav'))
            second.touch()
            third = self.w._create_log_filename()
            self.assertTrue(third.name.endswith('_3.wav'))

    def test_disconnect_finalizes(self):
        self.w.handle_batch(self.batch(0, 2))
        self.w.stop_input()
        self.assertFalse(self.w.recording)
        self.assertEqual(self.read()[0].nframes, 2)
