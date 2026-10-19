import unittest
import numpy as np
from unittest.mock import Mock,patch
from monitor.v17.radio_loop_guard import RadioLoopGuard
from monitor.v17.radio_output import RadioDacSource


class LoopGuardTests(unittest.TestCase):
    def test_fractional_adc_clock_never_indexes_exclusive_block_end(self):
        guard=RadioLoopGuard()
        count=14400
        guard.next_input=float(count)-1e-9
        guard.observe(np.zeros(count),160000000/150)
        for _ in range(100):guard.observe(np.zeros(count),160000000/150)
        self.assertGreaterEqual(guard.next_input,guard.input_count)
    def test_fractional_return_with_noise_keeps_strict_threshold(self):
        rng=np.random.default_rng(123)
        codes=np.repeat(rng.integers(600,3500,6000),10).astype('<u2')
        y=codes[::10].astype(float)*3.3/4095
        for phase in (.25,.5,.75):
            guard=RadioLoopGuard();guard.sent(codes,0)
            returned=(y[:-1]*(1-phase)+y[1:]*phase)*.7+.2+rng.normal(0,.001,len(y)-1)
            for i in range(3):
                self.assertEqual(guard.observe(returned[1000+i*512:1512+i*512],4000),i==2)

    def test_delayed_scaled_return_trips_only_after_three_windows(self):
        rng=np.random.default_rng(42)
        codes=np.repeat(rng.integers(600,3500,6000),10).astype('<u2')
        guard=RadioLoopGuard();guard.sent(codes,0)
        returned=codes[::10].astype(float)*3.3/4095*.6+.3
        for i in range(3):
            self.assertEqual(guard.observe(returned[1000+i*512:1000+(i+1)*512],4000),i==2)

    def test_independent_rf_silence_and_tone_do_not_trip(self):
        rng=np.random.default_rng(7)
        for index,values in enumerate((rng.normal(1.65,.3,4096),np.full(4096,1.65),
                       1.65+.5*np.sin(np.arange(4096)*2*np.pi/32))):
            guard=RadioLoopGuard()
            codes=np.repeat(np.rint((values+1)*500),10).astype('<u2')
            guard.sent(codes,0)
            incoming=rng.normal(1.65,.3,4096) if index==0 else values
            for part in np.array_split(incoming,8):self.assertFalse(guard.observe(part,4000))

    def test_source_latches_error_and_prevents_further_codes(self):
        source=RadioDacSource(buffer_seconds=0)
        rng=np.random.default_rng(3)
        codes=np.repeat(rng.integers(700,3300,6000),10).astype('<u2')
        source.loop_guard.sent(codes,0)
        values=codes[::10].astype(float)*3.3/4095
        for part in np.array_split(values[1000:2536],3):source.observe_input(part,4000)
        self.assertIn('realimentación',source.error)
        self.assertIsNone(source.try_codes(0,480))
        source.observe_input(np.zeros(512),4000)
        self.assertIn('realimentación',source.error)

    def test_panel_stops_output_and_displays_latched_reason(self):
        from PyQt6 import QtWidgets
        from monitor.v17.radio_output_panel import RadioOutputPanel
        from types import SimpleNamespace
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        owner=SimpleNamespace(radio_frequency=SimpleNamespace(value=lambda:550),
                              serial_worker=Mock(),_stop_wav=Mock())
        panel=RadioOutputPanel(owner)
        source=RadioDacSource();source.error='Radio A0: posible realimentación A0 → CH1; salida detenida'
        panel.source=source
        with patch('monitor.v17.radio_output_panel.record_stop') as record:panel.sync()
        self.assertIsNone(panel.source)
        self.assertTrue(source.closed)
        owner._stop_wav.assert_called_once()
        owner.serial_worker.set_radio_output_source.assert_called_once_with(None)
        self.assertIn('realimentación',panel.state.text())
        self.assertEqual(record.call_args.args[2],source.error)
        panel.close()
