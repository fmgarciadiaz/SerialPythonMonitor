import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from monitor.v19.app import QtCore,QtWidgets,GuiCallbackBridge

class Emitter(QtCore.QThread):
    delivered=QtCore.Signal(object)
    def run(self):self.delivered.emit({'value':42})

class ThreadBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_callback_is_queued_to_gui_thread_without_copying_payload(self):
        parent=QtCore.QObject();bridge=GuiCallbackBridge(parent);thread=Emitter()
        calls=[]
        bridge.connect_signal(thread.delivered,lambda value:calls.append((value,QtCore.QThread.currentThread())))
        thread.start()
        try:
            deadline=time.monotonic()+2
            while not calls and time.monotonic()<deadline:
                self.app.processEvents();time.sleep(.001)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][0],{'value':42})
            self.assertIs(calls[0][1],self.app.thread())
        finally:
            self.assertTrue(thread.wait(2000));parent.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
