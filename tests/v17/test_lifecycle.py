import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch, MagicMock
from PyQt6 import QtWidgets
from monitor.v17.app import SerialMonitorWindow, QPreparationThread

class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
    def tearDown(self):
        self.w.serial_worker=None;self.w.serial_thread=None;self.w.close()
    def test_shutdown_keeps_live_thread_and_does_not_wait(self):
        worker=MagicMock();thread=MagicMock();thread.isRunning.return_value=True
        self.w.serial_worker=worker;self.w.serial_thread=thread
        with patch('monitor.v17.app.QtCore.QTimer.singleShot') as timer:
            self.assertFalse(self.w.stop_input())
            self.assertIs(self.w.serial_thread,thread)
            thread.wait.assert_not_called();thread.deleteLater.assert_not_called()
            self.assertFalse(self.w.connect_button.isEnabled())
            callback=timer.call_args.args[1]
            thread.isRunning.return_value=False;callback()
            thread.deleteLater.assert_called_once()
            self.assertIsNone(self.w.serial_thread)
            self.assertTrue(self.w.connect_button.isEnabled())
    def test_close_waits_asynchronously_for_wav_preparation(self):
        thread=MagicMock();thread.isRunning.return_value=True;self.w._wav_thread=thread
        event=MagicMock()
        with patch('monitor.v17.app.QtCore.QTimer.singleShot'):
            self.w.closeEvent(event)
        event.ignore.assert_called_once();event.accept.assert_not_called();thread.wait.assert_not_called()
        thread.isRunning.return_value=False
    def test_preparation_watchdog_reports_unknown_state(self):
        thread=QPreparationThread('q');thread.TIMEOUT_SECONDS=0
        result=[];thread.result.connect(lambda success,text:result.append((success,text)))
        process=MagicMock();process.poll.return_value=None
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder, patch('monitor.v17.app.ROOT',Path(folder)), patch('subprocess.Popen',return_value=process), patch('monitor.v17.app.stop_process_tree') as stop:
            thread.run()
        stop.assert_called_once_with(process)

        self.assertFalse(result[0][0]);self.assertIn('sin confirmar',result[0][1])

    def test_shutdown_failure_is_reported_even_after_stop(self):
        from monitor.v17.app import OutputWorker
        from monitor.v17.receiver.unoq_switch import Mode
        worker=OutputWorker('q',Mode.SPI);worker.stop()
        receiver=MagicMock();receiver.shutdown_output.side_effect=RuntimeError('ACK ausente')
        results=[];worker.shutdown_confirmed.connect(lambda ok,text:results.append((ok,text)))
        with self.assertRaisesRegex(RuntimeError,'ACK ausente'):worker._shutdown_receiver(receiver)
        receiver.close.assert_called_once()
        self.assertFalse(results[0][0]);self.assertIn('sin confirmar',results[0][1])
        self.w._output_shutdown_result(*results[0]);self.w.stop_input()
        self.assertIn('sin confirmar',self.w.status_label.text())
