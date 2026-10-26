import unittest
from monitor.v18.radio_multiscan import estimate_rf,folded

class MultiscanTests(unittest.TestCase):
    def test_high_rate_adc8_uses_only_fast_auxiliary_profiles(self):
        from monitor.v18.radio_multiscan import scan_profiles
        from monitor.v18.receiver.unoq_acquisition import Configuration
        for rate in (1818181,1600000,1403508):
            original=Configuration(8,rate)
            configs=scan_profiles(original)
            self.assertEqual(configs[0],original)
            self.assertEqual(len(set(configs)),3)
            self.assertEqual({(c.period,c.node_pairs) for c in configs},
                             {(88,3488),(100,3456),(114,3456)})
            self.assertNotIn(1118881,[c.rate for c in configs])

    def test_other_high_rate_formats_avoid_legacy_auxiliaries(self):
        import json
        from pathlib import Path
        from unittest.mock import patch
        from monitor.v18.receiver import unoq_native
        from monitor.v18.receiver.unoq_acquisition import Configuration
        from monitor.v18.radio_multiscan import scan_profiles
        profiles=json.loads(Path('experimentos/fs_max_v18/candidate_profiles.json').read_text())
        with patch.object(unoq_native,'PROFILES',unoq_native.PROFILES+tuple(profiles)):
            for bits,ticks,excluded in ((10,122,176),(12,146,None),(14,176,228)):
                p=next(p for p in profiles if p['bits']==bits and p['ticks']==ticks)
                configs=scan_profiles(Configuration.from_wire(bits,unoq_native.code(p)))
                self.assertEqual(len(set(configs)),3)
                self.assertTrue(all(c.channels==1 and c.bits==bits for c in configs))
                if excluded:self.assertNotIn(excluded,[c.period for c in configs])

    def test_fast_auxiliary_rates_resolve_in_band_and_aliased_stations(self):
        from monitor.v18.radio_multiscan import scan_profiles
        from monitor.v18.receiver.unoq_acquisition import Configuration
        rates=[c.actual_rate for c in scan_profiles(Configuration(8,1818181))]
        for frequency in (500000,1250000,1700000):
            peaks=estimate_rf(self.scans(frequency,rates),rates[0],8000)
            self.assertEqual(len(peaks),1,peaks)
            self.assertAlmostEqual(peaks[0]['frequency'],frequency)

    def scans(self,frequency,rates):
        return [(r,[dict(frequency=folded(frequency,r),dbfs=-30,above_noise_db=20,persistence=3)]) for r in rates]
    def test_stationary_and_moving_alias(self):
        rates=[1600000,1250000,160000000/188]
        for frequency in (500000,710440,1000000,1500000):
            found=estimate_rf(self.scans(frequency,rates),rates[0],10000)
            self.assertEqual(len(found),1,found)
            self.assertAlmostEqual(found[0]['frequency'],frequency)
            self.assertEqual(found[0]['confidence'],'RF estimada')
    def test_two_rate_ambiguity_and_third_resolves(self):
        rates=[1600000,1250000]
        found=estimate_rf(self.scans(1425000,rates),rates[0],10000)
        self.assertEqual([p['frequency'] for p in found],[175000,1425000])
        self.assertTrue(all(p['confidence']=='ambigua' for p in found))
        rates.append(160000000/188)
        self.assertEqual([p['frequency'] for p in estimate_rf(self.scans(1425000,rates),rates[0],10000)],[1425000])
    def test_unmatched_or_boundary_does_not_confirm(self):
        self.assertEqual(estimate_rf([(1600000,[dict(frequency=500000)]),(1250000,[])],1600000,10000),[])

    def test_gui_transaction_cancel_restores_controls_and_frequency(self):
        from unittest.mock import patch,MagicMock
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        from monitor.v18.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000)
            w.radio_us.setChecked(True);w.radio_frequency.setValue(1000)
            w.serial_worker=MagicMock();w.radio_enabled.setChecked(True)
            scan=MultirateScan(w);w._radio_multiscan=scan
            scan.start()
            self.assertTrue(scan.active)
            self.assertEqual(len(scan.configs),3)
            self.assertFalse(w.radio_enabled.isChecked())
            self.assertFalse(w.radio_output_rate.isEnabled())
            scan.start()  # Second click cancels and restores.
            self.assertTrue(scan.restoring)
            w.sample_counter+=200000
            scan.tick()
            self.assertFalse(scan.active)
            self.assertEqual(w.radio_frequency.value(),1000)
            self.assertTrue(w.radio_enabled.isChecked())
            self.assertTrue(w.radio_output_rate.isEnabled())
        finally:
            w.serial_worker=None;w.close();app.processEvents()


    def test_pending_scan_does_not_read_rf_history_again(self):
        from unittest.mock import Mock,patch
        from concurrent.futures import Future
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        from monitor.v18.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        old=w.series
        try:
            w._acquisition_confirmed(8,1600000);w.serial_worker=Mock()
            scan=MultirateScan(w);scan.start();scan.future=Future()
            w.sample_counter=1000000
            class Unreadable(dict):
                def __getitem__(self,key):raise AssertionError('Repeated RF capture')
            w.series=Unreadable()
            scan.tick()
            self.assertFalse(scan.restoring)
        finally:
            scan.timer.stop();scan.active=False;w.series=old;w.serial_worker=None;w.close();app.processEvents()

    def test_failed_scan_resumes_pending_window_close(self):
        from unittest.mock import MagicMock,patch
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        from monitor.v18.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000);w.serial_worker=MagicMock()
            scan=MultirateScan(w);scan.start();w._close_pending=True;w.serial_worker=None
            scan.error='Flujo cerrado'
            with patch.object(w,'close') as close:
                scan.finish();app.processEvents();close.assert_called_once()
            self.assertFalse(scan.active)
        finally:w._close_pending=False;w.serial_worker=None;w.close();app.processEvents()

    def test_restore_timeout_keeps_radio_paused_even_with_matching_configuration(self):
        from unittest.mock import MagicMock,patch
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        from monitor.v18.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000);w.serial_worker=MagicMock()
            w.radio_enabled.setChecked(True)
            scan=MultirateScan(w);w._radio_multiscan=scan;scan.start();scan.restore()
            scan.tick()  # Matching settings alone are not fresh RF confirmation.
            self.assertTrue(scan.active)
            self.assertFalse(w.radio_enabled.isChecked())
            scan.deadline=0
            with patch.object(w,'_finish_radio_scan_a0') as finish:
                scan.tick();finish.assert_called_once_with(False)
            self.assertFalse(scan.active)
            self.assertFalse(scan.restore_confirmed)
            self.assertFalse(w.radio_enabled.isChecked())
            self.assertIn('Restauración no confirmada',w.radio_status.text())
        finally:w.serial_worker=None;w.close();app.processEvents()

    def test_disconnect_during_restore_does_not_resume_radio(self):
        from unittest.mock import MagicMock,patch
        from PyQt6 import QtWidgets
        from monitor.v18.app import SerialMonitorWindow
        from monitor.v18.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v18.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w._acquisition_confirmed(8,1600000);w.serial_worker=MagicMock()
            w.radio_enabled.setChecked(True)
            scan=MultirateScan(w);w._radio_multiscan=scan;scan.start();scan.restore()
            w.serial_worker=None;scan.tick()
            self.assertFalse(scan.active)
            self.assertFalse(w.radio_enabled.isChecked())
            self.assertFalse(scan.restore_confirmed)
        finally:w.serial_worker=None;w.close();app.processEvents()
