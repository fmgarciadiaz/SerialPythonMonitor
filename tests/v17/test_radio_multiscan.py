import unittest
from monitor.v17.radio_multiscan import estimate_rf,folded

class MultiscanTests(unittest.TestCase):
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
        from monitor.v17.app import SerialMonitorWindow
        from monitor.v17.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
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
        from monitor.v17.app import SerialMonitorWindow
        from monitor.v17.radio_multiscan import MultirateScan
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
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
