import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v17.app import SerialMonitorWindow
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.radio_stream import AudioResampler, RadioStream
from monitor.v17.radio_am import RadioConfig


class RadioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        with patch('monitor.v17.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()

    def tearDown(self):self.w.close()

    def audio_history(self, rate=40000, tone=1000):
        self.w.filter_source.setCurrentText('RADIO')
        self.w.radio_stream=RadioStream(RadioConfig(160000000/114,550000),rate)
        t=np.arange(12000)/rate
        audio=.3*np.sin(2*np.pi*tone*t)
        self.w.radio_stream.append(audio,audio*.5)
        self.w.h_scale=1000
        self.w.current_fs_hz=160000000/114
        for name,action in self.w.graph_channel_actions.items():action.setChecked(name=='RADIO')
        self.w.meas_channel_combo.setCurrentText('RADIO')
        return audio

    def mixed_history(self):
        from monitor.v17.processing import BatchProcessor
        from monitor.v17.numeric_batch import NumericBatch,SampleClock
        config=Configuration(8,1403508)
        self.w._acquisition_confirmed(config.bits,config.rate)
        self.w.radio_frequency.setValue(50)
        self.w.radio_enabled.setChecked(True)
        self.w.filter_source.setCurrentText('RADIO')
        self.w.filter_mode.setCurrentIndex(self.w.filter_mode.findData('bypass'))
        count=int(config.actual_rate*.12);t=np.arange(count)/config.actual_rate
        rf=1.65+.6*(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*50000*t)
        raw=np.zeros((count,4),np.uint32)
        raw[:,0]=1000000+np.arange(count)*config.period;raw[:,3]=np.arange(count)
        raw[:,1]=np.rint(rf*config.maximum/3.3).astype(np.uint32)
        batch=NumericBatch(raw,config.maximum,SampleClock(config.timestamp_hz),1);batch.acquisition=config
        BatchProcessor().process(batch,self.w._processing_settings())
        self.w.handle_batch(batch)
        self.w.x_axis_time_mode=True;self.w.on_h_scale_changed(int(config.actual_rate*.01))
        self.w.trigger_checkbox.setChecked(False)
        for name,action in self.w.graph_channel_actions.items():action.setChecked(name in ('CH1','RADIO','FILTER'))
        return config

    def test_mixed_rf_audio_are_visible_on_common_time_without_resampling(self):
        config=self.mixed_history();self.w.render_frame()
        x,values,channels=self.w._last_display_frame
        self.assertIsInstance(x,dict)
        for name in ('CH1','RADIO','FILTER'):
            self.assertIn(name,channels);self.assertTrue(self.w.line_items[name].isVisible())
            self.assertEqual(len(x[name]),len(values[name]))
        self.assertIs(x['RADIO'],x['FILTER'])
        self.assertGreater(len(x['CH1']),20*len(x['RADIO']))
        np.testing.assert_allclose(np.diff(x['CH1']),1e6/config.actual_rate,atol=1e-8)
        np.testing.assert_allclose(np.diff(x['RADIO']),25,atol=1e-8)
        self.assertGreater(self.w.radio_stream.series['Tiempo (us)'][0],0)
        self.w.detail_slider.setValue(25)
        self.assertTrue(self.w.line_items['CH1'].isVisible())
        self.assertTrue(self.w.line_items['RADIO'].isVisible())

    def test_mixed_old_position_copies_only_visible_interval(self):
        config=self.mixed_history();self.w.h_pos=-int(config.actual_rate*.04)
        clock=self.w.series['Tiempo (us)'];full=clock.window(0,len(clock))
        end=min(clock[-1],self.w.radio_stream.series['Tiempo (us)'][-1])
        right=end+self.w.h_pos*1e6/config.actual_rate
        left=right-self.w.h_scale*1e6/config.actual_rate
        a,b=np.searchsorted(full,left,'left'),np.searchsorted(full,right,'right')
        with patch.object(clock,'window',wraps=clock.window) as read:
            self.w.render_frame()
        self.assertEqual(read.call_count,1)
        self.assertEqual(read.call_args.args,(a,b))
        np.testing.assert_array_equal(self.w._last_display_frame[0]['CH1'],full[a:b]-left)
        frozen=self.w._last_display_frame[0]['CH1'].copy()
        clock.extend(full+1000000)
        np.testing.assert_array_equal(self.w._last_display_frame[0]['CH1'],frozen)

    def test_mixed_trigger_outlier_matches_reference_both_edges(self):
        from monitor.v17.history import SampleHistory
        self.mixed_history();stream=self.w.radio_stream
        times=stream.series['Tiempo (us)'].window(0,stream.counter)
        audio=1.65+1e-6*np.sin(np.arange(stream.counter))
        audio[len(audio)//2]=1.60;audio[len(audio)//2+20]=1.70
        stream.series['RADIO']=SampleHistory(stream.counter);stream.series['RADIO'].extend(audio)
        self.w.trigger_source_combo.setCurrentText('RADIO')
        self.w.dial_trigger_level.setValue(165);self.w.trigger_checkbox.setChecked(True)
        duration=self.w.h_scale*1e6/self.w.applied_configuration.actual_rate
        start=max(self.w.series['Tiempo (us)'][0],times[0])
        end=min(self.w.series['Tiempo (us)'][-1],times[-1])
        for rising,edge in ((True,'Ascendente'),(False,'Descendente')):
            self.w.trigger_edge=edge
            crosses=np.flatnonzero(((audio[1:]>=1.65)&(audio[:-1]<1.65)) if rising else ((audio[1:]<=1.65)&(audio[:-1]>1.65)))+1
            expected=None
            for i in crosses[::-1]:
                fraction=(1.65-audio[i-1])/(audio[i]-audio[i-1])
                crossing=times[i-1]+fraction*(times[i]-times[i-1])
                prior=audio[max(0,i-10):i]
                if start+duration*.1<=crossing<=end-duration*.9 and (np.min(prior)<=1.635 if rising else np.max(prior)>=1.665):
                    expected=crossing;break
            self.assertIsNotNone(expected);self.w.render_frame()
            x=self.w._last_display_frame[0]['RADIO']
            self.assertAlmostEqual(x[0]+expected,times[np.searchsorted(times,expected-duration*.1)])

    def test_mixed_tiny_noise_does_not_trigger_or_hide_rf(self):
        from monitor.v17.history import SampleHistory
        self.mixed_history()
        stream=self.w.radio_stream
        audio=1.65+1e-6*np.sin(np.arange(stream.counter))
        stream.series['RADIO']=SampleHistory(stream.counter)
        stream.series['RADIO'].extend(audio)
        self.w.trigger_source_combo.setCurrentText('RADIO')
        self.w.dial_trigger_level.setValue(165);self.w.trigger_checkbox.setChecked(True)
        self.w.render_frame()
        self.assertIn('buscando',self.w.trigger_status_label.text())
        self.assertTrue(self.w.line_items['CH1'].isVisible())
        self.assertTrue(self.w.line_items['RADIO'].isVisible())

    def test_mixed_trigger_rf_audio_single_and_preparing_keep_rf(self):
        self.mixed_history()
        stream=self.w.radio_stream;self.w.radio_stream=None;self.w.render_frame()
        self.assertTrue(self.w.line_items['CH1'].isVisible())
        self.w.radio_stream=stream
        for source in ('CH1','RADIO'):
            self.w.trigger_source_combo.setCurrentText(source)
            self.w.dial_trigger_level.setValue(165)
            self.w.trigger_checkbox.setChecked(True);self.w.render_frame()
            self.assertIn('Disparo',self.w.trigger_status_label.text())
            self.assertTrue(self.w.line_items['CH1'].isVisible())
            self.assertTrue(self.w.line_items['RADIO'].isVisible())
        self.w.arm_single_shot();self.w.render_frame()
        self.assertFalse(self.w.single_shot_armed);self.assertFalse(self.w.is_running)
        self.w.detail_slider.setValue(25)
        self.assertTrue(self.w.line_items['RADIO'].isVisible())

    def test_temporal_audio_frequency_uses_audio_rate(self):
        for rate in (20000,40000,48000):
            self.audio_history(rate,tone=1500)
            self.w._last_measurement_update=0
            self.w.render_frame()
            self.assertIn('1.50',self.w.val_freq.text().replace(',','.'))
            self.assertIn('kHz',self.w.val_freq.text())
            self.assertEqual(self.w.current_fs_hz,160000000/114)
            self.w.meas_channel_combo.setCurrentText('FILTER')
            self.w._last_measurement_update=0
            self.w.render_frame()
            self.assertIn('1.50',self.w.val_freq.text().replace(',','.'))

    def test_radio_measurement_uses_audio_when_rf_is_visible(self):
        self.audio_history(tone=1500)
        self.w.graph_channel_actions['RADIO'].setChecked(False)
        self.w.graph_channel_actions['CH1'].setChecked(True)
        self.w._last_measurement_update=0
        rf=np.sin(2*np.pi*np.arange(1000)/4)
        self.w._update_live_measurements({'CH1':rf,'Tiempo (us)':np.arange(1000)*.7125},['CH1'])
        self.assertIn('1.50',self.w.val_freq.text().replace(',','.'))

    def test_radio_trigger_edges_negative_level_and_single(self):
        self.audio_history()
        self.w.trigger_source_combo.setCurrentText('RADIO')
        self.assertEqual(self.w.trigger_level,0)
        self.assertEqual(self.w.dial_trigger_level.minimum(),-330)
        self.w.trigger_checkbox.setChecked(True)
        self.w.x_axis_time_mode=True
        for edge in ('Ascendente','Descendente'):
            self.w.trigger_edge_combo.setCurrentText(edge)
            self.w.render_frame()
            self.assertIn('Disparo',self.w.trigger_status_label.text())
            x,values,_=self.w._last_display_frame
            crossing=np.searchsorted(x,0)
            y=values['RADIO']
            self.assertTrue(y[crossing]>=0 and y[crossing-1]<0 if edge=='Ascendente' else
                            y[crossing]<=0 and y[crossing-1]>0)
            self.assertAlmostEqual(float(np.interp(0,x,y)),0,places=12)
            np.testing.assert_allclose(np.diff(x),25)
        self.w.dial_trigger_level.setValue(-10)
        self.assertAlmostEqual(self.w.trigger_level,-.1)
        self.w.trigger_line.setValue(-.2)
        self.w._on_trigger_line_dragged()
        self.assertAlmostEqual(self.w.trigger_level,-.2)
        self.w.auto_center_trigger_level()
        self.assertAlmostEqual(self.w.trigger_level,0,places=6)
        self.w.arm_single_shot();self.w.render_frame()
        self.assertFalse(self.w.single_shot_armed)
        self.assertFalse(self.w.is_running)

    def test_radio_trigger_normal_waits_and_filter_source_works(self):
        self.audio_history()
        self.w.trigger_source_combo.setCurrentText('FILTER')
        self.w.trigger_checkbox.setChecked(True)
        self.w.mode_combo.setCurrentText('Normal')
        self.w.dial_trigger_level.setValue(100)
        self.w.render_frame()
        self.assertIsNone(self.w.frozen_frame)
        self.assertIn('Esperando',self.w.trigger_status_label.text())
        self.w.dial_trigger_level.setValue(0)
        self.w.render_frame()
        self.assertIn('Disparo',self.w.trigger_status_label.text())

    def test_rf_and_audio_trigger_render_match_original_search(self):
        from monitor.v17.history import SampleHistory
        from tests.v17.test_trigger import reference_crossing
        count=12000
        self.audio_history()
        t=np.arange(count)
        self.w.handle_batch([{'Muestra':int(i+1),'Tiempo (us)':int(i*25),
                              'CH1':1.65,'CH2':1.65} for i in t])
        self.w.trigger_enabled=True;self.w.h_scale=1000
        for source,offset in (('CH1',1.65),('RADIO',0.)):
            for name,action in self.w.graph_channel_actions.items():action.setChecked(name==source)
            self.w.trigger_source_combo.setCurrentText(source)
            self.w.trigger_level=offset
            for case in ('AM','noise_outlier','NaN'):
                values=offset+.3*np.sin(t*.17)*(1+.5*np.sin(t*.003))
                if case=='noise_outlier':
                    values=offset+1e-6*np.sin(t)
                    values[3000]=offset-.5;values[3020]=offset+.5
                if case=='NaN':values[::13]=np.nan
                histories=self.w.series if source=='CH1' else self.w.radio_stream.series
                history=SampleHistory(count);history.extend(values);histories[source]=history
                for edge in ('Ascendente','Descendente'):
                    self.w.trigger_edge=edge
                    for mode in ('Auto','Normal','Single'):
                        with self.subTest(source=source,case=case,edge=edge,mode=mode):
                            results=[]
                            for reference in (True,False):
                                self.w.h_scale=1000;self.w.h_pos=0
                                self.w.x_axis_time_mode=False
                                self.w.trigger_enabled=True
                                self.w.trigger_mode='Normal' if mode=='Normal' else 'Auto'
                                self.w.single_shot_armed=mode=='Single'
                                self.w.is_running=True;self.w.frozen_frame=None
                                self.w._last_display_frame=None
                                if reference:
                                    with patch('monitor.v17.app.last_trigger_crossing',side_effect=reference_crossing):
                                        self.w.render_frame()
                                else:self.w.render_frame()
                                frame=self.w._last_display_frame
                                results.append((frame,self.w.trigger_status_label.text(),self.w.single_shot_armed,self.w.is_running))
                            self.assertEqual(results[0][1:],results[1][1:])
                            if results[0][0] is None:self.assertIsNone(results[1][0])
                            else:
                                np.testing.assert_array_equal(results[0][0][0],results[1][0][0])
                                for channel in results[0][0][1]:
                                    np.testing.assert_array_equal(results[0][0][1][channel],results[1][0][1][channel])

    def test_fractional_trigger_aligns_both_edges_without_changing_samples(self):
        from monitor.v17.radio_stream import RadioTimeline
        self.audio_history()
        self.w.trigger_source_combo.setCurrentText('RADIO')
        self.w.trigger_checkbox.setChecked(True)
        self.w.x_axis_time_mode=True
        self.w.dial_trigger_level.setValue(8)
        self.w.h_scale=200
        for frequency in (1000,4000):
            for phase in (.13,.7,1.9):
                for edge in ('Ascendente','Descendente'):
                    with self.subTest(frequency=frequency,phase=phase,edge=edge):
                        source=.3*np.sin(2*np.pi*frequency*np.arange(3000)/40000+phase)
                        self.w.radio_stream=RadioTimeline(40000)
                        self.w.radio_stream.append(source,source*.5)
                        self.w.trigger_edge_combo.setCurrentText(edge)
                        self.w.render_frame()
                        x,values,_=self.w._last_display_frame
                        y=values['RADIO']
                        self.assertAlmostEqual(float(np.interp(0,x,y)),.08,places=12)
                        np.testing.assert_allclose(np.diff(x),25,atol=1e-10)
                        matches=np.flatnonzero(source==y[0])
                        self.assertTrue(any(np.array_equal(source[i:i+len(y)],y) for i in matches))
                        i=np.searchsorted(x,0)
                        self.assertGreater(y[i]-y[i-1],0) if edge=='Ascendente' else self.assertLess(y[i]-y[i-1],0)

    def test_radio_fft_single_keeps_audio_clock(self):
        self.audio_history()
        self.w.trigger_source_combo.setCurrentText('RADIO')
        self.w.spectral.set_mode(1)
        self.w.spectral.channels[0].setCurrentText('RADIO')
        self.w.spectral.channels[1].setCurrentText('Ninguno')
        self.w.spectral.size.setCurrentText('1024')
        self.w.arm_single_shot();self.w.render_frame()
        self.assertFalse(self.w.single_shot_armed)
        snapshot=self.w.spectral._single_snapshot
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.current_fs_hz,40000)
        spectrum=self.w.spectral.statistics_by_channel['RADIO']
        self.assertLess(abs(spectrum.frequencies[np.argmax(spectrum.amplitude)]-1000),40)

    def test_radio_tuning_tracks_all_ch1_profile_nyquist_limits(self):
        from monitor.v17.receiver.unoq_native import PROFILES
        from monitor.v17.radio_am import radio_tuning_max
        self.w.radio_enabled.setChecked(True)
        for p in PROFILES:
            if p['channels']!=1:continue
            config=Configuration(p['bits'],160000000//p['ticks'])
            self.w._acquisition_confirmed(config.bits,config.rate)
            maximum=radio_tuning_max(config.actual_rate)
            self.assertEqual(self.w.radio_frequency_dial.maximum(),maximum)
            self.assertLessEqual(self.w.radio_frequency.value()*1000,maximum)
            self.assertIn(f'AM CH1 · ADC{config.bits}',self.w.radio_input_badge.text())
            self.assertIn('MHz',self.w.radio_input_badge.text())
            self.assertTrue(self.w.radio_enabled.isChecked())
            self.assertEqual(self.w._processing_settings().acquisition,config)

    def test_panel_and_filter_follow_output_rate(self):
        self.assertEqual(self.w.radio_output_rate.currentData(),40000)
        self.assertGreaterEqual(self.w.trigger_filter_tabs.indexOf(self.w.radio_panel),0)
        self.w.filter_source.setCurrentText('RADIO')
        for rate in (20000,40000,48000):
            self.w.radio_output_rate.setCurrentIndex(self.w.radio_output_rate.findData(rate))
            self.assertEqual(self.w._filter_sample_rate(),rate)
            self.assertAlmostEqual(self.w.filter_upper.maximum(),rate*.49)
        self.w.filter_source.setCurrentText('CH1')
        self.assertEqual(self.w._filter_sample_rate(),self.w.applied_configuration.actual_rate)

    def test_filter_trigger_range_follows_source_domain(self):
        self.w.filter_source.setCurrentText('CH1')
        self.w.trigger_source_combo.setCurrentText('FILTER')
        self.assertEqual(self.w.trigger_level,1.65)
        self.w.filter_source.setCurrentText('RADIO')
        self.assertEqual(self.w.trigger_level,0)
        self.assertEqual(self.w.dial_trigger_level.minimum(),-330)
        self.w.filter_source.setCurrentText('CH1')
        self.assertEqual(self.w.trigger_level,1.65)
        self.assertEqual(self.w.dial_trigger_level.minimum(),0)

    def test_independent_radio_test_switches_preserve_frequency_and_update_playing(self):
        from unittest.mock import Mock
        from PyQt6 import QtTest
        from monitor.v17.receiver.unoq_generator import GeneratorReply
        from monitor.v17.receiver.unoq_switch import Phase,Reason
        self.w.generator_mode.setCurrentIndex(6)
        self.assertTrue(all(not switch.isEnabled() for switch in self.w.radio_test_switches))
        worker=Mock();self.w.serial_worker=worker
        config=self.w._radio_test_config(True)
        self.w._generator_confirmed(GeneratorReply(0x80000001,Phase.APPLIED,Reason.OK,True,config,config,
            radio_test_hz_capable=True,radio_test_independent_capable=True))
        self.assertTrue(all(switch.isEnabled() for switch in self.w.radio_test_switches))
        for states in ((True,False),(False,False),(False,True),(True,True)):
            for switch,state in zip(self.w.radio_test_switches,states):switch.setChecked(state)
            QtTest.QTest.qWait(250)
            current=worker.request_generator.call_args.args[0]
            self.assertEqual((current.frequency,current.final_frequency),
                (20000000 if states[0] else 0,40000000 if states[1] else 0))
        self.assertEqual([control.value() for control in self.w.radio_test_carriers],[20000,40000])
        self.w.radio_test_play.setChecked(False);self.w._radio_test_toggle()
        worker.request_generator.reset_mock();self.w.radio_test_switches[0].setChecked(False)
        QtTest.QTest.qWait(250);worker.request_generator.assert_not_called()
        self.w.serial_worker=None

    def test_radio_test_mode_capability_play_stop(self):
        from unittest.mock import Mock
        from monitor.v17.receiver.unoq_generator import GeneratorReply
        from monitor.v17.receiver.unoq_switch import Phase,Reason
        self.w.generator_mode.setCurrentIndex(6)
        self.assertEqual(self.w.generator_mode.currentText(),'Radio Test')
        self.assertFalse(self.w.radio_test_play.isEnabled())
        worker=Mock();self.w.serial_worker=worker
        config=self.w._radio_test_config(True)
        self.w._generator_confirmed(GeneratorReply(0x80000001,Phase.APPLIED,Reason.OK,True,config,config,True,True,True,True))
        self.assertTrue(self.w.radio_test_play.isChecked())
        self.assertTrue(self.w.radio_test_play.isEnabled())
        from PyQt6 import QtTest
        self.w.radio_test_dials[0].setValue(20525)
        self.w.radio_test_dials[2].setValue(750)
        QtTest.QTest.qWait(250)
        update=worker.request_generator.call_args.args[0]
        self.assertEqual((update.frequency,update.duration,update.enabled),(20525000,750,1))
        self.assertEqual(self.w.radio_test_dials[2].maximum(),4000)
        self.assertEqual(self.w.radio_test_values[2].text(),'750 Hz')
        self.w.radio_test_play.setChecked(False);self.w._radio_test_toggle()
        self.assertEqual(worker.request_generator.call_args.args[0].enabled,0)
        self.w.serial_worker=None

    def test_radio_test_levels_update_while_playing_and_stay_off_after_stop(self):
        from unittest.mock import Mock
        from PyQt6 import QtTest
        self.w.generator_mode.setCurrentIndex(6)
        self.assertFalse(self.w.generator_offset_slider.isHidden())
        self.w.generator_mode.setCurrentIndex(4)
        self.w.generator_mode.setCurrentIndex(6)
        self.assertFalse(self.w.generator_offset_slider.isHidden())
        worker=Mock();self.w.serial_worker=worker
        self.w.radio_test_play.setChecked(True)
        self.w._radio_test_toggle()
        worker.request_generator.reset_mock()
        self.w.wav_amplitude_dial.setValue(100)
        self.w.generator_offset_slider.setValue(150)
        QtTest.QTest.qWait(300)
        config=worker.request_generator.call_args.args[0]
        self.assertEqual((config.low,config.high),(round(1.0*4095/3.3),round(2.0*4095/3.3)))
        self.assertTrue(config.enabled)
        self.assertFalse(self.w._generator_labels[self.w.generator_amplitude].isHidden())
        self.assertFalse(self.w._generator_labels[self.w.generator_offset].isHidden())
        self.w.radio_test_play.setChecked(False);self.w._radio_test_toggle()
        worker.request_generator.reset_mock()
        self.w.wav_amplitude_dial.setValue(200)
        QtTest.QTest.qWait(300)
        worker.request_generator.assert_not_called()
        self.w.serial_worker=None

    def test_radio_gain_offset_settings_and_generation(self):
        self.assertEqual(self.w.radio_gain.value(),2)
        self.assertEqual(self.w.radio_offset.value(),1.65)
        generation=self.w._processing_generation
        self.w.radio_gain.setValue(12)
        self.w.radio_offset.setValue(1.65)
        settings=self.w._processing_settings()
        self.assertEqual((settings.radio_gain,settings.radio_offset),(12,1.65))
        self.assertGreater(settings.generation,generation)
        self.assertFalse(self.w.radio_enabled.isChecked())

    def test_compact_radio_row_and_stable_tab_height(self):
        self.w.show();self.app.processEvents()
        heights=[]
        for index in (0,1,2,0,2):
            self.w.trigger_filter_tabs.setCurrentIndex(index);self.app.processEvents()
            heights.append(self.w.trigger_filter_tabs.height())
        self.assertEqual(len(set(heights)),1)
        buttons=(self.w.radio_enabled,self.w.radio_peak_previous,self.w.radio_peak_next,self.w.radio_scan_button)
        self.assertEqual(len({button.parentWidget() for button in buttons}),1)
        self.assertEqual(len({button.y() for button in buttons}),1)
        self.assertIs(buttons[0].parentWidget().parentWidget(),self.w.radio_control_cards[0])
        self.assertEqual(self.w.radio_peak_previous.text(),'<<')
        self.assertEqual(self.w.radio_peak_next.text(),'>>')
        self.assertEqual(self.w.radio_frequency_text.height(),self.w.radio_output_rate.height())
        self.assertEqual(self.w.radio_enabled.text(),'▶')
        self.assertEqual(self.w.radio_scan_button.text(),'')
        display=self.w.radio_frequency_text
        self.assertTrue(display.rect().contains(self.w.radio_frequency_led.geometry()))
        for label in display.findChildren(QtWidgets.QLabel):self.assertTrue(display.rect().contains(label.geometry()))

    def test_radio_controls_and_peak_markers(self):
        from concurrent.futures import Future
        self.assertEqual(self.w.radio_enabled.size(),self.w.radio_scan_button.size())
        self.assertFalse(self.w.radio_scan_button.icon().isNull())
        self.assertFalse(self.w.radio_frequency_dial.property('orangeColor'))
        peak=dict(frequency=20000,dbfs=-20,above_noise_db=15,persistence=3)
        future=Future();future.set_result([peak])
        self.w._radio_scan_future=future
        self.w._radio_scan_job_generation=self.w._radio_scan_generation
        self.w._radio_scan_finished()
        self.assertEqual(self.w.radio_frequency_dial.peak_frequencies,(20000,))
        self.w.radio_frequency_dial.grab() # Exercise marker painting.
        self.w._radio_scan() # No valid capture: old markers must still disappear.
        self.assertEqual(self.w.radio_frequency_dial.peak_frequencies,())

    def test_radio_test_hz_steps_units_and_ack_entry(self):
        from PyQt6 import QtCore, QtTest
        from monitor.v17.receiver.unoq_generator import GeneratorReply
        from monitor.v17.receiver.unoq_switch import Phase,Reason
        self.w.generator_mode.setCurrentIndex(6)
        dial=self.w.radio_test_dials[2]
        dial.setValue(975)
        self.assertEqual(self.w.radio_test_values[2].text(),'975 Hz')
        QtTest.QTest.keyClick(dial,QtCore.Qt.Key.Key_Right)
        self.assertEqual(self.w.radio_test_tone.value(),1000)
        self.assertEqual(self.w.radio_test_values[2].text(),'1 kHz')
        dial.setValue(1025)
        self.assertEqual(self.w.radio_test_values[2].text(),'1.025 kHz')
        dial.setValue(1026)
        self.assertEqual(dial.value(),1025)
        self.assertEqual(self.w.radio_test_tone.value(),1025)
        dial.setValue(0)
        self.assertEqual(self.w.radio_test_values[2].text(),'0 Hz')
        self.w.radio_test_dials[0].setValue(750)
        config=self.w._radio_test_config(True)
        self.assertEqual(config.frequency,750000)
        self.w._generator_confirmed(GeneratorReply(0x80000001,Phase.APPLIED,Reason.OK,True,config,config,True,True,True))
        self.assertFalse(self.w.radio_test_play.isEnabled()) # Legacy firmware cannot accept Hz controls.
        self.w.generator_mode.setCurrentIndex(0)
        self.w._generator_confirmed(GeneratorReply(0x80000002,Phase.APPLIED,Reason.OK,True,config,config,True,True,True,True))
        self.assertEqual(self.w.radio_test_carriers[0].value(),750)
        self.assertEqual(self.w.radio_test_tone.value(),0)
        self.assertTrue(self.w.radio_test_play.isEnabled())

    def test_dials_geometry_and_two_way_interaction(self):
        self.w._acquisition_confirmed(8,1403508)
        self.w.radio_frequency.setValue(550)
        from PyQt6 import QtCore, QtTest
        self.w.show()
        self.w.trigger_filter_tabs.setCurrentWidget(self.w.radio_panel)
        self.app.processEvents()
        for dial in (self.w.radio_frequency_dial,):
            self.assertEqual((dial.width(),dial.height()),(56,56))
        left=self.w.radio_frequency;right=self.w.radio_output_rate
        self.assertTrue(left.isHidden())
        self.assertFalse(hasattr(self.w,"radio_output_dial"))
        self.w.radio_frequency_dial.setFocus()
        QtTest.QTest.keyClick(self.w.radio_frequency_dial,QtCore.Qt.Key.Key_Right)
        self.assertAlmostEqual(left.value(),550.1)
        left.setValue(123.456)
        self.assertEqual(self.w.radio_frequency_dial.value(),123456)
        self.w.filter_source.setCurrentText('RADIO')
        for index in (1,2,0):
            right.setCurrentIndex(index)
            self.assertEqual(right.currentIndex(),index)
            self.assertEqual(self.w._filter_sample_rate(),right.currentData())
        right.setCurrentIndex(2)
        self.assertEqual(self.w._filter_sample_rate(),48000)
        self.w.radio_frequency_dial.setValue(5000)
        self.assertEqual(left.value(),5)

    def test_live_path_with_synthetic_rf(self):
        self.w.radio_output_rate.setCurrentIndex(self.w.radio_output_rate.findData(20000))
        self.w._acquisition_confirmed(8,1403508)
        self.w.radio_frequency.setValue(550)
        self.w.filter_source.setCurrentText('RADIO')
        self.w.radio_enabled.setChecked(True)
        rate=self.w.applied_configuration.actual_rate
        n=int(rate*.08);t=np.arange(n)/rate
        x=1.65+(1+.5*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*550000*t)
        for start in range(0,n,3456):
            data=x[start:start+3456]
            self.w._process_radio({'CH1':data,'Muestra':np.arange(start,start+len(data)),
                                  'Tiempo (us)':t[start:start+len(data)]*1e6})
        stream=self.w.radio_stream
        self.assertEqual(stream.rate,20000)
        self.assertGreater(stream.counter,1500)
        self.assertEqual(len(stream.series['FILTER']),len(stream.series['RADIO']))
        self.assertTrue(np.isfinite(stream.series['FILTER'][:]).all())
        np.testing.assert_allclose(np.diff(stream.series['Tiempo (us)'][:]),50)
        self.w._render_radio_audio(['RADIO','FILTER'],{'RADIO','FILTER'})
        self.assertIn('20',self.w.lbl_top_fs.text())
        self.w.spectral.mode=1
        self.w.spectral.channels[0].setCurrentText('RADIO')
        self.w.spectral.channels[1].setCurrentText('Ninguno')
        self.w.spectral.size.setCurrentText('1024')
        self.w.spectral.render()
        self.assertEqual(stream.analysis_owner(self.w).current_fs_hz,20000)
        spectrum=self.w.spectral.statistics_by_channel['RADIO']
        self.assertAlmostEqual(spectrum.frequencies[-1],10000)
        peak=spectrum.frequencies[np.argmax(spectrum.amplitude)]
        self.assertLess(abs(peak-1000),25)
        self.w.radio_output_rate.setCurrentIndex(self.w.radio_output_rate.findData(40000))
        self.assertIsNone(self.w.radio_stream)
        self.assertEqual(self.w._filter_sample_rate(),40000)

    def test_play_stop_and_fft_peak_navigation(self):
        from PyQt6 import QtCore, QtTest
        self.w._acquisition_confirmed(8,1403508)
        self.w.radio_frequency.setValue(550)
        rate=self.w.applied_configuration.actual_rate
        n=3*65536;self.w.spectral.size.setCurrentText('4096')
        t=np.arange(n)/rate
        frequencies=[256*rate/4096,512*rate/4096]
        self.w.series['CH1'].extend(np.cos(2*np.pi*frequencies[0]*t)+.8*np.cos(2*np.pi*frequencies[1]*t)+np.random.default_rng(3).normal(0,.01,n))
        self.w.series['Tiempo (us)'].extend(t*1e6)
        self.w.sample_counter=n
        self.w.radio_frequency.setValue(5)
        QtTest.QTest.mouseClick(self.w.radio_enabled,QtCore.Qt.MouseButton.LeftButton)
        self.assertTrue(self.w.radio_enabled.isChecked())
        self.assertEqual('■',self.w.radio_enabled.text())
        QtTest.QTest.mouseClick(self.w.radio_scan_button,QtCore.Qt.MouseButton.LeftButton)
        for _ in range(200):
            if self.w._radio_scan_future is None:break
            QtTest.QTest.qWait(25)
        self.assertIsNone(self.w._radio_scan_future)
        self.assertEqual(len(self.w.radio_candidates),2)
        for button,expected in ((self.w.radio_peak_next,frequencies[0]),
                                (self.w.radio_peak_next,frequencies[1]),
                                (self.w.radio_peak_next,frequencies[0]),
                                (self.w.radio_peak_previous,frequencies[1])):
            QtTest.QTest.mouseClick(button,QtCore.Qt.MouseButton.LeftButton)
            self.assertAlmostEqual(self.w.radio_frequency.value()*1000,expected,delta=1)
            self.assertEqual(len(self.w.series['CH1']),n)
        QtTest.QTest.mouseClick(self.w.radio_enabled,QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(self.w.radio_enabled.isChecked())
        self.assertEqual('▶',self.w.radio_enabled.text())
        self.assertIsNone(self.w.radio_stream)

    def test_unsupported_profile_silences_radio(self):
        self.w._acquisition_confirmed(16,1000)
        self.w.radio_enabled.setChecked(True)
        self.w._process_radio({'CH1':np.ones(32),'Muestra':np.arange(32)})
        self.assertIsNone(self.w.radio_stream)
        self.assertIn('requiere',self.w.radio_status.text())

    def test_scan_requires_data_and_discards_old_generation(self):
        from concurrent.futures import Future
        self.w._radio_scan()
        self.assertIsNone(self.w._radio_scan_future)
        self.assertEqual(self.w.radio_candidates,[])
        future=Future();future.set_result([{'frequency':100000}])
        self.w._radio_scan_future=future
        self.w._radio_scan_job_generation=self.w._radio_scan_generation
        self.w.clear_data()
        self.w._radio_scan_finished()
        self.assertEqual(self.w.radio_candidates,[])
        self.assertFalse(self.w.radio_peak_next.isEnabled())
        self.assertTrue(self.w.radio_scan_button.isEnabled())
        self.assertIn('descartado',self.w.radio_status.text())

    def test_scan_waits_for_fresh_samples_after_generator_change(self):
        config=Configuration(8,1403508);self.w.applied_configuration=config
        n=3*65536
        self.w.series['CH1'].extend(np.ones(n))
        self.w.series['Tiempo (us)'].extend(np.arange(n)*config.dt_us)
        self.w.sample_counter=n;self.w._radio_scan_not_before_sample=n
        self.w._radio_scan()
        self.assertIsNone(self.w._radio_scan_future)
        self.assertIn('bloques nuevos',self.w.radio_status.text())


class ResamplerTests(unittest.TestCase):
    def test_blocks_and_output_rates(self):
        rate=160000000/114/32
        x=np.sin(2*np.pi*1000*np.arange(6000)/rate)
        for output in (20000,40000,48000):
            whole=AudioResampler(rate,output).process(x)
            r=AudioResampler(rate,output)
            parts=np.concatenate([r.process(x[i:i+79]) for i in range(0,len(x),79)])
            np.testing.assert_allclose(parts,whole,atol=1e-12)
            self.assertLessEqual(abs(len(whole)-(len(x)-r.radius)*output/rate),1)
            self.assertLess(len(r.buffer),150)

    def test_20k_rejects_above_nyquist(self):
        rate=43859.649122807
        t=np.arange(10000)/rate
        low=AudioResampler(rate,20000).process(np.sin(2*np.pi*1000*t))[300:]
        high=AudioResampler(rate,20000).process(np.sin(2*np.pi*15000*t))[300:]
        self.assertGreater(np.std(low),100*np.std(high))
