import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import unittest
from unittest.mock import patch
from PyQt6 import QtCore,QtWidgets
from monitor.v15.midi_process import MidiProcess
from monitor.v15.app import SerialMonitorWindow


class MidiProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_timeout_does_not_wait_for_native_backend(self):
        client=MidiProcess();errors=[];client.error.connect(errors.append)
        with patch.object(client.process,'start'):
            client.start()
        self.assertEqual(client.timeout.interval(),8000)
        self.assertTrue(client.timeout.isActive())
        client.timeout.timeout.emit()
        self.assertTrue(client.closed);self.assertIn('8 segundos',errors[0])

    def test_message_dispatch_and_polling_are_bounded(self):
        client=MidiProcess()
        line=json.dumps({'message':dict(type='note_on',note=69,velocity=100)})+'\n'
        client.buffer.extend((line*300).encode())
        with patch.object(client.process,'readAllStandardOutput',return_value=QtCore.QByteArray()):
            client.read_output()
            self.assertEqual(len(client.messages),256)
            self.assertEqual(len(list(client.iter_pending())),128)
            client.read_output()
        self.assertEqual(len(client.messages),172)
        client.close()

    def test_refresh_is_async_and_populates_physical_inputs(self):
        with patch('monitor.v15.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            panel=w.fm_panel
            with patch('monitor.v15.fm_panel.MidiProcess') as factory:
                panel.refresh_midi()
                factory.return_value.start.assert_called_once_with()
                self.assertFalse(panel.refresh.isEnabled())
                panel._midi_ports_found(['Nord Stage 4 MIDI Output','Scarlett 4i4 4th Gen'])
                self.assertEqual(panel.midi_input.count(),4)
                self.assertTrue(panel.refresh.isEnabled())
                self.assertIsNone(panel._midi_discovery)
        finally:w.close()
