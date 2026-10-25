import time
import unittest
from types import SimpleNamespace
import numpy as np
from monitor.v18.io.receiver_process import RemotePcmSource, ReceiverProcess
from monitor.v18.receiver.unoq_acquisition import Configuration

class FakeConnection:
    def __init__(self, port):pass
    def __enter__(self):return self
    def __exit__(self,*args):pass

class FakeReceiver:
    def __init__(self, connection, samples, progress, running):
        self.samples=samples;self.running=running
        self.decoder=SimpleNamespace(numeric=False)
        self.wav_candidate=False;self.wav_codes=None;self.wav_pending=None
        self.last_generator_poll=time.monotonic();self.config=Configuration()
    def configure(self, config):
        self.config=config;self.on_configuration(config);return True
    def select(self,*args):pass
    def generator(self,config=None):
        self.last_generator_poll=time.monotonic()
        reply=SimpleNamespace(active=config)
        self.on_generator(reply);return reply
    def pump(self):
        time.sleep(.003)
        self.samples(np.array([[1,1,2,1]],dtype=np.uint32))
    def shutdown_output(self):pass
    def close(self):pass
    def set_wav_levels(self,*args):pass

class FloodReceiver(FakeReceiver):
    def __init__(self,connection,samples,progress,running):
        super().__init__(connection,samples,progress,running)
        self.progress=progress
    def pump(self):
        for i in range(100):self.progress(str(i))

class PcmChannelReceiver(FakeReceiver):
    def __init__(self,connection,samples,progress,running):
        super().__init__(connection,samples,progress,running)
        self.progress=progress
    def wav_request(self,opcode,codes=None,rate=20000):
        self.wav_codes=codes
    def pump(self):
        if self.wav_codes is not None:
            result=self.wav_codes.try_codes(0,3)
            if result is not None:
                self.progress('PCM:'+','.join(map(str,result)))
                self.wav_codes=None
        super().pump()

class ReceiverProcessTests(unittest.TestCase):
    def test_spawn_pcm_channel_is_independent_of_rf_event_consumption(self):
        owner=ReceiverProcess('fake',0,Configuration(),connection_factory=FakeConnection,
                              receiver_factory=PcmChannelReceiver).start()
        try:
            owner.submit('wav',opcode=1,codes=dict(kind='live',session=1,length=100,rate=20000),rate=20000)
            # Deliberately do not poll the RF/control queue before this request.
            event=owner.receive_pcm_request(timeout=5)
            self.assertEqual((event['type'],event['start'],event['end']),('pcm_request',0,3))
            owner.submit('pcm',session=1,offset=0,codes=np.array([11,22,33],dtype=np.uint16))
            deadline=time.monotonic()+3;seen=False
            while time.monotonic()<deadline and not seen:
                for event in owner.poll():
                    if event['type']=='batch':owner.release(event['id'])
                    if event.get('name')=='status_changed' and event.get('args')==('PCM:11,22,33',):seen=True
                time.sleep(.005)
            self.assertTrue(seen)
        finally:owner.close()
    def test_remote_codes_nonblocking_session_and_single_gain(self):
        requests=[]
        source=RemotePcmSource(dict(session=4,rate=20000),requests.append)
        self.assertIsNone(source.try_codes(0,3,(2.,1.65)))
        self.assertIsNone(source.try_codes(0,3,(2.,1.65)))
        self.assertEqual(len(requests),1)
        codes=np.array([0,2048,4095],dtype=np.uint16)
        self.assertFalse(source.accept(3,0,codes))
        self.assertTrue(source.accept(4,0,codes))
        np.testing.assert_array_equal(source.try_codes(0,3,(2.,1.65)),codes)
        self.assertIsNone(source.try_codes(3,6))
        self.assertFalse(source.accept(4,3,None))
        self.assertIsNone(source.try_codes(3,6))
        self.assertEqual(len(requests),3)
    def test_pcm_trace_identifies_session_offset_once_per_request(self):
        from unittest.mock import patch
        source=RemotePcmSource(dict(session=7),lambda event:None)
        with patch('monitor.v18.io.receiver_process._flow_trace') as trace:
            source.try_codes(24,27)
            source.try_codes(24,27)
            trace.assert_called_once_with('pcm_child_request','pcm:7:24')

    def test_spawn_fifo_numeric_credit_and_terminal(self):
        owner=ReceiverProcess('fake',0,Configuration(),connection_factory=FakeConnection,
                              receiver_factory=FakeReceiver,startup_gui_ack=True).start()
        events=[];deadline=time.monotonic()+8
        try:
            owner.submit('levels',amplitude=2.,offset=1.65)
            owner.submit('startup',bits=14,rate=31250)
            while time.monotonic()<deadline:
                events.extend(owner.poll())
                batches=[e for e in events if e['type']=='batch']
                if batches:break
                time.sleep(.01)
            self.assertTrue(batches)
            batch=batches[0]
            self.assertGreater(len(batch['batch']),0)
            self.assertTrue(any(e.get('name')=='acquisition_confirmed' for e in events[:events.index(batch)]))
            owner.release(batch['id'])
            owner.submit('shutdown')
            while time.monotonic()<deadline:
                terminal=owner.poll_terminal()
                if terminal:break
                owner.poll();time.sleep(.01)
            self.assertTrue(terminal['ok'],terminal)
            self.assertTrue(terminal['shutdown_confirmed'])
        finally:owner.close()

    def test_terminal_independent_of_full_event_fifo(self):
        owner=ReceiverProcess('fake',0,Configuration(),connection_factory=FakeConnection,
                              receiver_factory=FloodReceiver).start()
        try:
            deadline=time.monotonic()+8
            terminal=None
            while time.monotonic()<deadline:
                terminal=owner.poll_terminal()
                if terminal is not None:break
                time.sleep(.01)
            self.assertIsNotNone(terminal)
            self.assertFalse(terminal['ok'])
            self.assertIn('FIFO',terminal['error'])
            owner.process.join(2)
            self.assertFalse(owner.process.is_alive())
        finally:owner.close()

    def test_pcm_ramp_tracks_rendered_levels_during_edit(self):
        source=RemotePcmSource(dict(session=1),lambda event:None)
        ramp=(np.linspace(1.,2.,3),np.linspace(1.,1.65,3))
        source.try_codes(0,3,ramp)
        source.accept(1,0,np.zeros(3,dtype=np.uint16))
        source.try_codes(0,3,(3.,1.65))
        self.assertEqual(source.last_dac_levels,(2.,1.65))

