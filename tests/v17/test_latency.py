"""Host latency instrumentation and allocation optimizations; no hardware."""
import json
import os
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
from PyQt6 import QtCore, QtWidgets
from monitor.v17.fm_source import FMParameters, FMSource
from monitor.v17.midi_process import MidiProcess
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver


class LatencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_bounded_parse_preserves_partial_record_and_timestamps(self):
        client=MidiProcess()
        record={'message':dict(type='note_on',note=60,velocity=100),'received_ns':1_000_000}
        line=json.dumps(record).encode()+b'\n'
        client.buffer.extend(line*257+line[:11])
        try:
            with patch.object(client.process,'readAllStandardOutput',return_value=QtCore.QByteArray()), \
                    patch('monitor.v17.midi_process.time.monotonic_ns',return_value=3_000_000):
                client.read_output()
                self.assertEqual(len(client.messages),256)
                self.assertEqual(client.buffer,line+line[:11])
                client.read_output()
            self.assertEqual(len(client.messages),257)
            self.assertEqual(client.buffer,line[:11])
            self.assertEqual(client.messages[0].received_ns,1_000_000)
            self.assertEqual(client.messages[0].qt_received_ns,3_000_000)
        finally:client.close()

    def test_midi_timing_waits_for_matching_update_and_nonempty_render(self):
        source=FMSource(rate=20000)
        source.observe_midi_batch([SimpleNamespace(received_ns=1_000_000,qt_received_ns=3_000_000)])
        # A serial render between observe and update still uses old parameters.
        source[0:1]
        self.assertEqual(source.control_updates_rendered,0)
        with patch('monitor.v17.fm_source.time.monotonic_ns',return_value=5_000_000):
            source.update(replace(source.parameters,level=.5))
        source[1:1]
        self.assertEqual(source.control_updates_rendered,0)
        with patch('monitor.v17.fm_source.time.monotonic_ns',return_value=9_000_000):
            source[1:2]
        self.assertEqual(source.control_updates_rendered,1)
        self.assertEqual(source.midi_batches_observed,1)
        self.assertEqual(source.max_midi_to_qt_ms,2.)
        self.assertEqual(source.max_control_to_render_start_ms,4.)
        self.assertEqual(source.max_midi_to_render_start_ms,8.)
        source[2:3]
        self.assertEqual(source.control_updates_rendered,1)

    def test_coalesced_updates_keep_oldest_wait_and_ignore_legacy_timestamps(self):
        source=FMSource(rate=20000)
        for when in (10_000_000,12_000_000):
            source.observe_midi_batch([SimpleNamespace(received_ns=when-2_000_000,qt_received_ns=when)])
            with patch('monitor.v17.fm_source.time.monotonic_ns',return_value=when):
                source.update(source.parameters)
        source.observe_midi_batch([SimpleNamespace(type='note_on'),
                                   SimpleNamespace(received_ns='bad',qt_received_ns=1)])
        with patch('monitor.v17.fm_source.time.monotonic_ns',return_value=15_000_000):source[0:1]
        self.assertEqual(source.midi_batches_observed,2)
        self.assertEqual(source.max_control_to_render_start_ms,5.)
        self.assertEqual(source.max_midi_to_render_start_ms,7.)

    def test_constant_and_ramped_dac_levels_preserve_codes(self):
        for synth in (False,True):
            with self.subTest(synth=synth):
                receiver=OutputReceiver(None,lambda _:None)
                reference=FMSource(rate=20000,parameters=FMParameters(level=.7)) if synth else np.arange(960,dtype='<u2')
                receiver.wav_codes=FMSource(rate=20000,parameters=FMParameters(level=.7)) if synth else reference
                receiver.wav_levels=receiver.wav_previous_levels=(.7,1.65)
                for start,levels in ((0,(.7,1.65)),(480,(1.,1.7))):
                    previous=receiver.wav_previous_levels
                    receiver.wav_levels=levels
                    amplitude=np.linspace(previous[0],levels[0],480)
                    offset=np.linspace(previous[1],levels[1],480)
                    if synth:expected=reference.render_dac_codes(start,start+480,amplitude,offset)
                    else:
                        signal=reference[start:start+480].astype(float)/4095-.5
                        expected=np.rint((signal*amplitude+offset)*4095/3.3).clip(0,4095).astype('<u2')
                    np.testing.assert_array_equal(receiver._wav_chunk_codes(start,start+480),expected)
                    self.assertEqual(receiver.wav_previous_levels,levels)


if __name__=='__main__':unittest.main()
