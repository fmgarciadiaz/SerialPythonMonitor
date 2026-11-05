import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import unittest
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets
from monitor.v20 import app as mod


class AsyncPortsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def wait(self, condition):
        deadline=time.monotonic()+2
        while not condition() and time.monotonic()<deadline:
            self.qt.processEvents();time.sleep(.002)
        self.assertTrue(condition())

    def window(self):
        with patch.object(mod,'usb_devices',return_value=[]), patch.object(mod.list_ports,'comports',return_value=[]):
            w=mod.SerialMonitorWindow()
        w.render_timer.stop()
        self.wait(lambda:w.refresh_button.isEnabled())
        return w

    def test_slow_scan_keeps_gui_alive_and_preserves_selected_ports(self):
        w=self.window();release=Event();entered=Event();ticks=[]
        def devices():
            entered.set();release.wait(2);return ['q1','q2']
        ports=[SimpleNamespace(device='r4',description='R4',vid=1,pid=2,serial_number='other')]
        w.port_combo.addItem('Q2','q2');w.r4_combo.addItem('R4','r4');w.r4_combo.setCurrentIndex(1)
        timer=QtCore.QTimer();timer.setInterval(5);timer.timeout.connect(lambda:ticks.append(1))
        try:
            with patch.object(mod,'usb_devices',side_effect=devices),patch.object(mod.list_ports,'comports',return_value=ports):
                started=time.monotonic();w.refresh_ports()
                self.assertLess(time.monotonic()-started,.1)
                timer.start();self.wait(lambda:len(ticks)>=5 and entered.is_set())
                self.assertFalse(w.refresh_button.isEnabled())
                self.assertFalse(w.connect_button.isEnabled())
                release.set();self.wait(lambda:w.refresh_button.isEnabled())
            self.assertEqual(w.port_combo.currentData(),'q2')
            self.assertEqual(w.r4_combo.currentData(),'r4')
            self.assertTrue(w.connect_button.isEnabled())
        finally:release.set();timer.stop();w.close()

    def test_stale_results_close_and_connection_change_do_not_replace_ports(self):
        w=self.window()
        try:
            generation=w._port_refresh_generation
            w.port_combo.addItem('Keep','keep')
            result=(['late'],[])
            w._ports_discovered(generation-1,result,'')
            self.assertEqual(w.port_combo.currentData(),'keep')
            w._port_refresh_worker=object()
            w._ports_discovered(generation,result,'')
            self.assertEqual(w.port_combo.currentData(),'keep')
            w._port_refresh_worker=None
            w._port_discovery_closed=True
            w._ports_discovered(generation,result,'')
            self.assertEqual(w.port_combo.currentData(),'keep')
        finally:w.close()

    def test_discovery_error_is_visible_without_clearing_selection(self):
        w=self.window()
        try:
            w.port_combo.addItem('Keep','keep')
            with patch.object(w,'_set_connection_status') as status:
                w._ports_discovered(w._port_refresh_generation,None,'ADB timeout')
            status.assert_called_once_with('ADB timeout')
            self.assertEqual(w.port_combo.currentData(),'keep')
            self.assertTrue(w.refresh_button.isEnabled())
        finally:w.close()


if __name__=='__main__':unittest.main()
