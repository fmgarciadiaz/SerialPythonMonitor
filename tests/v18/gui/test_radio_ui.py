"""V18 GUI parity regressions adapted from the corresponding V17 suite."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v18.app import SerialMonitorWindow
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.radio_stream import AudioResampler, RadioStream
from monitor.v18.radio_am import RadioConfig



class RadioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


    def setUp(self):
        with patch('monitor.v18.app.usb_devices',return_value=[]):self.w=SerialMonitorWindow()


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


    def mixed_history(self,config=None):
        from monitor.v18.processing import BatchProcessor
        from monitor.v18.numeric_batch import NumericBatch,SampleClock
        config=config or Configuration(8,1403508)
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


    def test_radio_demodulates_and_draws_at_1600_without_generator_a0(self):
        self.mixed_history(Configuration(8,1600000))
        self.assertTrue(self.w.radio_enabled.isChecked())
        self.assertIsNone(self.w.radio_output_panel.source)
        self.assertFalse(self.w._wav_active)
        self.assertGreater(self.w.radio_stream.counter,1000)
        self.w.render_frame()
        curve=self.w.line_items['RADIO']
        self.assertTrue(curve.isVisible())
        x,y=curve.getData()
        self.assertGreater(len(y),100)
        self.assertTrue(np.isfinite(y).all())
        self.assertGreater(np.ptp(y),.1)


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


    def test_compact_radio_row_and_stable_tab_height(self):
        self.w.show();self.app.processEvents()
        heights=[]
        for index in (0,1,2,3,0,3):
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


    def test_radio_test_hz_steps_units_and_ack_entry(self):
        from PyQt6 import QtCore, QtTest
        from monitor.v18.receiver.unoq_generator import GeneratorReply
        from monitor.v18.receiver.unoq_switch import Phase,Reason
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


