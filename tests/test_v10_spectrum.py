import unittest
from unittest.mock import patch
import numpy as np
from monitor.v10.spectrum import spectrum, WINDOWS


class SpectrumMathTests(unittest.TestCase):
    def test_frequency_and_window_corrected_peak_amplitude(self):
        n, fs = 2048, 32768
        samples = 1.65 + .8*np.sin(2*np.pi*1024*np.arange(n)/fs)
        for window in WINDOWS:
            f, a = spectrum(samples, fs, window)
            self.assertEqual(f[np.argmax(a)], 1024)
            self.assertAlmostEqual(a.max(), .8, places=4)
            self.assertLess(a[0], 1e-7)

    def test_dc_and_nyquist_are_not_doubled(self):
        _, dc = spectrum(np.ones(1024)*1.65, 32768, 'Rectangular', False)
        self.assertAlmostEqual(dc[0], 1.65)
        _, nyquist = spectrum((-1.)**np.arange(1024), 32768, 'Rectangular')
        self.assertAlmostEqual(nyquist[-1], 1)


class SpectrumUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5 import QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from monitor.v10.app import SerialMonitorWindow
        with patch('monitor.v10.app.usb_devices', return_value=[]):
            self.w = SerialMonitorWindow()
        self.s = self.w.spectral
        self.s.size.setCurrentText('256')
        self.index = 0

    def tearDown(self):
        self.w.close()

    def feed(self, n=512, gap=0):
        batch = []
        for i in range(self.index, self.index+n):
            batch.append({'V_IN':1.65+np.sin(2*np.pi*1024*i/32768),
                          'V_OUT':1.65+.5*np.sin(2*np.pi*2048*i/32768),
                          'Tiempo (us)': i*1e6/32768+gap})
        self.index += n
        self.w.handle_batch(batch)
        self.s.render()

    def test_modes_two_channels_pause_and_return_to_scope(self):
        self.s.set_mode(1); self.feed()
        self.assertEqual(self.w.display_stack.currentIndex(), 1)
        for curve, expected in zip(self.s.curves, (1024, 2048)):
            x, y = curve.getData()
            self.assertEqual(x[np.argmax(y)], expected)
        end = self.s.last_end
        self.w.is_running = False; self.feed()
        self.assertEqual(self.s.last_end, end)
        self.w.is_running = True
        self.s.channels[1].setCurrentText('Ninguno'); self.s.render()
        self.assertFalse(self.s.plots[1].isVisible())
        self.s.set_mode(0)
        self.assertEqual(self.w.display_stack.currentIndex(), 0)

    def test_demo_has_uniform_sample_time_for_fft(self):
        self.s.set_mode(1)
        for _ in range(8): self.w._generate_demo_samples()
        self.s.render()
        self.assertIsNotNone(self.s.curves[0].getData()[0])
        self.assertTrue(np.all(np.abs(np.diff(self.w.series['Tiempo (us)'][:]) - 400) <= 1))

    def test_heatmap_wraps_resets_and_rejects_gap(self):
        self.s.set_mode(2); self.s.seconds.setValue(2)
        for _ in range(140): self.feed(1024)
        raster = self.s.images[0].image
        self.assertLessEqual(raster.shape[1], 512)
        self.assertTrue(np.all(np.isfinite(raster)))
        self.assertLessEqual(len(self.s.frames), 512)
        self.feed(128, gap=10000)
        self.assertEqual(len(self.s.frames), 0)
        self.assertIn('Discontinuidad', self.s.info.text())
        self.w.clear_data()
        self.assertIsNone(self.s.images[0].image)
        self.assertIsNone(self.s.last_end)

