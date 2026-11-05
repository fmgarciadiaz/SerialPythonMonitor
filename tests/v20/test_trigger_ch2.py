import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow


class TriggerCh2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v20.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
        self.w.render_timer.stop();self.w._fps_timer.stop()

    def tearDown(self):self.w.close();self.qt.processEvents()

    def signal(self,count,hpos=0):
        w=self.w;w.on_headers_detected(['CH1','CH2'])
        w.sample_counter=count;w.sample_numbers.extend(np.arange(count))
        w.series['Tiempo (us)'].extend(np.arange(count)*25.)
        w.series['CH1'].extend(np.full(count,.5))
        w.series['CH2'].extend(np.where(np.arange(count)%20<10,1.,2.3))
        w.current_dt_us=25.;w.h_scale=9000;w.h_pos=hpos
        w.selected_columns={name:name in ('CH1','CH2') for name in w.known_columns}
        w.trigger_source_combo.setCurrentText('CH2')
        w.trigger_checkbox.setChecked(True)

    def test_trigger_is_above_traces_and_cursor_overlays(self):
        self.signal(20000)
        self.w.render_frame()
        self.assertGreater(self.w.trigger_line.zValue(),200)
        self.assertGreater(self.w.trigger_t_marker.zValue(),200)
        self.assertTrue(self.w.trigger_line.isVisible())

    def test_ch2_triggers_both_edges_while_ch1_is_flat(self):
        self.signal(20000)
        for edge in ('Ascendente','Descendente'):
            self.w.trigger_edge_combo.setCurrentText(edge)
            self.w.render_frame()
            self.assertIsNotNone(self.w.frozen_frame)
            self.assertIn('Disparo (CH2',self.w.trigger_status_label.text())
            values=self.w.frozen_frame[1]['CH2'];pre=900
            if edge=='Ascendente':self.assertLess(values[pre-1],values[pre])
            else:self.assertGreater(values[pre-1],values[pre])

    def test_ch2_zero_pretrigger_does_not_read_negative_history(self):
        self.signal(10000,hpos=1000)
        self.w.render_frame()
        self.assertIsNotNone(self.w.frozen_frame)
        self.assertIn('Disparo (CH2',self.w.trigger_status_label.text())


if __name__=='__main__':unittest.main()
