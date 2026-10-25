import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch,MagicMock
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow,OutputWorker

class FastCloseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_window_hides_before_waiting_for_confirmed_worker_shutdown(self):
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
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

