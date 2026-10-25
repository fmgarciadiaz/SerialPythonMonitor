from dataclasses import replace
import queue
import struct
import unittest
from unittest.mock import patch
from monitor.v18.io.generator_path import GeneratorPath
from monitor.v18.io.audio_pump import AudioPump
from monitor.v18.io.local_transport import LocalTransport
from monitor.v18.io.process_audio import ProcessAudio,ProcessSocketAudio
from monitor.v18.io.tcp_model_server import TcpModelServer
from tests.v18.io.test_prototype import event,snapshot
from monitor.v18.receiver.unoq_switch import Phase,Reason
from monitor.v18.receiver.unoq_generator import GeneratorReply,GeneratorConfig


def _startup_fixture_owner(*args):
    """Inject faulty generator replies inside the local spawn fixture only."""
    from monitor.v18.io import process_audio
    from monitor.v18.io.local_transport import seal
    channels=list(args);options=channels[-1];requests=[]
    mode=options.pop('generator_fixture')
    class FixtureTransport(LocalTransport):
        def send(self,data):
            before=self.frame_count
            count=super().send(data)
            if self.frame_count!=before:
                frame=self.frames[-1];kind=struct.unpack_from('<H',frame,6)[0]
                requests.append((kind,frame[20] if kind==11 else None))
                if kind==10:
                    if mode=='missing':del self.incoming[-992:]
                    else:
                        reply=bytearray(self.incoming[-992:])
                        # CONFIG starts with wave, enabled, mode, units.
                        reply[25]=reply[45]=1
                        if mode=='running':reply[22]=1
                        self.incoming[-992:]=seal(reply)
            return count
    terminal=channels[-3]
    class EvidenceTerminal:
        def send(self,result):terminal.send(dict(result,fixture_requests=requests))
        def close(self):terminal.close()
    channels[-3]=EvidenceTerminal()
    with patch.object(process_audio,'LocalTransport',FixtureTransport):
        process_audio._audio_owner(*channels)


