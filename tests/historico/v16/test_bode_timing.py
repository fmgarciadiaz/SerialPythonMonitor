import unittest
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

from monitor.historico.v16.bode import BodeSweep, tone_transfer
from monitor.historico.v16.bode_timing import channel_delay_us, pair_delay_us, correct_phase
from monitor.historico.v16.receiver.unoq_acquisition import Configuration


class BodeTimingTests(unittest.TestCase):
    def test_loopback_and_circuit_phase(self):
        for config in (Configuration(14, 40000), Configuration(16, 40000),
                       Configuration(16, 76226), Configuration(10, 40000)):
            delay = channel_delay_us(config) / 1e6
            t = np.arange(8000) / config.actual_rate
            for circuit_phase in (0, -45):
                x = np.cos(2*np.pi*2000*t)
                y = .7*np.cos(2*np.pi*2000*(t+delay)+np.deg2rad(circuit_phase))
                gain, phase = tone_transfer(t, x, y, 2000)
                data = correct_phase([[2000, gain, phase]], delay*1e6)
                self.assertAlmostEqual(data[0, 2], circuit_phase, places=7)
                self.assertAlmostEqual(data[0, 1], 20*np.log10(.7), places=7)

    def test_filter_origin_and_reverse_pair(self):
        config = Configuration(16, 40000)
        delay = channel_delay_us(config)
        self.assertEqual(pair_delay_us(config, ('CH2', 'CH1')), -delay)
        self.assertEqual(pair_delay_us(config, ('CH1', 'FILTER'), 'CH1'), 0)
        self.assertEqual(pair_delay_us(config, ('CH1', 'FILTER'), 'CH2'), delay)
        self.assertEqual(pair_delay_us(config, ('FILTER', 'CH2'), 'CH2'), 0)

    def test_measured_calibration_is_not_subtracted_twice(self):
        raw = np.array([[1000., 0., 10.], [2000., 0., 20.]])
        check = SimpleNamespace(isChecked=lambda: True)
        panel = SimpleNamespace(correction=check,
                                history_delays=[10/360*1000], result_delay_us=0,
                                reference_for=lambda *args: (None, None))
        calibrated = raw.copy(); calibrated[0, 2] = 0
        with patch('monitor.historico.v16.bode.correct_transfer', return_value=(calibrated, np.array([True, False]))):
            result = BodeSweep.display_data(panel, raw, 0, Configuration(14, 40000))
        np.testing.assert_allclose(result[:, 2], 0, atol=1e-12)
        np.testing.assert_array_equal(raw[:, 2], [10, 20])

    def test_nan_and_same_channel_phase_survive(self):
        data = [[100, 0, float('nan')], [1000, -3, -90]]
        result = correct_phase(data, 0)
        self.assertTrue(np.isnan(result[0, 2]))
        self.assertEqual(result[1, 2], -90)

    def test_gui_toggle_preserves_raw_and_history_profiles(self):
        from PyQt6 import QtWidgets
        from monitor.historico.v16.app import SerialMonitorWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.historico.v16.app.usb_devices', return_value=[]):
            window = SerialMonitorWindow()
        try:
            for panel in window.spectral.bode.panels:
                self.assertTrue(panel.correction.isChecked())
                panel.result_profile = Configuration(16, 40000)
                panel.result_delay_us = channel_delay_us(panel.result_profile)
                phase = 360*1000*panel.result_delay_us/1e6
                panel.result = [(1000, 0, phase)]
                panel.history = [[(1000, 0, 360*1000*6.5185185185/1e6)]]
                panel.history_profiles = [Configuration(16, 76226)]
                panel.history_delays = [6.5185185185]
                panel.draw()
                self.assertAlmostEqual(panel.curve_sets[1][1].getData()[1][0], 0)
                self.assertAlmostEqual(panel.curve_sets[0][1].getData()[1][0], 0)
                panel.correction.setChecked(False)
                self.assertAlmostEqual(panel.curve_sets[1][1].getData()[1][0], phase)
                panel.correction.setChecked(True)
                self.assertEqual(panel.result[0][2], phase)
        finally:
            window.close()

    def test_unified_control_follows_reference_without_resetting_choice(self):
        from PyQt6 import QtWidgets
        from monitor.historico.v16.app import SerialMonitorWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.historico.v16.app.usb_devices', return_value=[]):
            window = SerialMonitorWindow()
        try:
            bode = window.spectral.bode
            reference = {'points': [[20, 0, 0], [5000, 0, 10]]}
            for panel in bode.panels:
                panel.correction.setChecked(False)
            with patch('monitor.historico.v16.bode_calibration.find_reference', return_value=reference):
                bode.refresh_reference()
                for panel in bode.panels:
                    self.assertEqual(panel.correction.text(), 'Corregir (medido)')
                    self.assertFalse(panel.correction.isChecked())
                    self.assertTrue(panel.correction.isEnabled())
                    self.assertIn('Fuera de esta banda', panel.correction.toolTip())
            with patch('monitor.historico.v16.bode_calibration.find_reference', return_value=None):
                bode.refresh_reference()
                for panel in bode.panels:
                    self.assertEqual(panel.correction.text(), 'Corregir (estimado)')
                    self.assertFalse(panel.correction.isChecked())
                    panel.correction.setChecked(True)
                    bode.refresh_reference()
                    self.assertTrue(panel.correction.isChecked())
        finally:
            window.close()

    def test_installed_references_are_profile_and_method_specific(self):
        import json
        from pathlib import Path
        from monitor.historico.v16.bode_calibration import find_reference, correct_transfer, CALIBRATION_DIR
        for path in CALIBRATION_DIR.glob('bode_reference_*_tone.json'):
            ref = json.loads(path.read_text())
            config = Configuration(**ref['acquisition'])
            found = find_reference(ref['instrument'], config, 'tone')
            self.assertIsNotNone(found)
            source = json.loads(Path(ref['source_report']).read_text())
            held_out = source['cases'][2]['curve']
            corrected, mask = correct_transfer(held_out, found, config, ref['instrument'])
            self.assertTrue(mask.all())
            self.assertLess(abs(corrected[:, 2]).max(), 5)
            self.assertIsNone(find_reference(ref['instrument'], config, 'pulse_h1'))
            wrong = dict(ref['instrument'], firmware_sha256='0'*64)
            self.assertIsNone(find_reference(wrong, config, 'tone'))

    def test_bode_fields_have_matching_width_and_alignment(self):
        from PyQt6 import QtWidgets
        from monitor.historico.v16.app import SerialMonitorWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.historico.v16.app.usb_devices', return_value=[]):
            window = SerialMonitorWindow()
        try:
            window.show()
            for index, panel in enumerate(window.spectral.bode.panels):
                window.spectral.select_bode(index)
                app.processEvents()
                controls = [panel.start, panel.end, panel.reference_channel, panel.response_channel]
                if index == 0:
                    controls += [panel.points, panel.cycles, panel.settle]
                elif index == 1:
                    controls += [panel.width, panel.capture, panel.averages]
                else:
                    controls += [panel.duration, panel.capture, panel.method]
                widths = [c.width() for c in controls]
                self.assertLessEqual(max(widths)-min(widths), 1, widths)
                self.assertTrue(all(c.height() == 28 for c in controls))
                left = panel.start.mapTo(window, panel.start.rect().topLeft()).x()
                self.assertEqual(panel.reference_channel.mapTo(window, panel.reference_channel.rect().topLeft()).x(), left)
                self.assertEqual(panel.response_channel.mapTo(window, panel.response_channel.rect().topLeft()).x(), panel.end.mapTo(window, panel.end.rect().topLeft()).x())
                single = panel.settle if index == 0 else panel.averages if index == 1 else panel.method
                self.assertEqual(single.mapTo(window, single.rect().topLeft()).x(), left)
        finally:
            window.close()


if __name__ == '__main__':
    unittest.main()
