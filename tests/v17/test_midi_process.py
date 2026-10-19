import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import unittest
from unittest.mock import MagicMock,patch
from PyQt6 import QtCore,QtWidgets
from monitor.v17.midi_process import MidiProcess
from monitor.v17.app import SerialMonitorWindow
from monitor.number_format import number


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
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            panel=w.fm_panel
            with patch('monitor.v17.fm_panel.MidiProcess') as factory:
                panel.refresh_midi()
                factory.return_value.start.assert_called_once_with()
                self.assertFalse(panel.refresh.isEnabled())
                panel._midi_ports_found(['Nord Stage 4 MIDI Output','Scarlett 4i4 4th Gen'])
                self.assertEqual(panel.midi_input.count(),4)
                self.assertTrue(panel.refresh.isEnabled())
                self.assertIsNone(panel._midi_discovery)
        finally:w.close()

    def test_arrival_dispatches_immediately_and_drains_burst_in_order(self):
        client=MidiProcess();batches=[]
        client.messages_ready.connect(lambda:batches.append(list(client.iter_pending())))
        records=[dict(type='control_change',control=1,value=i%128) for i in range(300)]
        payload=''.join(json.dumps({'message':record})+'\n' for record in records).encode()
        try:
            with patch.object(client.process,'readAllStandardOutput',side_effect=[QtCore.QByteArray(payload),QtCore.QByteArray()]):
                client.read_output()
                self.assertEqual(len(batches),1)
                self.assertEqual(len(batches[0]),128)
                for _ in range(5):self.app.processEvents()
            self.assertEqual([m.value for batch in batches for m in batch],[r['value'] for r in records])
            self.assertTrue(all(len(batch)<=128 for batch in batches))
            self.assertFalse(client.messages)
            self.assertFalse(client.dispatch.isActive())
        finally:client.close()

    def test_panel_applies_complete_midi_burst_once_on_arrival(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            panel=w.fm_panel
            with QtCore.QSignalBlocker(panel.midi_input):
                panel.midi_input.addItem('Test MIDI');panel.midi_input.setCurrentIndex(1)
            with patch.object(MidiProcess,'start'):panel.choose_midi()
            client=panel.midi
            panel.source=MagicMock();w.serial_worker=MagicMock()
            messages=[dict(type='note_on',note=60,velocity=100),
                      dict(type='control_change',control=64,value=127),
                      dict(type='note_off',note=60,velocity=0)]
            messages += [dict(type='control_change',control=1,value=i) for i in range(20)]
            messages += [dict(type='control_change',control=7,value=90)]
            client.buffer.extend(''.join(json.dumps({'message':m})+'\n' for m in messages).encode())
            with patch.object(client.process,'readAllStandardOutput',return_value=QtCore.QByteArray()), \
                    patch.object(panel,'_set_midi_activity') as activity:
                client.read_output()
            panel.source.update.assert_called_once();activity.assert_called_once_with(True)
            self.assertEqual(panel.volume_value.text(),number(panel.controls[3].value(),'.2f')+' Vpp')
            self.assertEqual(panel.dials[2].value(),round(panel.controls[2].value()*100))
            self.assertEqual(panel.dials[3].value(),round(panel.controls[3].value()*100))
            self.assertEqual(panel.notes,[(60,100)])
            self.assertTrue(panel.sustain_pedal)
            self.assertFalse(panel.pressed_notes)
            self.assertAlmostEqual(panel.controls[2].value(),19/127*10,places=1)
            self.assertAlmostEqual(panel.controls[3].value(),90/127*3.3,places=1)
        finally:w.close()
