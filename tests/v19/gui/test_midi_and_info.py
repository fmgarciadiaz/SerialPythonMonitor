import os,json,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from monitor.v19.app import QtCore,QtWidgets,SerialMonitorWindow,InstrumentLogo
from monitor.v19.midi_process import MidiProcess

class MidiAndInfoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_midi_json_and_queued_notification_without_device(self):
        parent=QtCore.QObject();client=MidiProcess(parent)
        ports=[];ready=[];notifications=[]
        client.ports.connect(ports.append);client.ready.connect(lambda:ready.append(True))
        client.messages_ready.connect(lambda:notifications.append(True))
        payload=b'\n'.join(json.dumps(row).encode() for row in (
            {'ports':['Entrada simulada']},{'ready':True},
            {'message':{'type':'note_on','note':60,'velocity':100},'received_ns':123})) + b'\n'
        with patch.object(client.process,'readAllStandardOutput',return_value=QtCore.QByteArray(payload)):
            client.read_output()
        self.app.processEvents()
        self.assertEqual(ports,[['Entrada simulada']]);self.assertEqual(ready,[True])
        self.assertEqual(len(client.messages),1);self.assertEqual(client.messages[0].note,60)
        self.assertEqual(client.messages[0].received_ns,123);self.assertTrue(notifications)
        client.close();self.assertFalse(client.dispatch.isActive());self.app.processEvents()

    def test_information_is_modeless_and_identifies_actual_binding(self):
        with patch('monitor.v19.app.usb_devices',return_value=[]),patch('monitor.v19.app.list_ports.comports',return_value=[]):
            window=SerialMonitorWindow()
            try:
                logo=window.findChild(InstrumentLogo);logo.info_button.click()
                dialog=logo.information
                self.assertFalse(dialog.isModal());self.assertTrue(dialog.isVisible())
                text='\n'.join(item.text() for item in dialog.findChildren(QtWidgets.QLabel))
                self.assertIn('PySide:',text);self.assertIn('SCP1',text);self.assertIn('F. Garcia Diaz',text)
                dialog.close();logo.info_button.click();self.assertIs(logo.information,dialog)
            finally:window.close();self.app.processEvents()

if __name__=='__main__':unittest.main()