class BodeMathTests(unittest.TestCase):
    def test_rc_gain_and_phase_with_dc_offsets(self):
        from monitor.v10.bode import tone_transfer
        fs, frequency, cutoff = 31250, 500, 200
        t = np.arange(10000)/fs
        ratio = 1/(1+1j*frequency/cutoff)
        vin = 1.5+.7*np.cos(2*np.pi*frequency*t)
        vout = 1.6+.7*np.real(ratio*np.exp(2j*np.pi*frequency*t))
        gain, phase = tone_transfer(t,vin,vout,frequency)
        self.assertAlmostEqual(gain,20*np.log10(abs(ratio)),places=8)
        self.assertAlmostEqual(phase,np.angle(ratio,deg=True),places=8)

    def test_zero_output_is_valid_zero_gain_with_undefined_phase(self):
        from monitor.v10.bode import tone_transfer
        t=np.arange(2048)/31250
        vin=1.65+np.cos(2*np.pi*1000*t)
        for vout in (np.zeros(len(t)), np.full(len(t),1.65)):
            gain,phase=tone_transfer(t,vin,vout,1000)
            self.assertTrue(np.isneginf(gain))
            self.assertTrue(np.isnan(phase))

    def test_tiny_filtered_output_keeps_gain(self):
        from monitor.v10.bode import tone_transfer
        t=np.arange(2048)/31250
        vin=1.65+np.cos(2*np.pi*1000*t)
        vout=1.65+1e-6*np.cos(2*np.pi*1000*t-.4)
        gain,phase=tone_transfer(t,vin,vout,1000)
        self.assertAlmostEqual(gain,-120,places=5)
        self.assertAlmostEqual(phase,np.rad2deg(-.4),places=5)

    def test_weak_reference_is_rejected(self):
        from monitor.v10.bode import tone_transfer
        t = np.arange(100)/1000
        with self.assertRaises(ValueError): tone_transfer(t,np.ones(100),np.ones(100),50)


