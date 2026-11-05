"""Exercise the real Qt retry timer without a board or receiver process."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import Mock,patch
from PySide6 import QtWidgets,QtTest
from monitor.v20.app import SerialMonitorWindow

class ThreadState:
    def __init__(self):self.running=True;self.deleted=0
    def isRunning(self):return self.running
    def quit(self):pass
    def deleteLater(self):self.deleted+=1

class DisconnectTimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        with patch.object(SerialMonitorWindow,'refresh_ports'):
            self.window=SerialMonitorWindow()
        self.window.render_timer.stop()
        self.thread=ThreadState();self.worker=Mock()
        self.window.serial_thread=self.thread;self.window.serial_worker=self.worker
    def tearDown(self):
        self.thread.running=False
        self.window.stop_input();self.window.close()
        self.window.deleteLater();self.app.processEvents()
    def test_repeated_stop_reuses_timer_and_releases_finished_worker(self):
        timer=self.window._disconnect_retry_timer
        self.assertIs(self.window.stop_input(),False)
        for _ in range(4):self.assertIs(self.window.stop_input(),False)
        self.assertIs(timer,self.window._disconnect_retry_timer)
        self.assertTrue(timer.isActive())
        self.thread.running=False;QtTest.QTest.qWait(160)
        self.assertIsNone(self.window.serial_worker);self.assertIsNone(self.window.serial_thread)
        self.assertEqual(self.thread.deleted,1);self.assertFalse(timer.isActive())
        self.assertFalse(self.window._disconnect_retry_pending)
    def test_nonwaiting_stop_does_not_schedule_retry(self):
        self.assertIs(self.window.stop_input(wait=False),False)
        self.assertFalse(self.window._disconnect_retry_timer.isActive())
        self.assertFalse(self.window._disconnect_retry_pending)
    def test_close_waits_for_worker_before_resuming(self):
        self.window._close_pending=True
        with patch.object(self.window,'close') as close:
            self.window.stop_input();self.assertFalse(close.called)
            self.thread.running=False;QtTest.QTest.qWait(160)
            close.assert_called_once()
            self.assertIsNone(self.window.serial_worker)
