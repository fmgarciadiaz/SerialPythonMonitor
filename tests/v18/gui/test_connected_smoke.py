"""Actual Qt window + proxy/DSP dataflow with an in-memory receiver, never Q."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import queue
import time
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6 import QtWidgets, QtTest
from monitor.v18.app import SerialMonitorWindow, OutputWorker
from monitor.v18.numeric_batch import NumericBatch, SampleClock
from monitor.v18.receiver.unoq_wav import Status, State
from monitor.v18.receiver.unoq_generator import GeneratorReply, GeneratorConfig
from monitor.v18.receiver.unoq_switch import Phase, Reason


class SyntheticBackend:
    instance = None
    def __init__(self, port, mode, config, **kwargs):
        type(self).instance = self
        self.mode, self.config = mode, config
        self.events = queue.Queue()
        self.sent, self.released = [], []
        self.cancelled = self.started = False
        self.sequence = self.sample = 0
        self.last_batch = time.monotonic()
        self.clock = SampleClock(config.timestamp_hz)
        self.wav_session = 0
        self.generator = kwargs.get('initial_generator') or GeneratorConfig()
    def emit(self, name, *args, **extra):
        self.events.put(dict(type='signal', name=name, args=args, **extra))
    def status(self, state, rate=20000):
        self.emit('wav_confirmed', Status(0x80000001, self.wav_session, state, 0,
            30, 0, 0, 40000 if state else 0, rate, 7, 30))
    def start(self):
        self.emit('acquisition_confirmed', self.config.bits, self.config.rate)
        self.emit('output_confirmed', int(self.mode), '')
        self.emit('switching', False)
        self.emit('instrument_confirmed', dict(board_serial='synthetic', app='scope-v17-main-1',
            firmware_sha256='a'*64, relay_sha256='b'*64))
        self.emit('generator_confirmed', GeneratorReply(0x80000001, Phase.APPLIED,
            Reason.OK, True, self.generator, self.generator, True, True, True, True))
        self.status(State.IDLE)
    def submit(self, op, **payload):
        self.sent.append((op, payload))
        if op == 'startup': self.started = True
        elif op == 'shutdown': self.cancelled = True
        elif op == 'wav':
            if payload['opcode'] == 1:
                self.wav_session += 1
                self.status(State.PLAYING, payload['rate'])
            elif payload['opcode'] == 3: self.status(State.IDLE)
    def poll(self):
        now = time.monotonic()
        if self.started and not self.cancelled and now-self.last_batch >= .02:
            self.last_batch = now
            n = round(self.config.actual_rate*.02)
            indices = np.arange(self.sample, self.sample+n)
            t = indices/self.config.actual_rate
            volts = 1.65+.5*(1+.4*np.sin(2*np.pi*500*t))*np.cos(2*np.pi*5000*t)
            raw = np.zeros((n, 4), dtype=np.uint32)
            raw[:, 0] = indices*self.config.period
            raw[:, 1] = np.rint(volts*self.config.maximum/3.3).astype(np.uint32)
            raw[:, 2] = raw[:, 1]; raw[:, 3] = indices
            block = NumericBatch(raw, self.config.maximum, self.clock, self.config.channels)
            block.acquisition = self.config
            self.sample += n; self.sequence += 1
            self.events.put(dict(type='batch', id=self.sequence, batch=block))
        result = []
        while not self.events.empty(): result.append(self.events.get_nowait())
        return result
    def release(self, identifier): self.released.append(identifier)
    def poll_terminal(self):
        return dict(ok=True, error=None, shutdown_confirmed=True) if self.cancelled else None
    def close(self): self.cancelled = True


class ConnectedSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def wait_for(self, predicate, seconds=5):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.qt.processEvents()
            if predicate(): return
            QtTest.QTest.qWait(10)
        self.fail('Synthetic GUI condition timed out')
    def test_connected_dataflow_radio_fm_wav_and_close(self):
        def threaded_worker(*args, **kwargs):
            kwargs['processing_backend'] = 'thread'
            return OutputWorker(*args, **kwargs)
        with patch('monitor.v18.app.usb_devices', return_value=[]), \
             patch('monitor.v18.app.list_ports.comports', return_value=[]), \
             patch('monitor.v18.io.receiver_process.ReceiverProcess', SyntheticBackend), \
             patch('monitor.v18.app.OutputWorker', side_effect=threaded_worker), \
             patch('monitor.v18.app.Connection') as hardware:
            window = SerialMonitorWindow()
            try:
                window.port_combo.addItem('Synthetic', 'synthetic')
                window.port_combo.setCurrentIndex(window.port_combo.count()-1)
                window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(10))
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(40000))
                window.show(); window.connect_serial()
                self.wait_for(lambda: window.sample_counter>1000 and window._wav_capable)
                backend = SyntheticBackend.instance
                self.assertTrue(backend.released)
                self.assertFalse(window.output_pending)
                self.assertEqual(set(window.spectral.bode.instrument),
                    {'board_serial', 'app', 'firmware_sha256'})
                window.radio_frequency.setValue(5)
                window.radio_output_panel.toggle()
                self.wait_for(lambda: window.radio_stream is not None and window.radio_stream.counter>1000)
                source = window.radio_output_panel.source
                self.assertIsNotNone(source)
                self.assertIs(window.serial_worker.radio_output_source, source)
                self.assertGreater(source._available, 0)
                window.render_frame(); window.repaint(); self.qt.processEvents()
                self.assertGreater(window.batch_processing_count, 2)
                self.assertGreater(len(window.line_items['CH1'].getData()[1]), 0)
                window.radio_output_panel.stop()
                self.wait_for(lambda: not window._wav_active)
                window.generator_mode.setCurrentIndex(5)
                window.fm_panel.toggle()
                self.wait_for(lambda: window._wav_active and window.fm_panel.source is not None)
                self.assertEqual(window.fm_panel.play.text(), 'Stop')
                window.fm_panel.toggle()
                self.wait_for(lambda: not window._wav_active)
                window.generator_mode.setCurrentIndex(4)
                window.serial_worker.request_wav(1, np.array([2000, 2100], dtype=np.uint16), 20000)
                self.wait_for(lambda: window._wav_active)
                self.assertTrue(any(op=='wav' and data.get('codes', {}).get('kind')=='npy'
                    for op, data in backend.sent if data.get('codes') is not None))
                window._stop_wav()
                self.wait_for(lambda: not window._wav_active)
                hardware.assert_not_called()
            finally:
                window.close()
                self.wait_for(lambda: not window.isVisible())
            self.assertIsNone(window.serial_worker)
            self.assertIsNone(window.serial_thread)
            self.assertFalse(window.render_timer.isActive())
            self.assertEqual(window._shutdown_status[0], True)
