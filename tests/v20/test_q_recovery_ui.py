import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import time
from unittest.mock import patch
from PySide6 import QtCore,QtWidgets
from monitor.v20 import app as mod


class FakeThread(QtCore.QObject):
    progress=QtCore.Signal(str)
    result=QtCore.Signal(bool,str)
    finished=QtCore.Signal()
    def __init__(self,serial,parent=None,*,recovery=False):
        super().__init__(parent);self.recovery=recovery;self.active=False
    def start(self):self.active=True
    def isRunning(self):return self.active


class RecoveryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_separate_action_busy_guards_and_unlock_retry(self):
        for patcher in (patch.object(mod,'usb_devices',return_value=[]),patch.object(mod.list_ports,'comports',return_value=[])):
            patcher.start();self.addCleanup(patcher.stop)
        w=mod.SerialMonitorWindow()
        deadline=time.monotonic()+2
        while not w.refresh_button.isEnabled() and time.monotonic()<deadline:
            self.qt.processEvents();time.sleep(.002)
        self.assertTrue(w.refresh_button.isEnabled())
        w.render_timer.stop()
        # Ignore any asynchronous port result; select a deterministic fake serial.
        w.port_combo.addItem('fake','fake');w.port_combo.setCurrentIndex(w.port_combo.count()-1)
        try:
            with patch.object(mod,'QPreparationThread',FakeThread):
                w.recover_q()
                thread=w._q_preparation
                self.assertTrue(thread.recovery)
                for widget in (w.connect_button,w.demo_button,w.prepare_q_button,w.recover_q_button,w.port_combo,w.refresh_button):
                    self.assertFalse(widget.isEnabled())
                w.prepare_q();w.recover_q();w.connect_serial()
                self.assertIs(w._q_preparation,thread)
                thread.active=False;thread.result.emit(False,'failure');thread.finished.emit()
                self.assertIsNone(w._q_preparation)
                self.assertTrue(w.recover_q_button.isEnabled())
                w.recover_q()
                self.assertTrue(w._q_preparation.recovery)
                w._q_preparation.active=False;w._q_preparation.finished.emit()
        finally:
            w._q_preparation=None;w.close()


if __name__=='__main__':unittest.main()
