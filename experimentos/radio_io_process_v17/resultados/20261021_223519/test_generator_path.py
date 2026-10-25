from dataclasses import replace
import unittest
from experimentos.radio_io_process_v17.generator_path import GeneratorPath
from experimentos.radio_io_process_v17.audio_pump import AudioPump
from experimentos.radio_io_process_v17.local_transport import LocalTransport
from experimentos.radio_io_process_v17.process_audio import ProcessAudio,ProcessSocketAudio
from experimentos.radio_io_process_v17.tcp_model_server import TcpModelServer
from experimentos.radio_io_process_v17.test_prototype import event
from monitor.v17.receiver.unoq_switch import Phase,Reason
from monitor.v17.receiver.unoq_generator import GeneratorReply,GeneratorConfig


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
