import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch,MagicMock
from PyQt5 import QtWidgets,QtTest
from experimentos.tasas_spi.opt125.p992.monitor.app import SerialMonitorWindow
from experimentos.tasas_spi.opt125.p992.receiver.unoq_acquisition import Configuration

class FastMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        with patch('experimentos.tasas_spi.opt125.p992.monitor.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()
    def tearDown(self):self.w.serial_worker=None;self.w.close()
    def test_experimental_125k_is_offered_and_auto_applied(self):
        w=self.w;combo=w.config_rate_combo
        self.assertGreaterEqual(combo.findData(125000),0)
        for rate in (200000,250000):self.assertEqual(combo.findData(rate),-1)
        w.serial_worker=MagicMock();combo.setCurrentIndex(combo.findData(125000));QtTest.QTest.qWait(80)
        w.serial_worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(14,125000))
    def test_high_rate_to_oversampling_is_one_safe_profile(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(125000))
        w.serial_worker=MagicMock();w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(16));QtTest.QTest.qWait(80)
        w.serial_worker.request_output.assert_called_once_with(0,w.r4_combo.currentData(),Configuration(16,50000))
        self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(125000)).isEnabled())
    def test_uart_retains_safe_ceiling(self):
        w=self.w;w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(125000))
        w.destination_combo.setCurrentIndex(w.destination_combo.findData(1))
        self.assertEqual(w.config_rate_combo.currentData(),31250)
        self.assertFalse(w.config_rate_combo.model().item(w.config_rate_combo.findData(125000)).isEnabled())
    def test_fast_spectral_refresh_keeps_samples_and_heatmap_hops(self):
        import numpy as np
        w=self.w;display=w.spectral;display.set_mode(2);w.current_fs_hz=100000
        def append(start,count):
            indices=np.arange(start,start+count)
            w.sample_numbers.extend(indices)
            for name,history in w.series.items():
                history.extend(indices*10 if name=='Tiempo (us)' else np.sin(indices/20))
            w.sample_counter+=count
        append(0,12000)
        with patch('experimentos.tasas_spi.opt125.p992.monitor.spectrum.time.monotonic',return_value=10):display.render()
        first=display.last_end;append(12000,10000)
        with patch('experimentos.tasas_spi.opt125.p992.monitor.spectrum.time.monotonic',return_value=10.02):display.render()
        self.assertEqual(display.last_end,first)
        with patch('experimentos.tasas_spi.opt125.p992.monitor.spectrum.time.monotonic',return_value=10.06):display.render()
        self.assertGreater(display.last_end,first)
        self.assertGreaterEqual(len(display.frames),3)
        self.assertEqual(w.sample_counter,22000)
        self.assertEqual(len(w.series['V_IN']),22000)

    def _batch_125k(self,count=6000):
        import math
        return [{'Muestra':i+1,'Tiempo (us)':i*8,'ADC_IN':round(8000+4000*math.sin(i/20)),'V_IN':1.6+math.sin(i/20),'ADC_OUT':4000,'V_OUT':.8} for i in range(count)]
    def test_graph_trigger_and_single_at_125k(self):
        import numpy as np
        w=self.w;w.applied_configuration=Configuration(14,125000);w.current_fs_hz=125000;w.current_dt_us=8
        w.h_scale=500;w.h_pos=0;w.handle_batch(self._batch_125k());w.is_running=True
        w.trigger_enabled=False;w.render_frame()
        x,y=w.line_items['V_IN'].getData();self.assertGreater(len(x),0);self.assertGreater(np.ptp(y),1)
        w.trigger_source='V_IN';w.trigger_level=1.6;w.trigger_edge='Ascendente';w.trigger_mode='Normal'
        w.arm_single_shot();w.render_frame()
        self.assertFalse(w.is_running);self.assertFalse(w.single_shot_armed);self.assertIsNotNone(w.frozen_frame)
        self.assertIn('SINGLE CAPTURADO',w.status_label.text())
        frozen=w.frozen_frame[1]['V_IN'].copy();w.render_frame();np.testing.assert_array_equal(w.frozen_frame[1]['V_IN'],frozen)
    def test_csv_keeps_raw_125k_samples(self):
        import csv,tempfile
        from pathlib import Path
        w=self.w;w.demo_mode=True;w.applied_configuration=Configuration(14,125000)
        batch=self._batch_125k(113)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'capture.csv'
            with patch.object(w,'_create_log_filename',return_value=path):w.start_recording()
            w.handle_batch(batch);w.stop_recording()
            with path.open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),113);self.assertEqual(int(rows[-1]['Tiempo_us']),896)
        self.assertEqual(int(rows[-1]['ADC_IN']),batch[-1]['ADC_IN'])
        self.assertEqual(len(w.series['V_IN']),113)
