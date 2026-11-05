"""A stream error must resume a close already waiting on US Scan restoration."""
import os
import unittest
from unittest.mock import Mock,patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtTest,QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.radio_multiscan import MultirateScan


class ThreadState:
    def __init__(self):self.running=True
    def isRunning(self):return self.running
    def quit(self):pass
    def deleteLater(self):pass


class ScanErrorCloseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_eof_after_close_waits_for_scan_then_releases_worker(self):
        with patch.object(SerialMonitorWindow,'refresh_ports'):
            w=SerialMonitorWindow()
        thread=ThreadState();worker=Mock()
        try:
            w.render_timer.stop();w.show();self.app.processEvents()
            w.serial_thread=thread;w.serial_worker=worker
            scan=MultirateScan(w);w._radio_multiscan=scan
            scan.active=True;scan.restoring=True;scan.restore_confirmed=False
            scan.original=w.applied_configuration;scan.widgets=[];scan.enabled=[]
            scan.timer.start()
            w.close()
            self.assertTrue(w._close_pending)
            self.assertTrue(scan.active)
            self.assertFalse(w._disconnect_retry_timer.isActive())

            with patch.object(w,'_save_delivery_failure'),patch.object(QtWidgets.QMessageBox,'critical') as modal:
                w._on_worker_error('El Q cerró el flujo.')
            modal.assert_not_called()
            self.assertFalse(scan.active)
            self.assertFalse(scan.restore_confirmed)
            self.assertIn('restauración no confirmada',scan.error)
            self.assertFalse(scan.timer.isActive())
            self.assertTrue(w._disconnect_retry_timer.isActive())
            worker.stop.assert_called()

            thread.running=False
            QtTest.QTest.qWait(180)
            self.assertIsNone(w.serial_worker)
            self.assertIsNone(w.serial_thread)
            self.assertFalse(w._close_pending)
            self.assertFalse(w.isVisible())
        finally:
            thread.running=False
            w.stop_input();w.close();w.deleteLater();self.app.processEvents()


if __name__=='__main__':unittest.main()
