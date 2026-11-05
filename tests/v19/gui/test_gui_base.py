"""Offline construction, presentation and ownership boundaries for the V19 GUI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from PySide6 import QtWidgets
from monitor.v19.app import SerialMonitorWindow


class GuiBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_construct_show_modes_and_close_without_opening_transport(self):
        with patch('monitor.v19.app.usb_devices', return_value=[]), \
             patch('monitor.v19.app.list_ports.comports', return_value=[]), \
             patch('monitor.v19.app.Connection') as connection, \
             patch('monitor.v19.io.receiver_process.ReceiverProcess') as receiver, \
             patch('monitor.v19.app.QPreparationThread') as preparation:
            window = SerialMonitorWindow()
            try:
                window.show()
                self.app.processEvents()
                self.assertIn('Arduscopio Q', window.windowTitle())
                self.assertNotIn('V19', window.windowTitle())
                self.assertFalse(window.windowIcon().isNull())
                self.assertEqual(window.filter_config.source, 'OFF')
                self.assertIsNone(window.serial_worker)
                window.prepare_q()
                preparation.assert_not_called()
                self.assertIsNone(window._q_preparation)
                for mode in range(4):
                    window.spectral.set_mode(mode)
                    window.render_frame()
                    self.app.processEvents()
                for mode in range(window.generator_mode.count()):
                    window.generator_mode.setCurrentIndex(mode)
                    self.app.processEvents()
                self.assertIsNone(window.serial_worker)
                connection.assert_not_called()
                receiver.assert_not_called()
                preparation.assert_not_called()
            finally:
                window.close()
                self.app.processEvents()
            self.assertFalse(window.isVisible())
            self.assertFalse(window.render_timer.isActive())

    def test_host_assets_are_local_and_installed_pair_is_v19(self):
        package = Path(__file__).resolve().parents[3] / 'monitor' / 'v19'
        # The host's visual identity is independent of the installed Q stack.
        self.assertTrue((package / 'assets' / 'scope_app.svg').is_file())
        config=json.loads((package.parents[1]/'arduino/v19/unoq.json').read_text())
        self.assertEqual(config['name'],'Scope V19')
        self.assertEqual(config['remote_app'],'/home/arduino/ArduinoApps/scope-v19')


if __name__ == '__main__':
    unittest.main()
