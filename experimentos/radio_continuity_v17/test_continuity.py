"""Offline regression; never imports or operates a physical Q connection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
from concurrent.futures import Future
import numpy as np
from experimentos.radio_continuity_v17.processing import ProcessingSettings,BatchProcessor,same_audio_continuity
from experimentos.radio_continuity_v17.app import OutputWorker,SerialMonitorWindow
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.digital_filter import FilterConfig


def batch(start=0,count=8000):
    return SimpleNamespace(columns={'CH1':np.full(count,1.65),'Muestra':np.arange(start,start+count,dtype=np.uint32),
        'Tiempo (us)':np.arange(start,start+count)*10.})


class ContinuityTests(unittest.TestCase):
    def settings(self):
        return ProcessingSettings(acquisition=Configuration(14,100000),radio_enabled=True,radio_frequency=20000,
            filter=FilterConfig(source='RADIO',mode='highpass'))

    def test_multiple_gain_edits_preserve_resampler_filter_and_sample_clock(self):
        p=BatchProcessor();s=self.settings();r=p.process(batch(),s)
        radio=p.radio;fstate=p.audio_filter.state;count=radio.resampler.output_count
        r=p.process(batch(8000),replace(s,generation=4,radio_gain=5,radio_offset=.3))
        self.assertIs(p.radio,radio)
        self.assertEqual(r.processing['audio_first_time_us'],count*25.)
        self.assertEqual(len(r.processing['audio']),radio.resampler.output_count-count)
        self.assertIsNotNone(r.processing['audio_filter_offset'])
        self.assertEqual(r.processing['audio_filter_offset'],0.)

    def test_structural_round_trip_and_filter_never_share_continuity(self):
        s=self.settings()
        self.assertFalse(same_audio_continuity(s,replace(s,generation=2,continuity_epoch=2)))
        self.assertFalse(same_audio_continuity(s,replace(s,filter=FilterConfig(source='RADIO',mode='lowpass'))))
        self.assertFalse(same_audio_continuity(s,replace(s,acquisition=Configuration(14,40000))))
        p=BatchProcessor();p.process(batch(),s);old=p.radio
        p.process(batch(),replace(s,generation=2,continuity_epoch=2))
        self.assertIsNot(old,p.radio)

    def test_pending_results_keep_original_filtered_audio_and_session_boundary(self):
        s=self.settings();w=OutputWorker('offline',Mode.SPI,processing_settings=s)
        source=Mock();w.set_radio_output_source(source)
        result=dict(settings=s,generation=0,audio_filter=np.array([.2]),audio_filter_offset=0.)
        b=SimpleNamespace(processing=result,columns={},radio_output_session=w._radio_output_session)
        w.set_processing_settings(replace(s,generation=3,radio_gain=8))
        w._feed_radio_output(b)
        source.feed_result.assert_called_once_with(result)
        source.feed_result.reset_mock()
        w.set_processing_settings(replace(s,generation=4,continuity_epoch=2))
        w._feed_radio_output(b);source.feed_result.assert_not_called()
        w.set_processing_settings(s);w.set_radio_output_source(None)
        new=Mock();w.set_radio_output_source(new);w._feed_radio_output(b)
        new.feed_result.assert_not_called()

    def test_publication_stamps_session_and_levels_only_epoch(self):
        s=self.settings();w=OutputWorker('offline',Mode.SPI,processing_settings=s)
        w.set_radio_output_source(Mock());w._processing_executor=Mock()
        w._processing_executor.submit.return_value=Future()
        b=batch();w.publish_batch(b)
        self.assertEqual(b.radio_output_session,w._radio_output_session)
        dummy=SimpleNamespace(_processing_generation=0,_audio_continuity_epoch=0,serial_worker=None)
        SerialMonitorWindow._reset_processing_settings(dummy,levels_only=True)
        SerialMonitorWindow._reset_processing_settings(dummy,levels_only=True)
        self.assertEqual((dummy._processing_generation,dummy._audio_continuity_epoch),(2,0))
        SerialMonitorWindow._reset_processing_settings(dummy)
        self.assertEqual(dummy._audio_continuity_epoch,1)