class BodeUITests(unittest.TestCase):
    setUpClass = classmethod(SpectrumUITests.setUpClass.__func__)
    def setUp(self):
        SpectrumUITests.setUp(self)
        self.s.bode.calibrated.setChecked(False)
        self.w._generator_state_known = True
    tearDown = SpectrumUITests.tearDown
    feed = SpectrumUITests.feed

    def test_log_fft_and_heatmap_frequency_coordinates(self):
        self.s.set_mode(1); self.s.log_frequency.setChecked(True); self.feed()
        self.assertTrue(self.s.plots[0].getAxis('bottom').logMode)
        self.assertGreater(self.s.curves[0].xData[0],0)
        self.s.set_mode(2); self.feed()
        self.assertTrue(self.s.plots[0].getAxis('left').logMode)
        rect = self.s.images[0].mapRectToParent(self.s.images[0].boundingRect())
        self.assertAlmostEqual(rect.top(),np.log10(32768/256),places=5)
        self.assertAlmostEqual(rect.bottom(),np.log10(32768/2),places=5)
        self.s.log_frequency.setChecked(False); self.feed()
        self.assertFalse(self.s.plots[0].getAxis('left').logMode)

    def test_fft_fill_tracks_units_color_and_mode(self):
        self.s.set_mode(1); self.feed()
        self.assertLess(float(np.nanmin(self.s.fft_fills[0].yData)),0)
        self.assertEqual(self.s.fft_fills[0].opts['fillBrush'].color().alpha(),38)
        self.s.scale.setCurrentIndex(1); self.feed()
        self.assertEqual(float(np.nanmin(self.s.fft_fills[0].yData)),0)
        self.s.set_mode(3)
        self.assertIsNone(self.s.curves[0].opts['fillLevel'])

    def test_bode_waits_for_ack_sweeps_and_restores_generator(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorReply
        from transport.unoq_switch import Phase, Reason
        self.w.serial_worker = MagicMock()
        bode = self.s.bode
        bode.start.setValue(100); bode.end.setValue(1000); bode.points.setValue(2); bode.settle.setValue(20)
        previous = self.w._generator_config()
        self.s.set_mode(3)
        self.assertTrue(bode.active)
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0].wave,1)
        self.feed(128)
        self.assertEqual(len(bode.buffer),0)
        cursor = 128
        for _ in range(3):
            config = bode.config
            self.w._generator_confirmed(GeneratorReply(0x80000000,Phase.APPLIED,Reason.OK,True,config,config))
            frequency = bode.frequency
            idx = np.arange(cursor,cursor+5000); t = idx/31250
            ratio = 1/(1+1j*frequency/200)
            x = 1.65+.7*np.cos(2*np.pi*frequency*t)
            y = 1.65+.7*np.real(ratio*np.exp(2j*np.pi*frequency*t))
            self.w.handle_batch([{'Tiempo (us)':ti*1e6,'V_IN':a,'V_OUT':b} for ti,a,b in zip(t,x,y)])
            cursor += 5000
        self.assertFalse(bode.active)
        self.assertEqual(len(bode.result),3)
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0],previous)
        for frequency,gain,phase in bode.result:
            ratio = 1/(1+1j*frequency/200)
            self.assertAlmostEqual(gain,20*np.log10(abs(ratio)),places=6)
            self.assertAlmostEqual(phase,np.angle(ratio,deg=True),places=6)

    def test_cancel_restores_and_rejection_does_not_capture(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorReply
        from transport.unoq_switch import Phase, Reason
        self.w.serial_worker = MagicMock()
        previous = self.w._generator_config()
        self.s.set_mode(3)
        config = self.s.bode.config
        self.s.bode.confirmed(GeneratorReply(0x80000000,Phase.REJECTED,Reason.BUSY,False,previous,config))
        self.assertFalse(self.s.bode.active)
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0],previous)
        self.w._generator_requested = None
        self.s.bode.begin()
        self.s.set_mode(1)
        self.assertFalse(self.s.bode.active)
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0],previous)

    def test_timeout_and_discontinuity_abort_and_restore(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorReply
        from transport.unoq_switch import Phase, Reason
        self.w.serial_worker = MagicMock()
        previous = self.w._generator_config()
        self.s.set_mode(3)
        self.s.bode.deadline = 0
        self.s.render()
        self.assertFalse(self.s.bode.active)
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0],previous)
        self.w._generator_requested = None
        self.s.bode.begin()
        config = self.s.bode.config
        self.s.bode.confirmed(GeneratorReply(0x80000000,Phase.APPLIED,Reason.OK,True,config,config))
        self.s.bode.batch([{'Tiempo (us)':0,'V_IN':1.5,'V_OUT':1.5},
                          {'Tiempo (us)':2000,'V_IN':1.5,'V_OUT':1.5}])
        self.assertFalse(self.s.bode.active)
        self.assertIn('Discontinuidad',self.s.bode.status.text())
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0],previous)

    def test_bode_restores_exact_confirmed_dac_codes_not_rounded_ui(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorConfig, GeneratorReply
        from transport.unoq_switch import Phase, Reason
        self.w.serial_worker = MagicMock()
        original = GeneratorConfig(frequency=79000,final_frequency=20000000,
                                   low=310,high=4033,duration=10000)
        self.w._generator_confirmed(GeneratorReply(0x80000000,Phase.APPLIED,Reason.OK,True,original,original))
        self.s.set_mode(3)
        self.assertTrue(self.s.bode.active)
        self.s.bode.cancel()
        self.assertEqual(self.w.serial_worker.request_generator.call_args.args[0], original)

    def test_bode_does_not_start_before_generator_status_is_known(self):
        from unittest.mock import MagicMock
        self.w.serial_worker = MagicMock()
        self.w._generator_state_known = False
        self.s.set_mode(3)
        self.assertFalse(self.s.bode.active)
        self.w.serial_worker.request_generator.assert_not_called()

    def test_decade_density_and_exact_selected_end(self):
        from monitor.v10.bode import decade_frequencies
        f = decade_frequencies(2,2000,10)
        self.assertEqual(len(f),31)
        self.assertEqual(f[0],2)
        self.assertEqual(f[-1],2000)
        partial = decade_frequencies(2,1234,10)
        self.assertEqual(partial[-1],1234)
        self.assertTrue(np.all(np.diff(partial)>0))

    def test_weak_tones_do_not_stop_before_selected_end(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorReply
        from transport.unoq_switch import Phase, Reason
        self.w.serial_worker=MagicMock()
        b=self.s.bode
        b.start.setValue(100); b.end.setValue(1000); b.points.setValue(1); b.settle.setValue(20)
        self.s.set_mode(3)
        cursor=0
        while b.active:
            config=b.config
            b.confirmed(GeneratorReply(0x80000000,Phase.APPLIED,Reason.OK,True,config,config))
            idx=np.arange(cursor,cursor+5000);cursor+=5000
            b.batch([{'Tiempo (us)':i/31250*1e6,'V_IN':1.65,'V_OUT':1.65} for i in idx])
        self.assertEqual(b.result[-1][0],1000)
        self.assertEqual(len(b.invalid_points),2)
        self.assertTrue(np.isnan(b.result[-1][1]))
        np.testing.assert_allclose(self.s.plots[0].getViewBox().viewRange()[0],[2,3])

    def test_fft_shared_scales_and_margin_hysteresis(self):
        self.s.set_mode(1); self.s.lock_axes.setChecked(True); self.feed()
        a=self.s.plots[0].getViewBox().viewRange()[1]
        b=self.s.plots[1].getViewBox().viewRange()[1]
        np.testing.assert_allclose(a,b)
        self.s.reset()
        initial=self.s.stable_range(0,[np.array([-50.,0.])])
        self.assertLess(initial[0],-50)
        self.assertGreater(initial[1],0)
        small=self.s.stable_range(0,[np.array([-49.,-1.])])
        self.assertEqual(initial,small)
        with patch('monitor.v10.spectrum.time.monotonic',return_value=10):
            self.s.stable_range(0,[np.array([-20.,-15.])])
        with patch('monitor.v10.spectrum.time.monotonic',return_value=14):
            reduced=self.s.stable_range(0,[np.array([-20.,-15.])])
        self.assertLess(reduced[1]-reduced[0],initial[1]-initial[0])

    def test_bode_log_toggle_keeps_results_and_does_not_restart(self):
        from unittest.mock import MagicMock
        self.w.serial_worker=MagicMock()
        self.s.bode.start.setValue(100)
        self.s.bode.end.setValue(1000)
        self.s.set_mode(3)
        self.s.bode.result=[(100,-20,-45),(1000,float('-inf'),float('nan'))]
        self.s.bode.draw()
        calls=self.w.serial_worker.request_generator.call_count
        self.s.bode.log_frequency.setChecked(False)
        self.assertFalse(self.s.plots[0].getAxis('bottom').logMode)
        np.testing.assert_allclose(self.s.plots[0].getViewBox().viewRange()[0],[100,1000])
        self.assertEqual(len(self.s.bode.result),2)
        self.assertTrue(np.isfinite(self.s.curves[0].yData[-1]))
        self.s.bode.log_frequency.setChecked(True)
        self.assertTrue(self.s.plots[0].getAxis('bottom').logMode)
        np.testing.assert_allclose(self.s.plots[0].getViewBox().viewRange()[0],[2,3])
        self.assertEqual(self.w.serial_worker.request_generator.call_count,calls)

    def test_settling_is_independent_of_frequency_and_cycles(self):
        b=self.s.bode
        b.settle.setValue(50);b.cycles.setValue(2)
        self.assertEqual(b.timing(.1,31250),(.05,20))
        self.assertEqual(b.timing(100,31250),(.05,.02))
        b.settle.setValue(0)
        self.assertEqual(b.timing(100,31250),(0,.02))
        self.assertEqual(b.timing(20000,50000),(0,32/50000))

    def test_estimate_and_deadline_use_selected_timing(self):
        from unittest.mock import MagicMock
        from transport.unoq_generator import GeneratorReply
        from transport.unoq_switch import Phase, Reason
        b=self.s.bode
        b.start.setValue(.1);b.end.setValue(1);b.points.setValue(1)
        b.settle.setValue(0);b.cycles.setValue(2)
        self.assertIn('22.0 s',b.estimate.text())
        self.w.serial_worker=MagicMock();self.s.set_mode(3)
        config=b.config
        with patch('monitor.v10.bode.time.monotonic',return_value=100):
            b.confirmed(GeneratorReply(0x80000000,Phase.APPLIED,Reason.OK,True,config,config))
        self.assertEqual(b.deadline,130)
        self.assertFalse(b.cycles.isEnabled())
        b.cancel()
        self.assertTrue(b.cycles.isEnabled())

    def test_equal_point_density_in_low_and_high_decades(self):
        from monitor.v10.bode import decade_frequencies
        frequencies=decade_frequencies(20,20000,10)
        for low in (20,200,2000):
            selected=frequencies[(frequencies>=low)&(frequencies<10*low)]
            self.assertEqual(len(selected),10)
            np.testing.assert_allclose(np.diff(np.log10(selected)),.1,atol=1e-5)
        self.s.set_mode(3)
        self.s.bode.result=[(20,-1,-10),(200,-10,-30),(2000,-20,-60)]
        self.s.bode.draw()
        self.assertEqual(self.s.curves[0].opts['symbol'],'o')
        self.s.set_mode(1)
        self.assertIsNone(self.s.curves[0].opts['symbol'])

    def test_curve_markers_distinguish_gain_from_undefined_phase(self):
        b=self.s.bode
        self.s.set_mode(3)
        b.result=[(100,-20,-45),(200,-60,float('nan')),(1000,float('-inf'),float('nan'))]
        b.draw()
        self.assertEqual(len(self.s.curves[0].xData),3)
        self.assertEqual(self.s.curves[0].opts['symbol'],'o')
        self.assertEqual(b.coverage.text(),'Ganancia: 3/3 · Fase: 1/3')

    def test_bode_add_preserves_five_curves_and_repeat_clears(self):
        from unittest.mock import MagicMock
        b = self.s.bode
        self.w.serial_worker = MagicMock()
        self.s.set_mode(3)
        for index in range(5):
            b.result[:] = [(100, -index, -10), (1000, -index-10, -45)]
            b.draw()
            b.cancel()
            self.w._generator_requested = None
            if index < 4:
                b.add_button.click()
                self.assertTrue(b.active)
                self.assertEqual(len(b.history), index+1)
        self.assertFalse(b.add_button.isEnabled())
        for index, curves in enumerate(b.curve_sets):
            self.assertEqual(len(curves[0].xData), 2)
            self.assertEqual(curves[0].opts['symbolBrush'], self.w.channel_palette[index])
        b.begin(add=True)
        self.assertFalse(b.active)
        b.button.click()
        self.assertTrue(b.active)
        self.assertEqual(b.history, [])
        self.assertEqual(b.result, [])
        self.assertTrue(all(curve.xData is None for curves in b.curve_sets for curve in curves))
        b.cancel()
        self.assertTrue(b.add_button.isEnabled())

    def test_added_bode_curves_hide_in_fft(self):
        self.s.set_mode(3)
        b = self.s.bode
        b.history = [[(100,-1,-10),(1000,-10,-45)]]
        b.result = [(100,-2,-20),(1000,-20,-60)]
        b.draw()
        self.s.set_mode(1)
        self.assertTrue(all(not curve.isVisible() for curves in b.curve_sets[1:] for curve in curves))
        self.assertTrue(all(not curve.isVisible() for curves in b.shadows for curve in curves))

    def test_bode_shadows_follow_color_data_and_repeat(self):
        self.s.set_mode(3)
        b=self.s.bode
        b.result=[(100,-1,-10),(1000,-10,-45)]
        b.draw()
        for curve,shadow in zip(b.curve_sets[0],b.shadows[0]):
            np.testing.assert_array_equal(curve.xData,shadow.xData[1:3])
            np.testing.assert_array_equal(curve.yData,shadow.yData[1:3])
            brush=shadow.opts['fillBrush']
            self.assertEqual(brush.color().name(),self.w.channel_palette[0])
            self.assertEqual(brush.color().alpha(),38)
            self.assertEqual(shadow.opts['fillLevel'],'enclosed')
            self.assertLess(shadow.yData[0],float(np.min(curve.yData)))
            self.assertLess(shadow.zValue(),curve.zValue())
