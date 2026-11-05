"""Resource parity and transition icons must not depend on loose SVG files."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import unittest
from PySide6 import QtCore, QtGui, QtWidgets
from monitor.v19.qt_assets import asset


class EmbeddedAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_all_embedded_svgs_preserve_bytes_and_pixels(self):
        assets = Path(__file__).resolve().parents[3] / 'monitor/v19/assets'
        # tests/v19/gui is three levels below the repository root.
        for path in assets.glob('*.svg'):
            with self.subTest(icon=path.name):
                resource = QtCore.QFile(asset(path.name))
                self.assertTrue(resource.open(QtCore.QIODevice.OpenModeFlag.ReadOnly))
                self.assertEqual(bytes(resource.readAll()), path.read_bytes())
                embedded = QtGui.QIcon(asset(path.name)).pixmap(32, 32).toImage()
                original = QtGui.QIcon(str(path)).pixmap(32, 32).toImage()
                self.assertFalse(embedded.isNull())
                self.assertEqual(embedded, original)
        self.assertGreater(len(list(assets.glob('*.svg'))), 50)

    def test_connection_and_playback_icons_use_resources(self):
        from monitor.v19.app import SerialMonitorWindow
        window = SerialMonitorWindow()
        try:
            for state in ('connecting', 'connected', 'disconnected'):
                window._set_connect_state(state)
                self.assertEqual(window.connect_button.icon().pixmap(32,32).toImage(),
                                 QtGui.QIcon(asset(f'plug_{state}.svg')).pixmap(32,32).toImage())
            window._wav_active = True
            window._sync_wav_transport()
            self.assertEqual(window.wav_play.icon().pixmap(32,32).toImage(),
                             QtGui.QIcon(asset('wav_stop.svg')).pixmap(32,32).toImage())
        finally:
            window.close()
