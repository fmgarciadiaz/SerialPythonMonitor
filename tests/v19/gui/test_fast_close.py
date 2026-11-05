import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch,MagicMock
from PySide6 import QtWidgets
from monitor.v19.app import SerialMonitorWindow,OutputWorker

class FastCloseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_window_hides_before_waiting_for_confirmed_worker_shutdown(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        w.show();self.app.processEvents()
        with patch.object(w,'stop_input',return_value=False):
            w.close()
            self.assertFalse(w.isVisible());self.assertTrue(w._close_pending)
            self.assertFalse(w.render_timer.isActive())
        w.close();self.assertFalse(w._close_pending)
    def test_stop_immediately_cancels_child_without_waiting_for_parent_loop(self):
        owner=MagicMock();owner.running=True
        OutputWorker.stop(owner)
        self.assertFalse(owner.running)
        owner._receiver_process.submit.assert_called_once_with('shutdown')

    def test_close_during_wav_preparation_waits_and_ignores_late_audio(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        w._wav_thread=MagicMock();w._wav_thread.isRunning.return_value=True
        w.show();self.app.processEvents()
        try:
            with patch('monitor.v19.app.QtCore.QTimer.singleShot') as retry:
                w.close()
                self.assertTrue(w._wav_cancelled)
                self.assertTrue(w._close_pending)
                self.assertFalse(w.isVisible())
                w._wav_thread.quit.assert_called_once()
                retry.assert_called_once_with(100,w.close)
            source=MagicMock()
            with patch.object(w,'serial_worker') as worker:
                w._wav_ready(source)
                worker.request_wav.assert_not_called()
            w._wav_thread.isRunning.return_value=False
            w.close()
            self.assertFalse(w._close_pending)
        finally:
            w._wav_thread.isRunning.return_value=False;w.serial_worker=None;w.close()

    def test_finished_wav_preparations_release_thread_and_close_with_none(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            for _ in range(10):
                thread=MagicMock();w._wav_thread=thread;w._wav_preparing=True
                w._wav_prepared()
                thread.deleteLater.assert_called_once()
                self.assertIsNone(w._wav_thread);self.assertFalse(w._wav_preparing)
            w.close();self.assertFalse(w._close_pending)
        finally:w.close()

    def test_cancelled_worker_cannot_create_new_dsp_or_synth_processes(self):
        from concurrent.futures import CancelledError
        from monitor.v19.fm_source import FMSource
        worker=OutputWorker('fake',0);worker.running=False
        with patch('monitor.v19.app.ProcessPoolExecutor') as process:
            with self.assertRaises(CancelledError):worker._ensure_process()
            with self.assertRaises(CancelledError):worker._prepare_live_audio(FMSource())
            process.assert_not_called()
