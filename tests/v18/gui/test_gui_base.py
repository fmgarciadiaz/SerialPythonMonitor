"""Offline construction, presentation and ownership boundaries for the V18 GUI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import unittest
from unittest.mock import patch

from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_autoload import CURRENT_FIRMWARE, APPS


class GuiBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_construct_show_modes_and_close_without_opening_transport(self):
        with patch('monitor.v18.app.usb_devices', return_value=[]), \
             patch('monitor.v18.app.list_ports.comports', return_value=[]), \
             patch('monitor.v18.app.Connection') as connection, \
             patch('monitor.v18.app.connect_scope') as connect_scope, \
             patch('monitor.v18.app.ensure_scope') as ensure_scope:
            window = SerialMonitorWindow()
            try:
                window.show()
                self.app.processEvents()
                self.assertIn('Scope V18', window.windowTitle())
                self.assertFalse(window.windowIcon().isNull())
                self.assertEqual(window.filter_config.source, 'OFF')
                self.assertIsNone(window.serial_worker)
                self.assertFalse(window.prepare_q_button.isEnabled())
                window.prepare_q()
                window._begin_q_preparation('offline')
                ensure_scope.assert_not_called()
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
                connect_scope.assert_not_called()
                ensure_scope.assert_not_called()
            finally:
                window.close()
                self.app.processEvents()
            self.assertFalse(window.isVisible())
            self.assertFalse(window.render_timer.isActive())

    def test_host_assets_are_local_and_installed_firmware_is_v18(self):
        package = Path(__file__).resolve().parents[3] / 'monitor' / 'v18'
        # The host's visual identity is independent of the installed Q stack.
        self.assertTrue((package / 'assets' / 'scope_app.svg').is_file())
        self.assertEqual(CURRENT_FIRMWARE, 'v18')
        self.assertEqual(APPS, {'Scope V18': 'v18'})


if __name__ == '__main__':
    unittest.main()
