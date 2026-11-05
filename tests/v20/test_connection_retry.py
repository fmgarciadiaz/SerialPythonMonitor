import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import unittest
from unittest.mock import patch
from PySide6 import QtCore,QtWidgets
from monitor.v20 import app as mod


class FinishedBeforeConnect(mod.OutputWorker):
    @QtCore.Slot()
    def run(self):
        # Same final notification as OutputWorker.run when setup exits early.
        self.finished.emit()


class ConnectionRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def until(self,condition):
        deadline=time.monotonic()+2
        while not condition() and time.monotonic()<deadline:
            self.qt.processEvents();time.sleep(.002)
        self.assertTrue(condition())

    def test_finished_before_connect_releases_ui_and_allows_retry(self):
        with patch.object(mod,'usb_devices',return_value=['fake-q']),patch.object(mod.list_ports,'comports',return_value=[]):
            w=mod.SerialMonitorWindow()
        w.render_timer.stop()
        self.until(lambda:w.refresh_button.isEnabled())
        try:
            with patch.object(mod,'OutputWorker',FinishedBeforeConnect):
                for _ in range(2):
                    w.connect_serial()
                    thread=w.serial_thread
                    self.until(lambda:w.serial_worker is None)
                    self.assertIsNone(w.serial_thread)
                    self.assertEqual(w.connection_state,'disconnected')
                    self.assertTrue(w.connect_button.isEnabled())
                    self.assertFalse(w._shutdown_status[0])
                    self.assertIn('sin confirmar',w._shutdown_status[1])
        finally:
            w.stop_input();w.close()

    def test_finished_from_old_thread_cannot_clear_new_attempt(self):
        with patch.object(mod,'usb_devices',return_value=[]),patch.object(mod.list_ports,'comports',return_value=[]):
            w=mod.SerialMonitorWindow()
        w.render_timer.stop()
        old=QtCore.QThread();current=QtCore.QThread();worker=object()
        old.finished.connect(w._receiver_thread_finished)
        w.serial_thread=current;w.serial_worker=worker
        try:
            old.finished.emit();self.qt.processEvents()
            self.assertIs(w.serial_thread,current)
            self.assertIs(w.serial_worker,worker)
        finally:w.serial_thread=None;w.serial_worker=None;w.close()

    def test_setup_exception_still_emits_finished(self):
        worker=mod.OutputWorker('fake',0);finished=[]
        worker.finished.connect(lambda:finished.append(True))
        with patch('monitor.v20.process_activity.acquisition_activity_mode',return_value='user'), \
             patch('monitor.v20.process_activity.MacActivity',side_effect=RuntimeError('setup failed')):
            with self.assertRaisesRegex(RuntimeError,'setup failed'):
                worker.run()
        self.assertEqual(finished,[True])


if __name__=='__main__':unittest.main()
