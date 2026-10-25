"""Initial foreign WAV sessions are observed and rejected, never taken over."""
import multiprocessing as mp
import socket
import struct
import time
import unittest
from unittest.mock import patch
from monitor.v18.io.local_transport import LocalTransport
from monitor.v18.io.process_audio import ProcessAudio,ProcessSocketAudio
from monitor.v18.io.prototype import Prototype
from monitor.v18.io.tcp_model_server import TcpModelServer
from monitor.v18.receiver.unoq_wav import State
from tests.v18.io.test_prototype import snapshot


def fixture_transport(state,delay=0.,drop=False,**kwargs):
    model=LocalTransport(**kwargs);model.realtime=False;model.state=State(state)
    model.session=77;model.total=96000
    model.accepted=96000 if state==State.DONE else 960
    model.played=96000 if state==State.DONE else 480 if state==State.PLAYING else 0
    model.drop=drop
    receive=model.recv;deadline=time.monotonic()+delay
    def recv(limit):
        if time.monotonic()<deadline:raise BlockingIOError()
        return receive(limit)
    model.recv=recv
    return model


def occupied_owner(*args):
    from monitor.v18.io import process_audio
    options=args[-1];state=options.pop('fixture_state');delay=options.pop('fixture_delay')
    drop=options.pop('fixture_drop');evidence=options.pop('fixture_evidence');models=[]
    def transport(**kwargs):
        model=fixture_transport(state,delay,drop,**kwargs);models.append(model);return model
    with patch.object(process_audio,'LocalTransport',transport):process_audio._audio_owner(*args)
    model=models[0]
    evidence.send(dict(requests=[(struct.unpack_from('<H',frame,6)[0],frame[20]) for frame in model.frames],
                       state=int(model.state),session=model.session,accepted=model.accepted,played=model.played))
    evidence.close()


def occupied_server(listener,commands,result,state):
    from monitor.v18.io import tcp_model_server
    with patch.object(tcp_model_server,'LocalTransport',lambda **kwargs:fixture_transport(state,**kwargs)):
        tcp_model_server._serve(listener,commands,result)


class OccupiedStartupTests(unittest.TestCase):
    def local_owner(self,state,delay=0.,drop=False):
        ctx=mp.get_context('spawn');evidence,writer=ctx.Pipe(duplex=False)
        owner=ProcessAudio.__new__(ProcessAudio)
        Prototype.__init__(owner,_target=occupied_owner,
            _options=dict(prebuffer=960,write_limit=992,rf_enabled=False,fixture_state=state,
                          fixture_delay=delay,fixture_drop=drop,fixture_evidence=writer))
        writer.close();self.addCleanup(evidence.close);self.addCleanup(owner.close)
        return owner,evidence

    def assert_rejected(self,owner,state):
        self.assertTrue(owner.terminal.poll(2),'Occupied startup produced no terminal result')
        owner.process.join(2)
        self.assertFalse(owner.process.is_alive(),'Owner did not exit without forced termination')
        self.assertEqual(owner.process.exitcode,0)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('occupied',result['error'])
        self.assertFalse(result['restored']);self.assertFalse(result['generator_verified'])
        self.assertTrue(result['model_only'])
        self.assertEqual(result['wav_readback']['session'],77)
        self.assertEqual(result['wav_readback']['state'],state)
        self.assertNotIn('generator_readback',result)
        return result

    def test_local_occupied_startup_exits_and_preserves_foreign_session(self):
        for state in (State.BUFFERING,State.PLAYING,State.DONE):
            with self.subTest(state=state):
                owner,evidence=self.local_owner(state)
                result=self.assert_rejected(owner,state)
                observed=evidence.recv()
                self.assertEqual(observed['requests'],[(11,0)])
                self.assertEqual((observed['state'],observed['session']),(state,77))
                self.assertEqual((observed['accepted'],observed['played']),
                                 (result['wav_readback']['accepted'],result['wav_readback']['played']))

    def test_shutdown_during_discovery_still_rejects_foreign_reply_without_stop(self):
        owner,evidence=self.local_owner(State.PLAYING,delay=.1)
        snapshot(owner,lambda row:row['state']=='new' and row['pending']==1)
        owner.command('SHUTDOWN')
        self.assert_rejected(owner,State.PLAYING)
        self.assertEqual(evidence.recv()['requests'],[(11,0)])

    def test_shutdown_during_lost_discovery_times_out_and_exits_without_stop(self):
        owner,evidence=self.local_owner(State.BUFFERING,drop=True)
        snapshot(owner,lambda row:row['state']=='new' and row['pending']==1)
        owner.command('SHUTDOWN')
        self.assertTrue(owner.terminal.poll(2));owner.process.join(2)
        self.assertFalse(owner.process.is_alive());self.assertEqual(owner.process.exitcode,0)
        result=owner.close()
        self.assertIn('ACK timeout',result['error']);self.assertFalse(result['restored'])
        self.assertEqual(evidence.recv()['requests'],[(11,0)])

    def test_tcp_occupied_startup_exits_with_only_query_and_remote_state_intact(self):
        for state in (State.PLAYING,):
            with self.subTest(state=state):
                ctx=mp.get_context('spawn');listener=socket.socket()
                self.addCleanup(listener.close)
                listener.bind(('127.0.0.1',0));listener.listen(1)
                server=TcpModelServer.__new__(TcpModelServer);server.address=listener.getsockname()
                reader,server.commands=ctx.Pipe(duplex=False);server.result,writer=ctx.Pipe(duplex=False)
                server.process=ctx.Process(target=occupied_server,args=(listener,reader,writer,state))
                server.closed=None;server.process.start();listener.close();reader.close();writer.close()
                self.addCleanup(server.close)
                owner=ProcessSocketAudio(server.connect());self.addCleanup(owner.close)
                result=self.assert_rejected(owner,state);remote=server.close()
                self.assertIsNone(remote['error']);self.assertEqual(remote['requests'],1)
                self.assertEqual(remote['state'],state)
                self.assertEqual((remote['accepted'],remote['played']),
                                 (result['wav_readback']['accepted'],result['wav_readback']['played']))
