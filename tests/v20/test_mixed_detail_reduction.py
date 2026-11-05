import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
from PySide6 import QtWidgets
from monitor.v20.app import SerialMonitorWindow
from monitor.v20.history import SampleHistory
from monitor.v20.receiver.unoq_acquisition import Configuration


class MixedDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_detail_uses_ring_extrema_but_cursors_and_measurements_keep_raw_samples(self):
        with patch('monitor.v20.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
        try:
            w.render_timer.stop();n=200000
            w.applied_configuration=Configuration(8,1860465)
            w.sample_counter=n;w.h_scale=n;w.h_pos=0;w.trigger_enabled=False
            w.detail_slider.setValue(50);w.active_meas_channel='CH1'
            times=np.arange(n)*1e6/w.applied_configuration.actual_rate
            values=np.sin(np.arange(n)*.02);values[12345]=99
            for name,data in (('Tiempo (us)',times),('CH1',values)):
                w.series[name].clear();w.series[name].extend(data)
            audio_times=np.linspace(times[0],times[-1],8000)
            audio={name:SampleHistory(10000) for name in ('Tiempo (us)','RADIO')}
            audio['Tiempo (us)'].extend(audio_times);audio['RADIO'].extend(np.zeros(8000))
            w.radio_stream=NS(rate=40000,sample_numbers=np.arange(8000),series=audio,counter=8000)
            with patch.object(w,'_draw_display_frame') as draw,patch.object(w,'_update_live_measurements') as meas:
                w._last_measurement_update=0
                w._render_mixed_temporal(['CH1','RADIO'],{'RADIO'})
                self.assertLess(len(draw.call_args.args[1]['CH1']),20000)
                self.assertEqual(max(draw.call_args.args[1]['CH1']),99)
                np.testing.assert_array_equal(meas.call_args.args[0]['CH1'],values)
                w._last_measurement_update=time.perf_counter();meas.reset_mock()
                w.scope_cursors.states[0].enabled=True
                w._render_mixed_temporal(['CH1','RADIO'],{'RADIO'})
                np.testing.assert_array_equal(draw.call_args.args[1]['CH1'],values)
                meas.assert_not_called()
                w.scope_cursors.states[0].enabled=False
                w._time_gap_sample_indices.append(100000)
                w._render_mixed_temporal(['CH1','RADIO'],{'RADIO'})
                np.testing.assert_array_equal(draw.call_args.args[1]['CH1'],values)
        finally:w.close();self.qt.processEvents()
