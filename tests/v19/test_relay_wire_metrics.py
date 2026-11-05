import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import zlib
from tools.relay_wire_metrics_v19 import WireMetrics,observe_connection,selected_metrics_profile,PROFILE_ENV


def packet(kind=20,node=0,offset=0,peak=3,send=150000,slack=100,epoch=1,state=2,queue=1):
    p=bytearray(992);struct.pack_into('<4sHHII',p,0,b'SCP1',4,kind,node,972)
    if kind==12:
        p[24]=state;struct.pack_into('<I',p,40,40000)
    else:
        struct.pack_into('<IIIIHBBIII',p,48,1860465,node*3488+offset,0,0,4,8,1,86,node,epoch<<1)
        struct.pack_into('<8I',p,84,3488,queue,peak,1,2,slack,send,node+1)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)


class WireMetricsTests(unittest.TestCase):
    def test_fragmented_private_timing_requires_explicit_mode_and_excludes_normal_timings(self):
        from tools.wav_timing_candidate_v19 import MAGIC
        from tests.v19.test_wav_timing import words
        frames=[]
        for page,value in enumerate(words()):
            frame=bytearray(packet(node=page,peak=2))
            struct.pack_into('<II',frame,40,MAGIC|(page<<16)|1,value)
            struct.pack_into('<I',frame,988,zlib.crc32(frame[:988]));frames.append(bytes(frame))
        with self.assertRaisesRegex(ValueError,'exact diagnostic binding'):WireMetrics().feed(frames[0])
        observer=WireMetrics(wav_timing=True);data=b''.join(frames)
        for offset in range(0,len(data),137):observer.feed(data[offset:offset+137])
        report=observer.report()
        self.assertFalse(report['ordinary_timing_valid'])
        self.assertFalse(report['performance_acceptance_eligible'])
        self.assertEqual(len(report['wav_chunk_timing']['records']),1)
        self.assertEqual(report['ack_batch_timing']['groups'],[])
        self.assertEqual(report['pending_bytes'],0)

    def test_peak_chunk_window_retains_only_eight_ids_without_pcm(self):
        from monitor.v19.receiver.unoq_wav import chunk
        import numpy as np
        observer=WireMetrics()
        for n in range(12):observer.sent(chunk(0x80000001+n,7,n*480,np.zeros(480,dtype=np.uint16)))
        observer.feed(packet(peak=3))
        event=next(e for e in observer.report()['phase_events'] if e['kind']=='cumulative_peak')
        self.assertEqual(len(event['recent_chunks']),8)
        self.assertEqual(event['recent_chunks'][0]['request_id'],0x80000005)
        self.assertTrue(all(set(c)=={'sent_at','phase','request_id'} for c in event['recent_chunks']))
        self.assertGreaterEqual(event['host_observed_at'],event['recent_chunks'][-1]['sent_at'])

    def test_tail_observations_are_bounded_deduplicated_and_keep_counter_meanings(self):
        observer=WireMetrics()
        for node in range(12):
            frame=packet(node=node,send=100000+node*10000)
            observer.feed(frame+packet(node=node,offset=872,send=999999))
        tails=observer.report()['slowest_node_observations']
        self.assertEqual(len(tails),8)
        self.assertEqual([t['node'] for t in tails],list(range(11,3,-1)))
        self.assertEqual(tails[0]['previous_node_send_ticks'],210000)
        self.assertEqual(tails[0]['copy_max_ticks'],1)
        self.assertEqual(tails[0]['poll_max_ticks'],2)
        self.assertIn('cumulative',observer.report()['node_timing_note'])
        observer.feed(packet(node=0,epoch=2,send=500000))
        self.assertEqual(observer.report()['slowest_node_observations'][0]['epoch'],'2')

    def test_explicit_target_uses_native_clock_and_preserves_other_profile_filter(self):
        with patch.dict(os.environ,{PROFILE_ENV:'[10,1355932]'}):
            profile=selected_metrics_profile()
            self.assertEqual(profile,(10,1355932,118,5568,1))
            observer=WireMetrics(*profile)
            observer.feed(packet())
            self.assertEqual(observer.report()['all']['samples'],0)
            frame=bytearray(packet())
            struct.pack_into('<I',frame,48,1355932)
            frame[66]=10
            struct.pack_into('<I',frame,68,118)
            struct.pack_into('<I',frame,84,5568)
            struct.pack_into('<I',frame,988,zlib.crc32(frame[:988]))
            observer.feed(frame)
            self.assertEqual(observer.report()['node_budget_ticks'],657024)
            self.assertEqual(observer.report()['all']['samples'],4)
        for invalid in ('[true,1355932]','[10,123456]','[14,40000]'):
            with patch.dict(os.environ,{PROFILE_ENV:invalid}):
                with self.assertRaises(ValueError):selected_metrics_profile()

    def test_stop_latency_uses_correlated_reply_not_any_status(self):
        from monitor.v19.receiver.unoq_wav import command
        observer=WireMetrics();rid=0x80000001
        reply=bytearray(packet(kind=12,state=0))
        struct.pack_into('<I',reply,16,rid)
        struct.pack_into('<I',reply,988,zlib.crc32(reply[:988]))
        with patch('tools.relay_wire_metrics_v19.time.monotonic',side_effect=[1.,1.025]):
            observer.sent(command(rid,op=3));observer.feed(packet(kind=12))
            self.assertEqual(observer.report()['stop_pending_count'],1)
            observer.feed(reply)
        self.assertAlmostEqual(observer.report()['stop_roundtrips'][0]['roundtrip_ms'],25.)
        self.assertEqual(observer.report()['stop_pending_count'],0)

    def test_physical_batch_mix_requires_adjacent_even_odd_sequence(self):
        observer=WireMetrics()
        observer.observe_batch(3,12,0) # First half absent: do not pair.
        observer.observe_batch(4,12,0);observer.observe_batch(5,20,872)
        observer.observe_batch(6,20,872);observer.observe_batch(9,20,0) # gap
        observer.observe_batch(10,20,872,final=True);observer.observe_batch(11,20,0)
        observer.observe_batch(12,12,0);observer.observe_batch(13,12,0)
        self.assertEqual(observer.report()['physical_batch_mix'],{
            'acquisition:wav+rf':1,'acquisition:rf+idle':1,'acquisition:wav+wav':1})
        self.assertEqual(observer.report()['final_rf_followed_by_idle'],{'acquisition':1})
        self.assertEqual(observer.report()['wav_rf_max_consecutive_batches'],{'acquisition':1})

    def test_chunk_intervals_are_separate_by_observed_phase(self):
        import numpy as np
        from monitor.v19.receiver.unoq_wav import chunk
        command=chunk(0x80000001,9,0,np.zeros(480,dtype=np.uint16))
        observer=WireMetrics()
        with patch('tools.relay_wire_metrics_v19.time.monotonic',side_effect=[1,1.0005,1.02,1.1]):
            observer.sent(command);observer.sent(command);observer.sent(command)
            observer.set_phase('playing');observer.sent(command)
        timing=observer.report()['chunk_timing']
        self.assertEqual(timing['acquisition']['gaps']['lt1ms'],1)
        self.assertEqual(timing['acquisition']['gaps']['ge12ms'],1)
        self.assertEqual(sum(timing['playing']['gaps'].values()),0)

    def test_phase_observation_does_not_erase_startup_peak(self):
        from monitor.v19.receiver.unoq_wav import command
        observer=WireMetrics()
        observer.feed(packet(peak=5,queue=5))
        observer.sent(command(0x80000001,op=1))
        observer.feed(packet(node=1,peak=5,queue=3))
        observer.feed(packet(kind=12)+packet(node=2,peak=5,queue=2,send=300000))
        report=observer.report()
        self.assertEqual(report['phases']['playing']['sampled_queue_max'],2)
        self.assertEqual(report['radio_playing']['mcu_queue_peak'],5)
        self.assertFalse(report['radio_playing']['headroom_pass'])
        self.assertEqual(report['phases']['playing']['send_over_budget_nodes'],1)
        self.assertEqual(report['phases']['playing']['send_ticks_max'],300000)
        peaks=[e for e in report['phase_events'] if e['kind']=='cumulative_peak']
        self.assertEqual(len(peaks),1)
        observer.feed(packet(node=3,peak=6,queue=4))
        peaks=[e for e in observer.report()['phase_events'] if e['kind']=='cumulative_peak']
        self.assertEqual(peaks[-1]['phase'],'playing')
        self.assertEqual(peaks[-1]['previous_peak'],5)

    def test_phase_event_storage_is_bounded(self):
        observer=WireMetrics()
        for _ in range(200):observer.set_phase('playing');observer.set_phase('stopped')
        self.assertEqual(len(observer.phase_events),128)
        self.assertEqual(observer.events_omitted,272)

    def test_outgoing_query_count_preserves_socket_and_does_not_count_failed_send(self):
        from monitor.v19.receiver.unoq_wav import command
        socket=Mock();socket.sendall.side_effect=[None,OSError('closed')]
        connection=SimpleNamespace(read=Mock(return_value=packet(kind=12)),socket=socket)
        query=command(0x80000001)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'metrics.json'
            with observe_connection(connection,path):
                connection.read()
                connection.socket.sendall(query)
                with self.assertRaises(OSError):connection.socket.sendall(query)
            self.assertIs(connection.socket,socket)
            self.assertEqual(socket.sendall.call_args_list[0].args,(query,))
            report=json.loads(path.read_text())
            self.assertEqual(report['sent_commands'],{'11:0':1})
            self.assertEqual(report['radio_playing_sent_commands'],{'11:0':1})

    def test_fragmentation_radio_gate_and_one_send_observation_per_node(self):
        wire=b''.join((packet(node=0,send=100000),packet(kind=12),packet(node=0,offset=872),
                       packet(node=1),packet(node=1,offset=872),packet(kind=12,state=3),
                       packet(node=2,send=180000),packet(node=0,epoch=2,send=200000)))
        observer=WireMetrics()
        for start in range(0,len(wire),31):
            observer.feed(wire[start:start+31]);self.assertLess(len(observer.buffer),992)
        result=observer.report()
        self.assertEqual(result['epoch_count'],2);self.assertEqual(result['all']['send_nodes'],4)
        self.assertEqual(result['radio_playing']['send_nodes'],1)
        self.assertAlmostEqual(result['radio_playing']['mean_send_margin'],1-150000/(3488*86))
        self.assertTrue(result['radio_playing']['headroom_pass'])
        self.assertEqual(result['frame_kinds'],{'20':6,'12':2})
        self.assertEqual(result['radio_playing_frame_kinds'],{'12':1,'20':3})

    def test_peak_or_slack_limits_fail_and_stack_frames_are_not_send_metrics(self):
        for peak,slack in ((4,100),(3,0)):
            observer=WireMetrics();observer.feed(packet(kind=12)+packet(peak=peak,slack=slack))
            self.assertFalse(observer.report()['radio_playing']['headroom_pass'])
        observer=WireMetrics();observer.feed(packet(kind=21))
        self.assertEqual(observer.report()['all']['send_nodes'],0)
        corrupt=bytearray(packet());corrupt[140]^=1
        with self.assertRaises(ValueError):observer.feed(corrupt)

    def test_connection_observer_preserves_bytes_and_restores_read_method(self):
        wire=packet(kind=12)+packet()
        read=Mock(side_effect=[wire[:17],wire[17:]])
        connection=SimpleNamespace(read=read)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'metrics.json'
            with observe_connection(connection,path) as observed:
                self.assertEqual(observed.read(),wire[:17]);self.assertEqual(observed.read(),wire[17:])
            self.assertIs(connection.read,read)
            report=json.loads(path.read_text());self.assertEqual(report['pending_bytes'],0)
            self.assertEqual(report['radio_playing']['send_nodes'],1)
