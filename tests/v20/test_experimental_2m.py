import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6 import QtWidgets, QtCore

from monitor.v20 import app, radio_output, radio_output_panel
from monitor.v20.rate_catalog import catalog_rates, label
from monitor.v20.radio_multiscan import scan_profiles
from monitor.v20.receiver.unoq_acquisition import Configuration, RATES, experimental_2m
from monitor.v20.receiver.unoq_switch import Mode


class Experimental2MTests(unittest.TestCase):
    def test_only_exact_geometry_is_exposed(self):
        candidate = Configuration(8, 2000000)
        self.assertEqual((candidate.channels, candidate.period, candidate.node_pairs), (1, 80, 3488))
        self.assertTrue(experimental_2m(candidate))
        self.assertIn(2000000, RATES)
        self.assertTrue(app._configuration_supported(8, 2000000))
        self.assertFalse(app._configuration_supported(8, 2051282))
        self.assertFalse(app._configuration_supported(10, 2000000))
        self.assertNotIn(2051282, RATES)
        for key, value in [('ticks', 78), ('node_pairs', 3456), ('queue_slots', 8),
                           ('experimental_visible', False), ('integration_pending', True)]:
            metadata = dict(candidate._native, **{key: value})
            altered = SimpleNamespace(bits=8, rate=2000000, channels=1,
                                      period=metadata['ticks'], node_pairs=metadata['node_pairs'],
                                      _native=metadata)
            self.assertFalse(experimental_2m(altered), key)

    def test_catalog_and_previous_profiles(self):
        root = Path(__file__).resolve().parents[2]
        old = json.loads((root/'respaldos/host/v20_before_experimental_2m_20261104/monitor/v20/receiver/native_profiles.json').read_text())
        new = json.loads((root/'monitor/v20/receiver/native_profiles.json').read_text())
        self.assertEqual(len(old), len(new))
        for before, after in zip(old, new):
            if (before['bits'], before['channels'], before['ticks'], before['node_pairs']) == (8, 1, 80, 3488):
                self.assertEqual(after, dict(before, experimental_visible=True))
            else:
                self.assertEqual(after, before)
        self.assertIn(2000000, catalog_rates(8))
        self.assertNotIn(2000000, catalog_rates(10))
        self.assertNotIn(2051282, catalog_rates(8))
        self.assertIn('EXPERIMENTAL', label(Configuration(8, 2000000), str))
        self.assertNotIn('EXPERIMENTAL', label(Configuration(8, 1860465), str))
        self.assertEqual(Configuration().rate, 31250)

    def test_audio_guard_and_scan_are_exact(self):
        candidate = Configuration(8, 2000000)
        for guard in (radio_output.acquisition_error, radio_output_panel.acquisition_error):
            self.assertIsNone(guard(candidate))
            self.assertIsNotNone(guard(Configuration(8, 2051282)))
        self.assertEqual([c.rate for c in scan_profiles(candidate)],
                         [2000000, 1600000, 1403508])
        self.assertEqual([c.rate for c in scan_profiles(Configuration(8, 1860465))],
                         [1860465, 1600000, 1403508])

    def test_selector_marks_only_2m_experimental(self):
        qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch.object(app.SerialMonitorWindow, 'refresh_ports'):
            window = app.SerialMonitorWindow()
        try:
            self.assertEqual(window.config_rate_combo.currentData(), 40000)
            window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(8))
            window._destination_changed()
            index = window.config_rate_combo.findData(2000000)
            self.assertGreaterEqual(index, 0)
            self.assertTrue(window.config_rate_combo.model().item(index).isEnabled())
            self.assertFalse(window.config_rate_combo.view().isRowHidden(index))
            self.assertIn('EXPERIMENTAL', window.config_rate_combo.itemText(index))
            self.assertIn('caída nativa GUI', window.config_rate_combo.itemData(index, QtCore.Qt.ItemDataRole.ToolTipRole))
            self.assertNotIn('EXPERIMENTAL', window.config_rate_combo.itemText(window.config_rate_combo.findData(1860465)))
            window.applied_configuration = Configuration(8, 2000000)
            window.confirmed_mode = int(Mode.SPI)
            worker = window.serial_worker
            window.serial_worker = object()
            try:
                window._set_connection_status('Adquisición en vivo')
                self.assertIn('2,00 MHz · EXPERIMENTAL', window.status_label.text())
                window._refresh_applied_summary()
                self.assertIn('EXPERIMENTAL', window.confirmed_output_label.text())
            finally:
                window.serial_worker = worker
            window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(10))
            window._destination_changed()
            self.assertFalse(window.config_rate_combo.model().item(index).isEnabled())
        finally:
            window.render_timer.stop()
            window.close()
            window.deleteLater()
            qt.processEvents()


if __name__ == '__main__':
    unittest.main()