class CleanupMarkerReceiver(FakeReceiver):
    def __init__(self,connection,samples,progress,running):
        super().__init__(connection,samples,progress,running)
        self.marker=connection.marker
    def shutdown_output(self):
        # Exercise a pump during cleanup, as mature shutdown_output does.
        self.pump()
        from pathlib import Path
        Path(self.marker).write_text('shutdown-confirmed\n')
    def close(self):
        with open(self.marker,'a') as stream:stream.write('closed\n')

class MarkerConnection(FakeConnection):
    def __init__(self,port):self.marker=port

class ReceiverParentDeathTests(unittest.TestCase):
    def test_parent_death_runs_cleanup_without_terminate(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        script='''
import os,sys,time
from monitor.v18.io.receiver_process import ReceiverProcess
from monitor.v18.receiver.unoq_acquisition import Configuration
from tests.v18.io.test_receiver_process import MarkerConnection,CleanupMarkerReceiver
owner=ReceiverProcess(sys.argv[1],0,Configuration(),connection_factory=MarkerConnection,receiver_factory=CleanupMarkerReceiver).start()
deadline=time.monotonic()+10
while time.monotonic()<deadline:
    for event in owner.poll():
        if event['type']=='batch':
            os._exit(0)
    time.sleep(.005)
os._exit(7)
'''
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'cleanup.txt'
            # Redirect inherited output so an orphan cannot hold communicate pipes.
            with open(Path(directory)/'launcher.log','w') as log:
                process=subprocess.Popen([sys.executable,'-c',script,str(marker)],stdout=log,stderr=log)
                self.assertEqual(process.wait(15),0)
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    if marker.exists() and 'closed' in marker.read_text():break
                    time.sleep(.02)
                self.assertTrue(marker.exists())
                self.assertEqual(marker.read_text(),'shutdown-confirmed\nclosed\n')

class CancelDuringReadReceiver(CleanupMarkerReceiver):
    def pump(self):
        if getattr(self,'completed',False):return
        time.sleep(.025)
        self.samples(np.array([[1,1,2,1]],dtype=np.uint32))
        deadline=time.monotonic()+5
        while self.running() and time.monotonic()<deadline:time.sleep(.002)
        # Same TCP read, another decoder event after cancellation arrived.
        self.samples(np.array([[2,1,2,2]],dtype=np.uint32))
        self.completed=True
        with open(self.marker,'w') as stream:stream.write('both-events-processed\n')
    def shutdown_output(self):
        from pathlib import Path
        self.pump()
        if not Path(self.marker).exists():raise AssertionError('Decoder read was interrupted')
    def close(self):pass

class ReceiverCancellationBoundaryTests(unittest.TestCase):
    def test_cancel_does_not_interrupt_events_in_same_read(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'read.txt'
            owner=ReceiverProcess(str(marker),0,Configuration(),connection_factory=MarkerConnection,
                                  receiver_factory=CancelDuringReadReceiver).start()
            try:
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    if any(event['type']=='batch' for event in owner.poll()):break
                    time.sleep(.005)
                owner.submit('shutdown')
                terminal=None
                while time.monotonic()<deadline:
                    terminal=owner.poll_terminal()
                    if terminal:break
                    time.sleep(.005)
                self.assertIsNotNone(terminal)
                self.assertTrue(terminal['ok'],terminal)
                self.assertEqual(marker.read_text(),'both-events-processed\n')
            finally:owner.close()

class OverflowDuringReadReceiver(CleanupMarkerReceiver):
    def pump(self):
        if getattr(self,'completed',False):return
        self.samples(np.zeros((40000,4),dtype=np.uint32))
        self.completed=True
        with open(self.marker,'w') as stream:stream.write('read-complete\n')
    def shutdown_output(self):
        from pathlib import Path
        if not Path(self.marker).exists():raise AssertionError('Overflow interrupted decoder events')
    def close(self):pass

class ReceiverOverloadBoundaryTests(unittest.TestCase):
    def test_overload_is_reported_after_read_and_cleanup_still_runs(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'read.txt'
            started_monotonic=time.monotonic()
            started_wall=time.time()
            owner=ReceiverProcess(str(marker),0,Configuration(),connection_factory=MarkerConnection,
                                  receiver_factory=OverflowDuringReadReceiver).start()
            try:
                terminal=None;deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    terminal=owner.poll_terminal()
                    if terminal:break
                    owner.poll();time.sleep(.005)
                self.assertIsNotNone(terminal)
                self.assertFalse(terminal['ok'])
                self.assertIn('pendiente supera un segundo',terminal['error'])
                snapshot=terminal['failure_snapshot']
                self.assertEqual(snapshot['buffered_samples'],40000)
                self.assertEqual(snapshot['buffered_chunks'],1)
                self.assertEqual(snapshot['retained_batches'],[])
                self.assertEqual(snapshot['actual_rate'],Configuration().actual_rate)
                self.assertEqual(snapshot['bits'],Configuration().bits)
                self.assertGreater(snapshot['pending_duration_s'],1.)
                self.assertGreaterEqual(snapshot['monotonic_s'],started_monotonic)
                self.assertLessEqual(snapshot['monotonic_s'],time.monotonic())
                self.assertGreaterEqual(snapshot['wall_time_s'],started_wall)
                self.assertLessEqual(snapshot['wall_time_s'],time.time())
                self.assertIsNone(snapshot['last_credit_monotonic_s'])
                self.assertIsNone(snapshot['last_credit_age_s'])
                self.assertTrue(terminal['shutdown_confirmed'],terminal)
                self.assertEqual(marker.read_text(),'read-complete\n')
            finally:owner.close()

class WavProgressBurstReceiver(FakeReceiver):
    def pump(self):
        from monitor.v18.receiver.unoq_wav import Status,State
        if not getattr(self,'burst_done',False):
            for accepted in range(1000):
                self.on_wav(Status(0x80000001,123,State.PLAYING,0,20,accepted,accepted,1000,20000,7,30))
            self.on_wav(Status(0x80000002,123,State.DONE,0,30,1000,1000,1000,20000,7,30))
            self.burst_done=True
        super().pump()

class ReceiverProgressTests(unittest.TestCase):
    def test_progress_burst_is_bounded_and_done_is_not_delayed(self):
        owner=ReceiverProcess('fake',0,Configuration(),connection_factory=FakeConnection,
                              receiver_factory=WavProgressBurstReceiver).start()
        statuses=[];deadline=time.monotonic()+8
        try:
            while time.monotonic()<deadline:
                for event in owner.poll():
                    if event['type']=='batch':owner.release(event['id'])
                    if event.get('name')=='wav_confirmed':statuses.append(event['args'][0])
                if len(statuses)>=2:break
                time.sleep(.005)
            self.assertEqual([int(s.state) for s in statuses],[2,3])
            self.assertEqual(statuses[-1].played,1000)
            self.assertIsNone(owner.poll_terminal())
        finally:owner.close()


class RemoteRadioBurstTests(unittest.TestCase):
    def source(self,radio=True):
        self.requests=[]
        return RemotePcmSource(dict(session=9,radio_audio=radio),self.requests.append)

    def test_three_credits_partial_prefix_and_exact_retry(self):
        source=self.source()
        source.prepare_burst(0,480,3)
        self.assertIsNone(source.try_codes(0,480))
        self.assertEqual(self.requests[-1]['end'],1440)
        # New credits cannot alter an outstanding request.
        source.prepare_burst(0,480,8)
        source.try_codes(0,480)
        self.assertEqual(len(self.requests),1)
        codes=np.arange(960,dtype=np.uint16)
        self.assertTrue(source.accept(9,0,codes))
        np.testing.assert_array_equal(source.try_codes(0,480),codes[:480])
        self.assertIsNone(source.try_codes(960,1440))
        self.assertEqual(len(self.requests),1)  # Cache must drain first.
        np.testing.assert_array_equal(source.try_codes(480,960),codes[480:])
        source.prepare_burst(960,480,3)
        self.assertIsNone(source.try_codes(960,1440))
        self.assertEqual(self.requests[-1]['start'],960)
        self.assertEqual(self.requests[-1]['end'],2400)

    def test_none_retries_same_offset_and_stale_session_rejected(self):
        source=self.source()
        source.prepare_burst(480,480,3)
        source.try_codes(480,960)
        self.assertFalse(source.accept(8,480,np.zeros(1440,dtype=np.uint16)))
        self.assertFalse(source.accept(9,480,None))
        source.try_codes(480,960)
        self.assertEqual([request['start'] for request in self.requests],[480,480])
        self.assertEqual([request['end'] for request in self.requests],[1920,1920])

    def test_burst_maximum_validation_and_normal_exact_contract(self):
        source=self.source()
        source.prepare_burst(0,480,99)
        source.try_codes(0,480)
        self.assertEqual(self.requests[-1]['end'],8*480)
        for codes in (np.zeros(481,dtype=np.uint16),np.zeros(9*480,dtype=np.uint16),
                      np.zeros((480,1),dtype=np.uint16),np.zeros(480,dtype=np.float64)):
            with self.assertRaises(ValueError):source.accept(9,0,codes)
        source=self.source(False)
        source.prepare_burst(0,480,3)
        source.try_codes(0,480)
        self.assertEqual(self.requests[-1]['end'],480)
        with self.assertRaises(ValueError):source.accept(9,0,np.zeros(960,dtype=np.uint16))

    def test_service_sends_cached_blocks_in_one_turn_with_tokens(self):
        from unittest.mock import Mock
        from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
        connection=SimpleNamespace(socket=Mock(),read=lambda:b'')
        receiver=OutputReceiver(connection,lambda _:None)
        source=self.source()
        source.credit_window=8;source.maximum_blocks=30;source.target_blocks=30
        source.chunk_interval=.012;source.chunk_burst=8
        receiver.wav_candidate=True;receiver.wav_codes=source;receiver.wav_session=9
        receiver.wav_started=True;receiver.wav_chunk_tokens=3.;receiver.wav_chunk_token_at=time.monotonic()
        receiver.wav_status=SimpleNamespace(session=9,free_blocks=3,accepted=0,queue_slots=30)
        receiver.service_wav()
        self.assertEqual(self.requests[-1]['end'],1440)
        source.accept(9,0,np.zeros(1440,dtype=np.uint16))
        receiver.service_wav()
        self.assertEqual(len(receiver.wav_inflight),3)
        self.assertEqual(receiver.wav_next_offset,1440)
        self.assertEqual(connection.socket.sendall.call_count,3)
        self.assertLess(receiver.wav_chunk_tokens,1.)
