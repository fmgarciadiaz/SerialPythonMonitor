"""Qt regressions for real FFT controls, histories, and frozen captures."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt6'
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.historico.v14.app import SerialMonitorWindow


class FftWidgetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setStyle('Fusion')

    def setUp(self):
        with patch('monitor.historico.v14.app.usb_devices',return_value=[]): self.w = SerialMonitorWindow()
        self.w.current_fs_hz = 40000
        self.s = self.w.spectral
        self.s.size.setCurrentText('1024')
        self.s.set_mode(1)

    def tearDown(self): self.w.close()

    def test_preparation_disconnect_retries_without_blocking_gui(self):
        self.w._preparing_disconnect = True
        with patch.object(self.w,'stop_input',return_value=False) as stop,patch('monitor.historico.v14.app.QtCore.QTimer.singleShot') as timer,patch('monitor.historico.v14.app.QPreparationThread') as factory:
            self.w._begin_q_preparation('q')
            stop.assert_called_once_with(wait=False)
            self.assertEqual(timer.call_args.args[0],100)
            factory.assert_not_called()
        with patch.object(self.w,'stop_input',return_value=None),patch('monitor.historico.v14.app.QPreparationThread') as factory:
            self.w._begin_q_preparation('q')
            factory.return_value.start.assert_called_once()
            self.assertFalse(self.w._preparing_disconnect)
        self.w._q_preparation = None

    def test_cancel_preparation_warning_keeps_acquisition_untouched(self):
        with patch.object(self.w.port_combo,'currentData',return_value='q'),patch('monitor.historico.v14.app.QtWidgets.QMessageBox.warning',return_value=QtWidgets.QMessageBox.StandardButton.Cancel) as warning,patch.object(self.w,'stop_input') as stop:
            self.w.prepare_q()
            warning.assert_called_once()
            self.assertIn('varios minutos',warning.call_args.args[2])
            stop.assert_not_called()
            self.assertIsNone(self.w._q_preparation)

    def feed(self,count=10000,start=0,zero_out=False):
        t = np.arange(start,start+count)/40000
        x = 1.65+np.sin(2*np.pi*997.3*t)+.03*np.sin(4*np.pi*997.3*t)
        y = np.zeros(count) if zero_out else 1.65+.5*np.sin(2*np.pi*997.3*t-.2)
        rows = [{'Muestra':int(i+1),'Tiempo (us)':int(i*25),'ADC_IN':100,'V_IN':float(vx),'ADC_OUT':50,'V_OUT':float(vy)} for i,vx,vy in zip(range(start,start+count),x,y)]
        self.w.handle_batch(rows)

    def render(self):
        self.s.last_fast_render=0; self.s.render(); self.app.processEvents()
        if self.s.fft_mode.currentText() == 'Distort' and self.s._distortion_future is not None:
            self.s._distortion_future.result(timeout=10)
            self.s.last_fast_render=0;self.s.render();self.app.processEvents()

    def test_spectre_peak_and_power_band_annotations(self):
        self.feed();self.render()
        label = self.s.harmonic_labels[0][0]
        self.assertTrue(label.isVisible())
        self.assertIn('f pico',label.toPlainText())
        self.assertNotIn('dBc',label.toPlainText())
        self.s.fft_mode.setCurrentText('Power');self.render()
        band,floor,caption = self.s.power_annotations[0]
        self.assertTrue(band.isVisible())
        self.assertTrue(floor.isVisible())
        self.assertIn('V RMS',caption.toPlainText())
        self.assertFalse(label.isVisible())
        self.s.fft_mode.setCurrentText('Distort')
        self.assertFalse(band.isVisible())
        self.assertFalse(floor.isVisible())
        self.assertFalse(caption.isVisible())

    def test_power_band_drag_syncs_controls_and_preserves_distort_band(self):
        self.feed();self.s.fft_mode.setCurrentText('Power');self.render()
        self.assertEqual((self.s.band_low.value(),self.s.band_high.value()),(100,500))
        region = self.s.power_annotations[0][0]
        region.setRegion((150,650))
        self.assertEqual((self.s.band_low.value(),self.s.band_high.value()),(150,650))
        self.render()
        self.s.log_frequency.setChecked(True);self.render()
        region.setRegion((np.log10(200),np.log10(800)))
        self.assertEqual((self.s.band_low.value(),self.s.band_high.value()),(200,800))
        self.s.fft_mode.setCurrentText('Distort')
        self.assertEqual((self.s.band_low.value(),self.s.band_high.value()),(0,0))
        self.s.fft_mode.setCurrentText('Power')
        self.assertEqual((self.s.band_low.value(),self.s.band_high.value()),(200,800))

    def test_secondary_selector_and_size_are_independent_per_mode(self):
        self.assertEqual(self.s.secondary_label.text(),'Modo FFT')
        self.assertIs(self.s.secondary_stack.currentWidget(),self.s.fft_mode)
        self.s.size.setCurrentText('4096')
        self.assertEqual(self.s.heatmap_size.currentText(),'4096')
        self.s.set_mode(2)
        self.assertIs(self.s.secondary_stack.currentWidget(),self.s.heatmap_size)
        self.s.heatmap_size.setCurrentText('512')
        self.assertEqual(self.s.size.currentText(),'512')
        self.s.set_mode(3)
        self.assertIs(self.s.secondary_stack.currentWidget(),self.s.bode_method_combo)

    def test_all_fft_modes_render_and_preserve_raw_histories(self):
        self.feed();before = self.w.series['V_IN'][:]
        for index,name in enumerate(('Spectre','Power','Distort','Transfer')):
            self.s.fft_mode.setCurrentIndex(index);self.render()
            self.assertIn(name,self.s.info.text())
            self.assertIsNotNone(self.s.analysis_result)
            if name == 'Distort':
                self.assertIn('SINAD',self.s.metrics.text())
                self.assertIn('THD',self.s.summary_labels[0].toPlainText())
                self.assertAlmostEqual(self.s.analysis_result[0].distortion['thd'],.03,delta=.001)
            self.assertTrue(self.s.summary_labels[0].toPlainText())
            x,y = self.s.curves[0].getData()
            self.assertGreater(len(x),0);self.assertEqual(len(x),len(y))
            np.testing.assert_array_equal(self.w.series['V_IN'][:],before)
            self.assertEqual(self.w.sample_counter,10000)

    def test_plot_headers_select_channels_and_remain_reachable_when_hidden(self):
        self.w.show();self.app.processEvents()
        self.feed();self.render()
        self.assertEqual(self.s.header_attached,{0,1})
        self.assertIs(self.s.channels[0].parentWidget(),self.s.plot_headers[0].widget())
        self.assertEqual(self.s.settings_form.getWidgetPosition(self.s.channels[0])[0],-1)
        self.s.channels[0].setCurrentText('V_OUT');self.render()
        self.assertEqual(self.s.channels[0].property('selectedTextColor'),self.w.channel_colors['V_OUT'])
        self.s.channels[0].setCurrentText('Ninguno');self.render()
        self.assertNotIn(0,self.s.attached)
        self.assertIn(0,self.s.header_attached)
        self.assertTrue(self.s.plot_headers[0].isVisible())
        self.s.channels[0].setCurrentText('V_IN');self.render()
        self.assertIn(0,self.s.attached)
        self.s.set_mode(2)
        self.assertEqual(self.s.header_labels[0].text(),'· Heatmap')
        self.s.set_mode(3)
        self.assertFalse(self.s.header_attached)
        self.s.set_mode(1);self.s.fft_mode.setCurrentText('Transfer')
        self.assertFalse(self.s.header_attached)
        self.assertIn('V_OUT / V_IN',self.s.plots[0].titleLabel.text)

    def test_distortion_marks_fitted_harmonics_and_clears_other_modes(self):
        self.w.resize(1500,950);self.w.show();self.app.processEvents()
        self.feed();self.s.fft_mode.setCurrentText('Distort');self.render()
        visible = [label.toPlainText() for label in self.s.harmonic_labels[0] if label.isVisible()]
        self.assertTrue(any('f₀' in text for text in visible))
        self.assertTrue(any('H2' in text and 'dBc' in text for text in visible))
        frequencies,levels = self.s.harmonic_points[0].getData()
        self.assertGreaterEqual(len(frequencies),2)
        self.assertAlmostEqual(frequencies[1]/frequencies[0],2,places=8)
        self.assertAlmostEqual(levels[1]-levels[0],20*np.log10(.03),delta=.02)
        self.s.log_frequency.setChecked(True);self.render()
        for label in self.s.harmonic_labels[0]:
            if label.isVisible() and 'f₀' in label.toPlainText():
                self.assertAlmostEqual(label.pos().x(),np.log10(frequencies[0]),places=6)
        self.s.fft_mode.setCurrentText('Spectre');self.render()
        visible = [label.toPlainText() for labels in self.s.harmonic_labels for label in labels if label.isVisible()]
        self.assertTrue(visible)
        self.assertTrue(all('f pico' in text and 'dBc' not in text for text in visible))
        self.assertEqual(len(self.s.harmonic_points[0].getData()[0]),1)

    def test_phase_psd_and_transfer_views_have_correct_axes(self):
        self.feed();self.s.spectrum_view.setCurrentIndex(1);self.render()
        self.assertIn('Fase',self.s.plots[0].getAxis('left').labelText)
        self.s.fft_mode.setCurrentIndex(1);self.render()
        self.assertEqual(self.s.plots[0].getAxis('left').labelUnits,'dB re 1 V²/Hz')
        self.s.fft_mode.setCurrentIndex(3)
        for index,unit in ((0,'°'),(1,''),(2,'s')):
            self.s.transfer_view.setCurrentIndex(index);self.render()
            self.assertEqual(self.s.plots[1].getAxis('left').labelUnits,unit)

    def test_single_snapshot_supports_all_modes_and_transfer_na(self):
        self.feed();self.assertTrue(self.s.capture_single(7000));self.w.is_running=False
        snapshot = self.s._single_snapshot
        x = snapshot.series['V_IN'][:].copy()
        self.feed(2000,start=10000)
        for index in range(4):
            self.s.fft_mode.setCurrentIndex(index);self.app.processEvents()
            self.assertIs(self.s._single_snapshot,snapshot)
            self.assertEqual(self.s.last_end,1024)
            self.assertTrue(all(marker.isVisible() for marker in self.s.single_markers))
            np.testing.assert_array_equal(snapshot.series['V_IN'][:],x)
        result = self.s.analysis_result[0]
        self.assertEqual(result['segments'],1)
        self.assertTrue(np.all(np.isnan(result['coherence'])))
        self.s.transfer_view.setCurrentIndex(1);self.app.processEvents()
        self.assertIn('un segmento',self.s.summary_labels[1].toPlainText())

    def test_run_and_clear_do_not_resurrect_single_snapshot(self):
        self.feed();self.assertTrue(self.s.capture_single(7000));self.w.is_running=False
        self.w.run_stop_btn.setChecked(True);self.w.toggle_run_stop()
        self.assertIsNone(self.s._single_snapshot)
        self.w.is_running=False;self.s.fft_mode.setCurrentIndex(1);self.app.processEvents()
        self.assertIsNone(self.s._single_snapshot)
        self.w.clear_data()
        self.assertIsNone(self.s._single_snapshot)

    def test_invalid_single_timestamps_are_not_marked_captured(self):
        self.feed()
        self.w.series['Tiempo (us)'].clear();self.w.series['Tiempo (us)'].extend(np.zeros(10000))
        self.assertFalse(self.s.capture_single(7000))
        self.assertIsNone(self.s._single_snapshot)
        self.assertFalse(any(marker.isVisible() for marker in self.s.single_markers))

    def test_missing_and_zero_channels_have_explicit_status(self):
        self.feed(zero_out=True);self.s.fft_mode.setCurrentIndex(3);self.render()
        self.assertIn('salida cero',self.s.summary_labels[0].toPlainText())
        self.s.fft_mode.setCurrentIndex(0)
        for channel in self.s.channels: channel.setCurrentIndex(0)
        self.render()
        self.assertIn('V_IN',self.s.statistics_by_channel)
        self.assertNotEqual(self.w._measurement_values[0].text(),'N/A')
        self.assertTrue(self.s.capture_single(7000))

    def test_measurement_cards_follow_fft_mode_and_restore_time_labels(self):
        self.s.set_mode(0)
        self.w.meas_channel_combo.setCurrentText('ADC_OUT')
        self.s.set_mode(1)
        self.feed()
        for mode, title in [('Spectre','F DOMINANTE'),('Power','V RMS'),('Distort','F FUNDAMENTAL'),('Transfer','F REFERENCIA')]:
            self.s.fft_mode.setCurrentText(mode);self.render()
            self.assertEqual(self.w._measurement_cards[0].layout().itemAt(0).widget().text(),title)
            self.assertFalse(any(label.isVisible() for label in self.s.summary_labels))
            self.assertFalse(self.s.metrics.isVisible())
            self.assertEqual(self.w._measurement_cards[6].isHidden(),mode != 'Power')
            self.assertNotEqual(self.w._measurement_values[0].text(),'N/A')
        self.assertEqual(self.w.meas_channel_combo.currentText(),'OUT / IN')
        self.assertFalse(self.w.meas_channel_combo.isEnabled())
        self.s.set_mode(0)
        self.assertEqual(self.w._measurement_cards[0].layout().itemAt(0).widget().text(),'V MAX')
        self.assertTrue(self.w.meas_channel_combo.isEnabled())
        self.assertEqual(self.w.meas_channel_combo.currentText(),'ADC_OUT')

    def test_measurement_input_changes_without_recomputing_or_overwriting_fft(self):
        self.feed();self.render()
        original = self.w._measurement_values[1].text()
        result = self.s.analysis_result
        self.w.meas_channel_combo.setCurrentText('V_OUT')
        self.assertNotEqual(self.w._measurement_values[1].text(),original)
        self.assertIs(self.s.analysis_result,result)
        selected = [v.text() for v in self.w._measurement_values]
        self.w._update_live_measurements({'V_OUT':np.ones(100)*3},['V_OUT'])
        self.assertEqual([v.text() for v in self.w._measurement_values],selected)
        self.assertTrue(self.s.capture_single(7000));self.w.is_running=False
        snapshot = self.s._single_snapshot
        self.w.meas_channel_combo.setCurrentText('V_IN')
        self.assertIs(self.s._single_snapshot,snapshot)
        self.assertNotEqual(self.w._measurement_values[1].text(),'N/A')

    def test_hidden_plot_channel_can_be_selected_for_statistics(self):
        self.s.channels[1].setCurrentText('Ninguno')
        self.feed();self.render()
        self.w.meas_channel_combo.setCurrentText('V_OUT');self.render()
        self.assertIn('V_OUT',self.s.statistics_by_channel)
        self.assertNotEqual(self.w._measurement_values[1].text(),'N/A')
        hidden = self.s.curves[1].getData()[0]
        self.assertTrue(hidden is None or len(hidden)==0)

    def test_distortion_plot_refreshes_without_waiting_for_fit(self):
        self.feed();self.s.fft_mode.setCurrentIndex(2)
        with patch('monitor.historico.v14.spectrum.time.monotonic',return_value=10):self.s.render()
        end = self.s.last_end
        self.feed(100,start=10000)
        with patch('monitor.historico.v14.spectrum.time.monotonic',return_value=10.1):self.s.render()
        self.assertEqual(self.s.last_end,10100)
        self.assertEqual(self.s._distortion_submitted,10)
        with patch('monitor.historico.v14.spectrum.time.monotonic',return_value=10.21):self.s.render()
        self.assertEqual(self.s.last_end,10100)

    def test_distortion_pending_job_does_not_block_or_queue_more_fits(self):
        from concurrent.futures import Future
        self.feed();self.s.fft_mode.setCurrentText('Distort');self.render()
        pending = Future()
        self.s._distortion_future = pending
        self.s._distortion_job_generation = self.s._distortion_generation
        self.s._distortion_submitted = 0
        self.feed(100,start=10000)
        with patch('monitor.historico.v14.spectrum.analysis.distortion',side_effect=AssertionError('Fit on UI thread')):
            self.s.last_fast_render=0;self.s.render()
        self.assertEqual(self.s.last_end,10100)
        self.assertIs(self.s._distortion_future,pending)
        self.assertGreater(len(self.s.curves[0].getData()[0]),0)
        self.s.reset()
        pending.set_result({'V_IN':{'valid':False,'reason':'stale'}})
        with patch.object(self.s._distortion_executor,'submit',return_value=Future()):
            fitted = self.s._live_distortion({},40000,{'n':1024},False)
        self.assertEqual(fitted,{})

    def test_gap_restarts_welch_from_contiguous_post_gap_samples(self):
        self.feed(4500)
        times = self.w.series['Tiempo (us)'][:]
        times[3000:] += 1000
        self.w.series['Tiempo (us)'].clear();self.w.series['Tiempo (us)'].extend(times)
        self.render()
        self.assertEqual(self.s.analysis_result[0].segments,1)
        self.assertIn('1/4 segmentos reales',self.s.info.text())
        self.assertEqual(len(self.s.frames),1)


if __name__ == '__main__': unittest.main()