class GeneratorTests(unittest.TestCase):
    def path(self):
        pump=AudioPump(LocalTransport());pump.control.state='ready'
        path=GeneratorPath(pump);pump.on_event=path.event
        path.query(0);return path

    def reply(self,path):
        config=GeneratorConfig(enabled=0)
        return GeneratorReply(path.pending[0],Phase.APPLIED,Reason.OK,False,config,config)

    def test_accepted_waits_for_applied_and_duplicate_does_not_succeed(self):
        path=self.path();reply=self.reply(path)
        path.event('generator',replace(reply,phase=Phase.ACCEPTED))
        self.assertIsNone(path.observed);self.assertIsNotNone(path.pending)
        path.event('generator',reply);self.assertEqual(path.observed,reply)
        with self.assertRaises(ValueError):path.event('generator',reply)

    def test_unknown_request_cannot_publish_generator(self):
        path=self.path();reply=replace(self.reply(path),request_id=0x8000ffff)
        with self.assertRaises(ValueError):path.event('generator',reply)
        self.assertIsNone(path.observed);self.assertIsNotNone(path.pending)

    def test_query_timeout_does_not_fabricate_observation(self):
        path=self.path()
        with self.assertRaises(TimeoutError):path.tick(.51)
        self.assertIsNone(path.observed)

    def test_query_during_audio_is_not_scheduled(self):
        path=self.path();path.pending=None;path.pump.outgoing=None;path.pump.control.state='playing'
        with self.assertRaises(ValueError):path.query(.1)

    def test_begin_admission_requires_applied_off_reference_and_no_pending_query(self):
        path=self.path();reply=self.reply(path)
        with self.assertRaises(ValueError):path.require_off()
        path.event('generator',replace(reply,phase=Phase.ACCEPTED))
        with self.assertRaises(ValueError):path.require_off()
        path.event('generator',reply);path.require_off()
        for changes in ({'running':True},{'active':replace(reply.active,enabled=1)}):
            path.observed=replace(reply,**changes)
            with self.assertRaises(ValueError):path.require_off()
        path.observed=reply;path.pump.outgoing=None;path.query(.1)
        with self.assertRaises(ValueError):path.require_off()

    def test_ready_requires_automatic_confirmed_off_readback(self):
        for rf_enabled in (False,True):
            with self.subTest(rf_enabled=rf_enabled):
                owner=ProcessAudio(rf_enabled=rf_enabled);self.addCleanup(owner.close)
                startup=[]
                while True:
                    row=owner.events.get(timeout=2);startup.append(row)
                    if row['op']=='READY':break
                readbacks=[row for row in startup if row['op']=='GENERATOR_READBACK']
                self.assertEqual(len(readbacks),1)
                self.assertEqual(readbacks[0]['config'].enabled,0)
                self.assertFalse(readbacks[0]['running'])
                if rf_enabled:self.assertIn('CONFIG_APPLIED',[row['op'] for row in startup])
                result=owner.close()
                self.assertTrue(result['generator_verified']);self.assertTrue(result['restored'])

    def test_unconfirmed_or_active_startup_never_becomes_ready_or_takes_over_output(self):
        from monitor.v18.io.prototype import Prototype
        for mode in ('active','running','missing'):
            with self.subTest(mode=mode):
                owner=ProcessAudio.__new__(ProcessAudio)
                Prototype.__init__(owner,_target=_startup_fixture_owner,
                    _options=dict(prebuffer=960,write_limit=992,rf_enabled=False,generator_fixture=mode))
                self.addCleanup(owner.close)
                self.assertTrue(owner.terminal.poll(2),'Unsafe generator did not fail startup')
                startup=[]
                while True:
                    try:startup.append(owner.events.get_nowait()['op'])
                    except queue.Empty:break
                result=owner.close()
                self.assertNotIn('READY',startup)
                self.assertEqual(result['reason'],'fault')
                self.assertIn('Generator query timeout' if mode=='missing' else 'Known active generator',result['error'])
                self.assertFalse(result['generator_verified']);self.assertFalse(result['restored'])
                self.assertEqual(result['fixture_requests'],[(11,0),(10,None)])

    def test_begin_while_initial_generator_query_is_unconfirmed_never_reaches_wire(self):
        from monitor.v18.io.prototype import Prototype
        owner=ProcessAudio.__new__(ProcessAudio)
        Prototype.__init__(owner,_target=_startup_fixture_owner,
            _options=dict(prebuffer=960,write_limit=992,rf_enabled=False,generator_fixture='missing'))
        self.addCleanup(owner.close)
        snapshot(owner,lambda row:row['state']=='ready' and row['frames']==2)
        owner.command('BEGIN',1,11,total=96000)
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertIn('before confirmed generator startup',result['error'])
        self.assertEqual(result['fixture_requests'],[(11,0),(10,None)])
        self.assertFalse(result['restored'])

    def check_process(self,owner):
        self.addCleanup(owner.close);event(owner,'READY')
        owner.command('GEN_QUERY');readback=event(owner,'GENERATOR_READBACK')
        self.assertEqual(readback['config'].frequency,1234567)
        self.assertEqual(readback['config'].final_frequency,2345678)
        self.assertEqual((readback['config'].low,readback['config'].high,readback['config'].duty),(123,3456,37))
        self.assertFalse(readback['running']);self.assertEqual(readback['config'].enabled,0)
        result=owner.close();self.assertTrue(result['restored'])
        self.assertEqual(result['generator_readback']['duty'],37)
        self.assertFalse(result['generator_running'])

    def test_generator_readback_inside_local_owner_uses_strict_decoder(self):
        self.check_process(ProcessAudio())

    def test_generator_readback_traverses_tcp_and_child_before_snapshot(self):
        server=TcpModelServer();self.addCleanup(server.close)
        self.check_process(ProcessSocketAudio(server.connect()))
        self.assertEqual(server.close()['state'],0)

    def test_set_requires_a_confirmed_off_baseline(self):
        path=self.path();path.pending=None;path.pump.outgoing=None
        with self.assertRaises(ValueError):path.set_off(GeneratorConfig(enabled=0),.1)

    def test_wrong_set_applied_is_not_accepted_as_restored(self):
        path=self.path();path.event('generator',self.reply(path));path.pump.outgoing=None
        wanted=GeneratorConfig(enabled=0,low=111,high=2222,duty=37)
        path.set_off(wanted,.1)
        with self.assertRaises(ValueError):path.event('generator',self.reply(path))
        self.assertIsNotNone(path.pending);self.assertNotEqual(path.observed.active,wanted)

    def test_tcp_mutation_restores_all_parameters_then_independently_reads_them(self):
        from dataclasses import asdict
        server=TcpModelServer();self.addCleanup(server.close)
        owner=ProcessSocketAudio(server.connect());self.addCleanup(owner.close);event(owner,'READY')
        owner.command('GEN_QUERY');original=event(owner,'GENERATOR_READBACK')['config']
        changed=replace(original,frequency=1337000,low=27,high=2011,duration=54321,duty=61)
        owner.command('GEN_SET',generator_config=changed)
        applied=event(owner,'GENERATOR_READBACK')
        self.assertEqual(applied['config'],changed)
        result=owner.close()
        self.assertTrue(result['generator_verified']);self.assertTrue(result['restored'])
        self.assertEqual(result['generator_readback'],asdict(original))
        remote=server.close();self.assertEqual(remote['generator'],asdict(original))
        self.assertIsNone(remote['error'])

    def test_experiment_never_accepts_generator_enable_command(self):
        owner=ProcessAudio();self.addCleanup(owner.close);event(owner,'READY')
        with self.assertRaises(ValueError):owner.command('GEN_SET',generator_config=GeneratorConfig(enabled=1))
        self.assertEqual(owner.sequence,0)
        self.assertTrue(owner.close()['generator_verified'])
