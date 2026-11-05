from concurrent.futures import Future
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from tools.synth_transition_scenario_v20 import SynthTransition,preparation_snapshot,source_snapshot,configure_synth_rate


def status(session,state=2,played=0,reason=0):
    return SimpleNamespace(session=session,state=state,played=played,reason=reason)


class SynthTransitionTests(unittest.TestCase):
    def test_delayed_prepare_does_not_stop_or_close_and_old_ack_does_not_start_hold(self):
        scenario=SynthTransition();scenario.request(72.)
        for now in (82.4,85.,100.):
            self.assertIsNone(scenario.observe(status(9,3,160000),now,(8,9)))
            self.assertIsNone(scenario.action(now))
            self.assertGreater(scenario.end_at(85.,now),now)
        self.assertEqual(scenario.phase,'wait-play')
        self.assertEqual(scenario.observe(status(10,2),101.,(8,9)),'playing')
        self.assertIsNone(scenario.action(105.999))
        self.assertEqual(scenario.action(106.),'stop')
        self.assertIsNone(scenario.action(106.1))
        self.assertIsNone(scenario.observe(status(9,3,160000),106.2,(8,9)))
        self.assertFalse(scenario.complete)
        self.assertEqual(scenario.observe(status(10,0,100000),106.3,(8,9)),'stopped')
        self.assertTrue(scenario.complete);self.assertTrue(scenario.hold_completed)
        self.assertEqual(scenario.snapshot()['played'],100000)
        self.assertEqual(scenario.end_at(85.,106.3),108.3)

    def test_prepare_and_stop_deadlines_are_explicit_and_faults_never_count_as_success(self):
        scenario=SynthTransition();scenario.request(0.)
        self.assertIsNone(scenario.action(120.))
        with self.assertRaisesRegex(TimeoutError,'nuevo PLAY'):scenario.action(120.01)
        scenario=SynthTransition();scenario.request(0.)
        scenario.observe(status(10),1.,(8,9));self.assertEqual(scenario.action(6.),'stop')
        with self.assertRaisesRegex(TimeoutError,'STOP confirmado'):scenario.action(16.01)
        with self.assertRaisesRegex(RuntimeError,'state=4'):scenario.observe(status(10,4,10,2),7.,(8,9))
        self.assertFalse(scenario.complete)
        startup=SynthTransition();startup.request(0.)
        with self.assertRaisesRegex(RuntimeError,'startup state=4'):startup.observe(status(10,4,0,2),1.,(8,9))
        scenario=SynthTransition();scenario.request(0.);scenario.observe(status(10),1.,(8,9))
        with self.assertRaisesRegex(RuntimeError,'before confirmed hold'):scenario.observe(status(10,0),2.,(8,9))

    def test_late_play_and_stop_ack_cannot_beat_the_next_tick_deadline(self):
        scenario=SynthTransition();scenario.request(100.) # Request after the old GUI end at 85 s.
        self.assertTrue(scenario.pending);self.assertGreater(scenario.end_at(85.,100.),100.)
        with self.assertRaisesRegex(TimeoutError,'nuevo PLAY'):scenario.observe(status(10),220.001,(8,9))
        self.assertEqual(scenario.phase,'wait-play');self.assertIsNone(scenario.session)
        scenario=SynthTransition();scenario.request(0.);scenario.observe(status(10),1.,(8,9))
        self.assertEqual(scenario.action(6.),'stop')
        with self.assertRaisesRegex(TimeoutError,'STOP confirmado'):scenario.observe(status(10,0),16.001,(8,9))
        self.assertFalse(scenario.complete);self.assertEqual(scenario.phase,'wait-stop')

    def test_sixty_second_hold_starts_at_new_ack_and_voice_counts_cover_only_playing(self):
        self.assertEqual(SynthTransition().hold_seconds,5.)
        with self.assertRaises(ValueError):SynthTransition(hold_seconds=10)
        scenario=SynthTransition(hold_seconds=60);scenario.request(0.)
        scenario.observe_voices(20)
        scenario.observe(status(10),110.,(8,9));scenario.observe_voices(None)
        scenario.observe_voices(20);scenario.observe_voices(0)
        self.assertIsNone(scenario.action(169.999))
        self.assertGreater(scenario.end_at(25.,169.999),169.999)
        self.assertEqual(scenario.action(170.),'stop');scenario.observe_voices(99)
        self.assertEqual(scenario.snapshot()['voice_observations'],2)
        self.assertEqual((scenario.voice_min,scenario.voice_max),(0,20))
        scenario.observe(status(10,0),170.1,(8,9))
        self.assertTrue(scenario.hold_completed);self.assertTrue(scenario.complete)

    def test_actual_synth_rate_widget_changes_only_with_enabled_firmware_capability(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'QT_QPA_PLATFORM':'offscreen'}):
            from PySide6 import QtWidgets
            app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            synth=QtWidgets.QComboBox();firmware=QtWidgets.QComboBox()
            for combo in (synth,firmware):
                combo.addItem('20 kHz',20000);combo.addItem('40 kHz',40000)
            window=SimpleNamespace(fm_panel=SimpleNamespace(output_rate=synth),wav_rate=firmware)
            self.assertEqual(configure_synth_rate(window,40000),40000)
            self.assertEqual(synth.currentData(),40000);self.assertEqual(firmware.currentData(),20000)
            configure_synth_rate(window,20000);firmware.model().item(1).setEnabled(False)
            with self.assertRaisesRegex(RuntimeError,'no habilitada'):configure_synth_rate(window,40000)
            self.assertEqual(synth.currentData(),20000)
            firmware.model().item(1).setEnabled(True);synth.model().item(1).setEnabled(False)
            with self.assertRaisesRegex(RuntimeError,'no habilitada'):configure_synth_rate(window,40000)
            self.assertEqual(synth.currentData(),20000)

    def test_scalar_preparation_and_observed_voice_snapshot(self):
        task=Future();source=SimpleNamespace(rate=20000,position=4800,
            parameters=SimpleNamespace(notes=tuple((n,100) for n in range(20))),remote_active_voice_count=20,
            max_render_ms=1.5,slow_render_blocks=0)
        worker=SimpleNamespace(_wav_prepare_task=task,_wav_prepare_request=(source,20000),
            _wav_prepare_active=(source,20000),_synth_process=object())
        self.assertEqual(preparation_snapshot(worker),dict(request_pending=True,task_present=True,task_done=False,
            active=True,requested_rate=20000,active_rate=20000,synth_process_created=True))
        observed=source_snapshot(source);self.assertEqual(observed['configured_notes'],20)
        self.assertEqual(observed['remote_active_voice_count'],20)
        self.assertFalse(any(isinstance(v,(tuple,list)) for v in observed.values()))

    def test_product_keeps_priming_serialized_and_cancels_stale_begin_after_stop(self):
        # Exercise the actual unmodified product gates without starting a worker or Q.
        from monitor.v20.app import OutputWorker
        future=Future();source=SimpleNamespace(live=True,prepare_audio=Mock())
        worker=SimpleNamespace(_wav_prepare_request=None,_wav_prepare_task=None,_wav_prepare_active=None,
            _pcm_executor=Mock(),_prepare_live_audio=Mock(),_pcm_prepared=set(),
            _ipc_wav_source=Mock(return_value={'session':4}))
        worker._pcm_executor.submit.return_value=future;backend=Mock()
        OutputWorker._queue_ipc_wav(worker,backend,1,source,20000)
        OutputWorker._advance_wav_preparation(worker,backend)
        OutputWorker._advance_wav_preparation(worker,backend)
        backend.submit.assert_not_called()
        self.assertFalse(preparation_snapshot(worker)['task_done'])
        OutputWorker._queue_ipc_wav(worker,backend,3)
        future.set_result(True);OutputWorker._advance_wav_preparation(worker,backend)
        backend.submit.assert_called_once_with('wav',opcode=3,codes=None,rate=20000)
        worker._ipc_wav_source.assert_not_called();self.assertEqual(worker._pcm_prepared,set())

    def test_product_emits_begin_once_after_successful_preparation(self):
        from monitor.v20.app import OutputWorker
        future=Future();source=SimpleNamespace(live=True,prepare_audio=Mock())
        worker=SimpleNamespace(_wav_prepare_request=None,_wav_prepare_task=None,_wav_prepare_active=None,
            _pcm_executor=Mock(),_prepare_live_audio=Mock(),_pcm_prepared=set(),
            _ipc_wav_source=Mock(return_value={'session':4}))
        worker._pcm_executor.submit.return_value=future;backend=Mock()
        OutputWorker._queue_ipc_wav(worker,backend,1,source,20000)
        OutputWorker._advance_wav_preparation(worker,backend);future.set_result(True)
        OutputWorker._advance_wav_preparation(worker,backend);OutputWorker._advance_wav_preparation(worker,backend)
        backend.submit.assert_called_once_with('wav',opcode=1,codes={'session':4},rate=20000)
        self.assertEqual(worker._pcm_prepared,{4})
