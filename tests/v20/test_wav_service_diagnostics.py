import struct
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import numpy as np
from monitor.v20.receiver import unoq_config_receiver as core
from monitor.v20.io.receiver_process import RemotePcmSource


class ServiceDiagnosticsTests(unittest.TestCase):
    def receiver(self,enabled=True):
        receiver=core.OutputReceiver(SimpleNamespace(socket=Mock()),lambda _:None)
        receiver.child_stage_timing=core._ChildStageTiming() if enabled else None
        receiver.wav_session=9;receiver.next_id=0x80000001
        receiver.wav_codes=RemotePcmSource(dict(session=9,rate=40000,radio_audio=True,
            credit_window=2,target_blocks=2,maximum_blocks=2,length=960),Mock())
        receiver.wav_status=SimpleNamespace(session=9,queue_slots=30,free_blocks=30,accepted=0)
        return receiver

    def reasons(self,receiver):
        return receiver.child_stage_timing.snapshot()['wav_service']['reasons']

    def test_diagnostics_preserve_wire_order_credits_and_play_waits_for_both_acks(self):
        traces=[]
        for enabled in (False,True):
            r=self.receiver(enabled);source=r.wav_codes
            with patch.object(core.time,'monotonic',return_value=10.):
                r.service_wav() # PCM request only: reserve no DAC credit.
                self.assertEqual(r.wav_inflight,{})
                self.assertTrue(source.accept(9,0,np.zeros(960,dtype=np.uint16)))
                r.service_wav()
                ids=list(r.wav_inflight)
                self.assertEqual(len(ids),2);self.assertFalse(r.wav_started)
                r.service_wav();self.assertEqual(r.connection.socket.sendall.call_count,2)
                r.wav_inflight.pop(ids[0]);r.wav_pending=(ids[1],10.)
                r.wav_status.accepted=480;r.wav_status.free_blocks=29
                r.service_wav();self.assertFalse(r.wav_started)
                r.wav_inflight.clear();r.wav_pending=None
                r.wav_status.accepted=960;r.wav_status.free_blocks=28
                r.service_wav();self.assertTrue(r.wav_started)
            frames=[call.args[0] for call in r.connection.socket.sendall.call_args_list]
            traces.append(frames)
            self.assertEqual([struct.unpack_from('<H',frame,6)[0] for frame in frames],[13,13,11])
            self.assertEqual([struct.unpack_from('<I',frame,20)[0] for frame in frames[:2]],[0,480])
            if enabled:
                snapshot=r.child_stage_timing.snapshot()['wav_service']
                self.assertEqual(snapshot['sends']['chunk'],2);self.assertEqual(snapshot['sends']['play'],1)
                self.assertEqual(snapshot['reasons']['pcm_pending'],1)
                self.assertEqual(snapshot['reasons']['pending_chunk_ack'],1)
                self.assertEqual(snapshot['reasons']['priming_ack'],1)
                self.assertEqual(snapshot['priming_calls'],5)
        self.assertEqual(traces[0],traces[1])

    def test_token_limited_burst_matches_disabled_diagnostics_exactly(self):
        results=[]
        for enabled in (False,True):
            r=self.receiver(enabled);source=r.wav_codes
            source.chunk_interval=1.;source.chunk_burst=2
            source.pending=(0,960);source.pending_levels=None;source.pending_chunk_points=480
            r.wav_chunk_tokens=1.;r.wav_chunk_token_at=10.
            with patch.object(core.time,'monotonic',return_value=10.):
                source.accept(9,0,np.zeros(960,dtype=np.uint16));r.service_wav();r.service_wav()
            self.assertEqual(r.wav_next_offset,480);self.assertEqual(r.wav_chunk_tokens,0.)
            with patch.object(core.time,'monotonic',return_value=12.):r.service_wav()
            self.assertEqual(r.wav_next_offset,960);self.assertEqual(r.wav_chunk_tokens,1.)
            results.append(([call.args[0] for call in r.connection.socket.sendall.call_args_list],
                            dict(r.wav_inflight),r.wav_pending,r.wav_next_offset,r.wav_chunk_tokens))
            if enabled:self.assertEqual(self.reasons(r)['token'],2)
        self.assertEqual(results[0],results[1])

    def test_pending_control_credit_and_token_blocks_do_not_consume_audio(self):
        with patch.object(core.time,'monotonic',return_value=10.):
            r=self.receiver();r.wav_started=True
            r.wav_pending=(8,10.);r.wav_inflight={8:(10.,11)}
            r.service_wav();self.assertEqual(self.reasons(r)['pending_control_ack'],1)
            r.wav_inflight={8:(10.,13)};r.wav_status.free_blocks=1
            r.service_wav();self.assertEqual(self.reasons(r)['credits'],1)
            r.wav_inflight.clear();r.wav_pending=None;r.wav_status.free_blocks=30
            r.wav_codes.chunk_interval=1.;r.wav_chunk_tokens=0.;r.wav_chunk_token_at=10.
            r.service_wav();self.assertEqual(self.reasons(r)['token'],1)
            self.assertEqual(r.wav_next_offset,0);self.assertEqual(r.wav_chunk_tokens,0.)
            r.connection.socket.sendall.assert_not_called();r.wav_codes.emit.assert_not_called()

    def test_unavailable_source_status_and_target_are_distinct(self):
        with patch.object(core.time,'monotonic',return_value=10.):
            r=self.receiver();source=r.wav_codes;r.wav_codes=None
            r.service_wav();self.assertEqual(self.reasons(r)['no_source'],1)
            r.wav_codes=source;status=r.wav_status;r.wav_status=None
            r.service_wav();self.assertEqual(self.reasons(r)['no_status'],1)
            r.wav_status=status;r.wav_status.session=10
            r.service_wav();self.assertEqual(self.reasons(r)['session_mismatch'],1)
            r.wav_status.session=9;r.wav_started=True;r.wav_poll_at=20.
            r.wav_status.free_blocks=28
            r.service_wav();self.assertEqual(self.reasons(r)['target_full'],1)
            r.wav_status.free_blocks=30;r.wav_codes=SimpleNamespace(live=True,radio_audio=True,
                target_blocks=2,maximum_blocks=2,credit_window=2)
            # An unavailable direct source has no remote PCM request outstanding.
            r.wav_codes=type('Source',(),dict(live=True,radio_audio=True,target_blocks=2,
                maximum_blocks=2,credit_window=2,__len__=lambda _:960,try_codes=lambda *args:None))()
            r.service_wav();self.assertEqual(self.reasons(r)['no_chunk'],1)
            r.connection.socket.sendall.assert_not_called()

    def test_chunk_gap_uses_host_monotonic_and_excludes_session_boundary(self):
        r=self.receiver();source=r.wav_codes
        source.pending=(0,960);source.pending_levels=None;source.pending_chunk_points=480
        with patch.object(core.time,'monotonic',return_value=10.):
            source.accept(9,0,np.zeros(960,dtype=np.uint16));r.service_wav()
        tracker=r.child_stage_timing.wav_service
        tracker.sent(13,9,10.125);snapshot=tracker.snapshot()
        self.assertEqual(snapshot['chunk_gap_last_ms'],125.);self.assertEqual(snapshot['chunk_gap_max_ms'],125.)
        self.assertEqual(snapshot['chunk_gaps'],2)
        tracker.sent(13,10,30.)
        self.assertEqual(tracker.snapshot()['chunk_gaps'],2)
        self.assertIsNone(tracker.snapshot()['chunk_gap_last_ms'])
        snapshot['reasons']['token']=100
        self.assertEqual(tracker.snapshot()['reasons']['token'],0)
        self.assertEqual(set(tracker.reasons),set(tracker.REASONS))

    def test_default_has_no_counter_object_and_pcm_snapshot_exposes_opt_in_totals(self):
        with patch.object(core,'_child_stage_timing_enabled',False):
            r=core.OutputReceiver(SimpleNamespace(socket=Mock()),lambda _:None)
        self.assertIsNone(r.child_stage_timing)
        r=self.receiver();r.wav_codes=None;r.service_wav()
        source=RemotePcmSource(dict(session=1),Mock())
        snapshot=source.transport_snapshot(child_timing=r.child_stage_timing)
        self.assertEqual(snapshot['child_stages']['wav_service']['reasons']['no_source'],1)
