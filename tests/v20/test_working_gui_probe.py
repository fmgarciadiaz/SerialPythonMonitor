import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from tools import probe_working_v20_gui as probe


class WorkingGuiProbeTests(unittest.TestCase):
    def test_candidate_and_transition_commands_are_explicit(self):
        cmd=probe.command('serial',Path('/tmp/report.json'),60,radio_bits=12,radio_rate=1142857,
                          us=True,scan_during_a0=True,restart_a0=True)
        self.assertEqual(cmd[cmd.index('--bits')+1],'12')
        self.assertEqual(cmd[cmd.index('--frequency-khz')+1],'530')
        for flag in ('--allow-private-adc','--us','--scan-during-a0','--restart-a0'):
            self.assertIn(flag,cmd)
        self.assertNotIn('--allow-internal-2m',cmd)

    def artifacts(self,output,identity,restored=True):
        (output/'gui.json').write_text(json.dumps(dict(errors=[],assertions=dict(radio_hold_completed=True,
            radio_progress=True,shutdown_confirmed=True,worker_released=True),
            stages=[dict(stage='periodic',exposed=False)],paint_events=1,display=dict(platform='cocoa'))))
        (output/'wire_metrics.json').write_text(json.dumps(dict(raw_chunk_ack_latency=dict(enabled=True,matched=2,decoded=2))))
        (output/'reader_stages.json').write_text(json.dumps(dict(trackers=[dict(wav_service=dict(calls=8,sends=dict(chunk=2)))])))
        sessions=output/'private_gui_sessions';sessions.mkdir()
        (sessions/'session_1.json').write_text(json.dumps(dict(state='closed',hardware_restored=restored,errors=[],
            snapshot=dict(identity=identity),recovery=dict(seconds=10.01,continuous=True,dropped=0,fatal=0))))

    def test_smoke_rejects_mixed_analysis_and_radio_time_modes_before_connecting(self):
        import io,contextlib,sys
        from unittest.mock import patch
        from tools.gui_live_smoke_v20 import main
        args=['probe','--serial','not-a-board','--output','/tmp/no-gui.json','--radio-time-view','--analysis-mode','vt']
        with patch.object(sys,'argv',args),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:main()
        self.assertEqual(raised.exception.code,2)

    def test_long_window_flags_are_explicit_and_default_command_unchanged(self):
        basic=probe.command('serial',Path('/tmp/report.json'),20)
        self.assertNotIn('--window-seconds',basic)
        cmd=probe.command('serial',Path('/tmp/report.json'),20,window_seconds=2,detail_percent=100,stall_trace=True)
        self.assertEqual(cmd[cmd.index('--window-seconds')+1],'2')
        self.assertEqual(cmd[cmd.index('--detail-percent')+1],'100')
        self.assertIn('--stall-trace',cmd)
        self.assertIn('--radio-time-view',cmd)
        self.assertNotIn('--analysis-mode',cmd)

    def test_radio_only_command_and_child_diagnostics_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp);cmd=probe.command('board',output/'report.json',60)
            self.assertEqual(cmd[cmd.index('--hold-radio-seconds')+1],'60')
            self.assertEqual(cmd[cmd.index('--duration')+1],'65')
            for flag in ('--wav','--fm','--scan','--us'):self.assertNotIn(flag,cmd)
            child=Mock(pid=123,returncode=0);child.poll.return_value=0
            with patch.object(probe.subprocess,'Popen',return_value=child) as popen:
                self.assertTrue(probe.run_child(cmd,output,60,{},lambda:None))
            env=popen.call_args.kwargs['env']
            self.assertEqual(env['MONITOR_V19_CHILD_STAGE_TIMING'],'1')
            self.assertEqual(env['ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY'],'1')
            self.assertEqual(env['ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS'],'10')
            child.send_signal.assert_not_called();child.kill.assert_not_called()

    def test_optional_audio_flags_preserve_radio_duration_and_voice_count(self):
        binding=Path('/tmp/report.json')
        for wav,fm,voices in ((True,False,1),(False,True,1),(True,True,20)):
            with self.subTest(wav=wav,fm=fm,voices=voices):
                cmd=probe.command('board',binding,60,wav=wav,fm=fm,voices=voices)
                self.assertEqual('--wav' in cmd,wav);self.assertEqual('--fm' in cmd,fm)
                self.assertEqual(cmd[cmd.index('--duration')+1],'65')
                self.assertEqual(cmd[cmd.index('--hold-radio-seconds')+1],'60')
                if fm:self.assertEqual(cmd[cmd.index('--voices')+1],str(voices))
                else:self.assertNotIn('--voices',cmd)

    def test_native_only_mode_removes_host_timers_without_claiming_ack_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp);identity=dict(board_serial='board',app='scope-v20-main-1')
            self.artifacts(output,identity)
            (output/'reader_stages.json').unlink()
            (output/'wire_metrics.json').write_text(json.dumps(dict(all=dict(frames=8,samples=6976),
                raw_chunk_ack_latency=dict(enabled=False,matched=0,decoded=0))))
            report=dict(child_returncode=0,requested_tests=dict(diagnostics_mode='native-only'))
            probe.collect(output,report,identity)
            self.assertTrue(report['functional_ok']);self.assertTrue(report['native_diagnostics_complete'])
            self.assertFalse(report['diagnostics_complete']);self.assertTrue(report['diagnostics_requirement_met'])
            child=Mock(pid=123,returncode=0);child.poll.return_value=0
            with patch.object(probe.subprocess,'Popen',return_value=child) as popen:
                self.assertTrue(probe.run_child(['fake'],output,20,report,lambda:None))
            env=popen.call_args.kwargs['env']
            self.assertEqual(env['MONITOR_V19_CHILD_STAGE_TIMING'],'0')
            self.assertEqual(env['ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY'],'0')
            (output/'reader_stages.json').write_text('{}')
            probe.collect(output,report,identity)
            self.assertFalse(report['diagnostics_requirement_met'])

    def test_synth_hold_rate_flags_and_total_budget_cover_prepare_and_recovery(self):
        default=probe.command('board',Path('/tmp/report.json'),20,fm=True)
        self.assertEqual(default[default.index('--synth-hold')+1],'5')
        self.assertEqual(default[default.index('--synth-rate')+1],'20000')
        cmd=probe.command('board',Path('/tmp/report.json'),20,wav=True,fm=True,voices=20,synth_hold=60,synth_rate=40000)
        self.assertEqual(cmd[cmd.index('--synth-hold')+1],'60')
        self.assertEqual(cmd[cmd.index('--synth-rate')+1],'40000')
        self.assertEqual(probe.execution_budget(20),200)
        self.assertGreaterEqual(probe.execution_budget(20,fm=True,synth_hold=60),20+60+120+10+10+60)

    def test_private_receiver_recovery_override_is_explicit_and_preserves_prior_default(self):
        from tools.gui_private_v20 import private_receiver_options
        import os
        with patch.dict(os.environ,{},clear=True):
            self.assertNotIn('recovery_seconds',private_receiver_options(Path('/tmp/binding.json')))
        with patch.dict(os.environ,{'ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS':'10'}):
            self.assertEqual(private_receiver_options(Path('/tmp/binding.json'))['recovery_seconds'],10)
        with patch.dict(os.environ,{'ARDUSCOPIO_PRIVATE_RECOVERY_SECONDS':'.2'}):
            with self.assertRaises(ValueError):private_receiver_options(Path('/tmp/binding.json'))

    def test_timeout_requests_graceful_close_without_killing_or_taking_over(self):
        with tempfile.TemporaryDirectory() as temp:
            child=Mock(pid=123,returncode=None);child.poll.return_value=None
            child.wait.side_effect=subprocess.TimeoutExpired(['gui'],60)
            report={}
            with patch.object(probe.subprocess,'Popen',return_value=child),patch.object(probe.time,'monotonic',side_effect=(0.,1000.)):
                self.assertFalse(probe.run_child(['gui'],Path(temp),60,report,lambda:None))
            child.send_signal.assert_called_once_with(signal.SIGINT)
            child.kill.assert_not_called();child.terminate.assert_not_called()
            self.assertTrue(report['child_still_running']);self.assertTrue(report['timeout'])

    def test_hidden_gui_is_separate_from_functional_result_and_snapshot_restoration(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp);identity=dict(board_serial='board',app='scope-v20-main-1')
            self.artifacts(output,identity);report=dict(child_returncode=0)
            probe.collect(output,report,identity)
            self.assertTrue(report['functional_ok']);self.assertTrue(report['diagnostics_complete'])
            self.assertTrue(report['v20_snapshot_restore']['ok']);self.assertFalse(report['exposure']['exposure_sufficient'])
            path=next((output/'private_gui_sessions').glob('*.json'))
            data=json.loads(path.read_text());data['hardware_restored']=False;path.write_text(json.dumps(data))
            probe.collect(output,report,identity)
            self.assertFalse(report['v20_snapshot_restore']['ok'])

    def test_collect_keeps_actual_phase_configurations_and_short_audio_voices(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp);identity=dict(board_serial='board',app='scope-v20-main-1')
            self.artifacts(output,identity)
            path=output/'gui.json';gui=json.loads(path.read_text())
            gui['stages'] += [dict(stage='radio_a0_playing_confirmed',elapsed=8,
                applied_configuration=dict(bits=8,rate=1860465,channels=1)),
                dict(stage='wav_playing_confirmed',elapsed=69,
                applied_configuration=dict(bits=8,rate=40000,channels=2)),
                dict(stage='fm_play_requested',elapsed=77,requested_voices=20,
                applied_configuration=dict(bits=8,rate=40000,channels=2))]
            path.write_text(json.dumps(gui));report=dict(child_returncode=0)
            probe.collect(output,report,identity)
            self.assertEqual([p['applied_configuration']['rate'] for p in report['audio_phases']],
                             [1860465,40000,40000])
            self.assertEqual(report['audio_phases'][-1]['requested_voices'],20)
            self.assertTrue(report['v20_snapshot_restore']['ok']);self.assertTrue(report['diagnostics_complete'])

    def test_main_uses_new_binding_and_preserves_working_receipt_and_sealed_activation(self):
        self.check_main_fixture()

    def test_main_records_requested_wav_and_twenty_voice_synth_without_deployment(self):
        self.check_main_fixture(('--wav','--fm','--voices','20','--synth-hold','60','--synth-rate','40000'))

    def test_private_priming_binding_is_explicit_and_other_rates_are_rejected_before_q(self):
        import contextlib,io
        self.check_main_fixture(('--radio-rate','2000000','--prime-real-time'))
        with patch.object(sys,'argv',['probe','--serial','fake','--output','/tmp/no-q','--prime-real-time']),patch.object(probe,'identity') as identity,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):probe.main()
        identity.assert_not_called()

    def check_main_fixture(self,extra=()):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();output=root/'diagnosticos/resultados_v20/working_probe'
            sealed=root/'activation.json';sealed.write_text('{"sealed":true}')
            receipt_path=root/'working_pair.json';expected=dict(board_serial='board',app='scope-v20-main-1')
            receipt=dict(identity=expected,activation_report=str(sealed),source_report=str(root/'proof.json'),source_report_sha256='a'*64)
            receipt_path.write_text(json.dumps(receipt));original=receipt_path.read_bytes();seal=sealed.read_bytes()
            def run(cmd,folder,hold,report,save):
                self.artifacts(folder,expected);report['child_returncode']=0;return True
            with patch.object(probe,'ROOT',root),patch.object(probe,'RECEIPT',receipt_path),patch.object(probe,'identity',return_value=expected) as identity,patch.object(probe,'run_child',side_effect=run):
                # Keep real host sources available when ROOT points at the fixture.
                for name in ('tools/gui_private_v20.py','tools/private_v20_pair.py','tools/private_rate_profiles_v20.py','tools/private_radio_priming_v20.py',
                             'tools/gui_live_smoke_v20.py','tools/synth_transition_scenario_v20.py',
                             'monitor/v20/receiver/unoq_config_receiver.py','monitor/v20/io/receiver_process.py',
                             'monitor/v20/fm_source.py','monitor/v20/fm_panel.py','monitor/v20/synth_process.py',
                             'monitor/v20/app.py','monitor/v20/radio_multiscan.py','monitor/v20/temporal_raster.py','monitor/v20/scope_cursors.py'):
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
                with patch.object(probe,'__file__',str(root/'tools/probe_working_v20_gui.py')):
                    (root/'tools/probe_working_v20_gui.py').write_text('fixture')
                    with patch.object(sys,'argv',['probe','--serial','board','--output',str(output),*extra]):
                        self.assertEqual(probe.main(),0)
            self.assertEqual(identity.call_count,2)
            report=json.loads((output/'report.json').read_text())
            self.assertNotIn('restoration',report);self.assertTrue(report['ok'])
            self.assertEqual(report['requested_tests']['wav'],'--wav' in extra)
            self.assertEqual(report['requested_tests']['fm'],'--fm' in extra)
            self.assertEqual(report['requested_tests']['voices'],20 if '--fm' in extra else None)
            self.assertEqual(report['requested_tests']['synth_confirmed_hold_seconds'],60 if '--fm' in extra else None)
            self.assertEqual(report['requested_tests']['synth_dac_rate'],40000 if '--fm' in extra else None)
            self.assertEqual(report.get('private_priming_realtime',False),'--prime-real-time' in extra)
            self.assertEqual('--wav' in report['gui_command'],'--wav' in extra)
            self.assertEqual('--fm' in report['gui_command'],'--fm' in extra)
            self.assertEqual(receipt_path.read_bytes(),original);self.assertEqual(sealed.read_bytes(),seal)
            self.assertFalse(report['exposure']['exposure_sufficient'])
