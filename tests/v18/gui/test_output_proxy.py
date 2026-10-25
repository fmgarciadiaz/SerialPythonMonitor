"""Offline regressions for ownership, FIFO DSP barriers and explicit IPC credit."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from queue import Queue
from threading import Event
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from PyQt6 import QtWidgets
from monitor.v18.app import OutputWorker
from monitor.v18.numeric_batch import NumericBatch


class OutputProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def worker(self):
        return OutputWorker('offline', 0, autoload=True)

    def test_activity_releases_before_finished_even_if_cleanup_raises(self):
        worker=self.worker();order=[]
        activity=Mock();activity.close.side_effect=lambda:order.append('released')
        worker.finished.connect(lambda:order.append('finished'))
        with patch('monitor.v18.process_activity.acquisition_activity_mode',return_value='user'), \
             patch('monitor.v18.process_activity.MacActivity',return_value=activity), \
             patch.object(worker,'_run_receiver_process',side_effect=RuntimeError('cleanup')):
            with self.assertRaisesRegex(RuntimeError,'cleanup'):worker.run()
        self.assertEqual(order,['released','finished'])

    def test_ready_audio_is_available_while_loop_check_is_in_progress(self):
        from monitor.v18.radio_output import RadioDacSource
        from monitor.v18.processing import ProcessingSettings
        from monitor.v18.receiver.unoq_acquisition import Configuration
        for detected in (False,True):
            with self.subTest(detected=detected):
                worker=self.worker();source=RadioDacSource(1,buffer_seconds=0)
                settings=ProcessingSettings(radio_enabled=True,acquisition=Configuration(14,40000))
                worker.set_processing_settings(settings);worker.set_radio_output_source(source)
                batch=SimpleNamespace(columns={'CH1':np.ones(512)},
                    radio_output_session=worker._radio_output_session,
                    processing=dict(settings=settings,radio_key=('station','AM',40000),
                                    audio=np.ones(960)*(settings.radio_offset+.1)))
                entered=Event();release=Event()
                def check(*args):
                    entered.set()
                    if not release.wait(3):raise TimeoutError('Loop check not released')
                    return detected
                with patch.object(source.loop_guard,'observe',check),ThreadPoolExecutor(1) as pool:
                    task=pool.submit(worker._feed_radio_output,batch)
                    try:
                        self.assertTrue(entered.wait(2))
                        self.assertEqual(len(source.try_codes(0,480)),480)
                    finally:release.set()
                    task.result(timeout=2)
                if detected:
                    self.assertIsNone(source.try_codes(480,960))
                    self.assertIn('realimentación',source.error)
                else:self.assertEqual(len(source.try_codes(480,960)),480)

    def test_acquisition_trace_signal_preserves_gui_install_barrier(self):
        worker = self.worker()
        worker.trace.enabled = True
        installed = []
        worker.trace_configuration_ready.connect(installed.append)
        worker._ipc_event(Mock(), dict(type='signal', name='acquisition_confirmed', args=(10, 40000)))
        self.assertEqual(installed[0][1:], (10, 40000))
        self.assertEqual(worker.trace.snapshot()[0]['events'][-1]['event'],
            'target_configuration_confirmed')

    def test_batch_credit_only_returns_once_after_gui_consumption(self):
        worker = self.worker()
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        worker._receiver_process = backend
        block = NumericBatch(np.array([[1, 2, 3, 4]]), 4095)
        received = []
        worker.batch_ready.connect(received.append)
        worker._ipc_event(backend, dict(type='batch', id=41, batch=block))
        self.assertEqual(received, [block])
        backend.release.assert_not_called()
        worker.batch_consumed(block)
        worker.batch_consumed(block)
        backend.release.assert_called_once_with(41)
        self.assertEqual(worker.pending_batches, 0)

    def test_radio_dsp_releases_ipc_copy_while_gui_budget_keeps_full_batch(self):
        from monitor.v18.processing import ProcessingSettings
        for radio in (False,True):
            with self.subTest(radio=radio):
                worker=self.worker();backend=Mock();worker._receiver_process=backend
                settings=ProcessingSettings(radio_enabled=radio)
                worker.set_processing_settings(settings)
                block=NumericBatch(np.array([[1,2,3,4]]),4095)
                with patch.object(worker,'_dispatch_reserved_batch'):
                    worker._ipc_event(backend,dict(type='batch',id=42,batch=block))
                block.processing=dict(settings=settings)
                task=Future();task.set_result(block)
                worker._processed(task,block)
                self.assertEqual(worker.pending_batches,1)
                self.assertIs(worker.delivery_budget.entries[0][0],block)
                self.assertEqual(len(block),1)
                if radio:backend.release.assert_called_once_with(42)
                else:backend.release.assert_not_called()
                worker.batch_consumed(block);worker.batch_consumed(block)
                backend.release.assert_called_once_with(42)
                self.assertEqual(worker.pending_batches,0)

    def test_wav_buffering_and_playing_keep_full_gui_copy_without_holding_ipc(self):
        for state in range(6):
            with self.subTest(state=state):
                worker=self.worker();backend=Mock();worker._receiver_process=backend
                worker._ipc_event(backend,dict(type='signal',name='wav_confirmed',
                    args=(SimpleNamespace(state=state),)))
                block=NumericBatch(np.array([[1,2,3,4]]),4095)
                worker._ipc_event(backend,dict(type='batch',id=43,batch=block))
                self.assertEqual(worker.pending_batches,1)
                self.assertIs(worker.delivery_budget.entries[0][0],block)
                if state in (1,2):backend.release.assert_called_once_with(43)
                else:backend.release.assert_not_called()
                worker.batch_consumed(block)
                backend.release.assert_called_once_with(43)

    def test_ack_is_queued_after_dsp_and_credit_id_survives(self):
        worker = self.worker()
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        worker._receiver_process = backend
        order = []
        worker._processing_executor = ThreadPoolExecutor(max_workers=1)
        worker._processing_executor.submit(lambda: order.append('rf'))
        # A minimal signal endpoint records synchronously in the executor.
        signal = SimpleNamespace(emit=lambda *args: order.append('ack'))
        worker._emit_after_processing(signal, 1)
        worker._processing_executor.shutdown(wait=True)
        self.assertEqual(order, ['rf', 'ack'])
        self.assertEqual(worker._pending_control_signals, 0)

    def test_live_source_stays_local_and_pcm_levels_applied_once(self):
        worker = self.worker()
        source = Mock(live=True, radio_audio=False, rate=40000)
        source.__len__ = Mock(return_value=10000)
        source.try_codes.return_value = np.array([1, 2], dtype=np.uint16)
        descriptor = worker._ipc_wav_source(source, 40000)
        self.assertEqual(descriptor['kind'], 'live')
        self.assertNotIn(source, descriptor.values())
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        event = dict(session=descriptor['session'], start=0, end=2, levels=(.7, 1.2))
        worker._produce_pcm(backend, event)
        source.try_codes.assert_called_once_with(0, 2, (.7, 1.2))
        source.prepare_audio.assert_called_once()
        self.assertEqual(backend.submit.call_args.args, ('pcm',))
        self.assertEqual(backend.submit.call_args.kwargs['offset'], 0)

    def test_radio_burst_returns_only_available_sequential_prefix(self):
        worker=self.worker()
        backend=Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        source=Mock(live=True,radio_audio=True,rate=40000)
        source.__len__=Mock(return_value=10000)
        source.try_codes.side_effect=[np.array([1,2],dtype=np.uint16),
                                      np.array([3,4],dtype=np.uint16),None]
        descriptor=worker._ipc_wav_source(source,40000)
        worker._produce_pcm(backend,dict(session=descriptor['session'],start=10,end=16,
                                        chunk_points=2,levels=None))
        self.assertEqual([call.args[:2] for call in source.try_codes.call_args_list],
                         [(10,12),(12,14),(14,16)])
        np.testing.assert_array_equal(backend.submit.call_args.kwargs['codes'],[1,2,3,4])
        self.assertEqual(backend.submit.call_args.kwargs['offset'],10)

    def test_wav_is_mmap_descriptor_and_source_status_matches_session(self):
        worker = self.worker()
        descriptor = worker._ipc_wav_source(np.array([12, 34], dtype=np.uint16), 20000)
        try:
            data = np.load(descriptor['path'], mmap_mode='r', allow_pickle=False)
            self.assertIsInstance(data, np.memmap)
            np.testing.assert_array_equal(data, [12, 34])
            del data
            old, current = Mock(), Mock()
            worker._pcm_sources.update({1: old, 2: current})
            worker._pcm_session = 2
            worker._ipc_event(Mock(), dict(type='signal', name='wav_confirmed',
                args=(SimpleNamespace(),), source_session=1))
            old.observe_status.assert_called_once()
            current.observe_status.assert_not_called()
        finally:
            Path(descriptor['path']).unlink(missing_ok=True)

    def test_non_radio_underrun_retains_child_transport_evidence(self):
        worker = self.worker()
        source = SimpleNamespace(observe_status=Mock())
        worker._pcm_sources[7] = source
        timing = {'roundtrip_max_ms': 231.0, 'pending_age_ms': 175.0}
        worker._ipc_event(Mock(), dict(type='signal', name='wav_confirmed',
            args=(SimpleNamespace(state=4),), source_session=7,
            status_observed_at=123.0, pcm_transport=timing))
        self.assertEqual(worker.last_pcm_underrun['pcm_transport'], timing)
        self.assertEqual(worker.last_pcm_underrun['source_session'], 7)
        source.observe_status.assert_called_once()

    def test_live_begin_waits_for_warmup_and_stop_invalidates_it(self):
        worker = self.worker()
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        source = Mock(live=True, radio_audio=False)
        source.__len__ = Mock(return_value=10000)
        first, second = Future(), Future()
        worker._pcm_executor = Mock()
        worker._pcm_executor.submit.side_effect = [first, second]
        worker._queue_ipc_wav(backend, 1, source, 40000)
        worker._advance_wav_preparation(backend)
        backend.submit.assert_not_called()
        self.assertIs(worker._wav_prepare_active[0], source)
        first.set_result(None)
        worker._advance_wav_preparation(backend)
        self.assertEqual(backend.submit.call_args.kwargs['opcode'], 1)
        self.assertIn(backend.submit.call_args.kwargs['codes']['session'], worker._pcm_prepared)
        backend.reset_mock()
        worker._queue_ipc_wav(backend, 1, source, 40000)
        worker._advance_wav_preparation(backend)
        worker._queue_ipc_wav(backend, 3)
        second.set_result(None)
        worker._advance_wav_preparation(backend)
        backend.submit.assert_called_once_with('wav', opcode=3, codes=None, rate=20000)
        self.assertIsNone(worker._wav_prepare_request)

    def test_normal_stop_still_reports_child_restoration_failure(self):
        worker = self.worker()
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        def stop_during_poll():
            worker.stop()
            return []
        backend.poll.side_effect = stop_during_poll
        backend.poll_terminal.side_effect = [None, dict(error='restore failed', shutdown_confirmed=False)]
        shutdown, errors = [], []
        worker.shutdown_confirmed.connect(lambda ok, text: shutdown.append(ok))
        worker.error_occurred.connect(errors.append)
        with patch('monitor.v18.io.receiver_process.ReceiverProcess', return_value=backend):
            worker.run()
        self.assertEqual(shutdown, [False])
        self.assertEqual(errors, ['restore failed'])
        backend.submit.assert_called_with('shutdown')

    def test_run_uses_child_and_never_autoloads(self):
        worker = self.worker()
        backend = Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        backend.poll.return_value = []
        backend.poll_terminal.return_value = dict(ok=True, error=None, shutdown_confirmed=True)
        with patch('monitor.v18.io.receiver_process.ReceiverProcess', return_value=backend), \
             patch('monitor.v18.app.connect_scope') as connect, \
             patch('monitor.v18.app.ensure_scope') as ensure, \
             patch('monitor.v18.app.Connection') as connection:
            worker.run()
        backend.start.assert_called_once()
        backend.close.assert_called_once()
        connect.assert_not_called()
        ensure.assert_not_called()
        connection.assert_not_called()

    def test_close_terminal_preserves_child_failure_snapshot_after_stop(self):
        worker=self.worker()
        backend=Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        snapshot=dict(monotonic_s=123.,buffered_samples=40000)
        terminal=dict(error='RF pendiente supera un segundo',shutdown_confirmed=True,
                      failure_snapshot=snapshot)
        def stop_during_poll():
            worker.stop()
            return []
        backend.poll.side_effect=stop_during_poll
        backend.poll_terminal.side_effect=[None,terminal]
        errors=[];shutdown=[]
        worker.error_occurred.connect(lambda error:errors.append(
            (error,worker.delivery_failure_snapshot['receiver_failure_snapshot'])))
        worker.shutdown_confirmed.connect(lambda ok,text:shutdown.append(ok))
        with patch('monitor.v18.io.receiver_process.ReceiverProcess',return_value=backend), \
             patch.object(worker,'_capture_delivery_failure',wraps=worker._capture_delivery_failure) as capture:
            worker.run()
        self.assertEqual(errors,[(terminal['error'],snapshot)])
        self.assertEqual(shutdown,[True])
        self.assertEqual(worker._receiver_failure_snapshot,snapshot)
        capture.assert_called_once_with(terminal['error'])
        backend.close.assert_called_once()

    def test_terminal_seen_in_loop_does_not_capture_same_failure_twice(self):
        worker=self.worker()
        backend=Mock()
        backend.receive_pcm_request.side_effect=Queue().get
        backend.poll.return_value=[]
        terminal=dict(error='DSP atrasado',shutdown_confirmed=True,
                      failure_snapshot=dict(monotonic_s=123.))
        backend.poll_terminal.return_value=terminal
        with patch('monitor.v18.io.receiver_process.ReceiverProcess',return_value=backend), \
             patch.object(worker,'_capture_delivery_failure',wraps=worker._capture_delivery_failure) as capture:
            worker.run()
        capture.assert_called_once()


if __name__ == '__main__':
    unittest.main()
