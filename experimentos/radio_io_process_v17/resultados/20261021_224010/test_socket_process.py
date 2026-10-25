import time
import unittest
from experimentos.radio_io_process_v17.process_audio import ProcessSocketAudio
from experimentos.radio_io_process_v17.tcp_model_server import TcpModelServer
from experimentos.radio_io_process_v17.prototype import Audio,RfBarrier
from experimentos.radio_io_process_v17.test_prototype import event,snapshot,hold_parent_gil,assert_orphan_exit
from monitor.v17.receiver.unoq_acquisition import Configuration


class SocketProcessTests(unittest.TestCase):
    def owner(self,**kwargs):
        server=TcpModelServer();self.addCleanup(server.close)
        connected=server.connect();self.addCleanup(connected.close)
        owner=ProcessSocketAudio(connected,**kwargs);self.addCleanup(owner.close)
        self.assertEqual(connected.fileno(),-1) # Parent cannot read or keep TCP artificially alive.
        initial=None
        for _ in range(4):
            row=owner.events.get(timeout=3)
            if row['op']=='CONFIG_APPLIED':initial=row
            if row['op']=='READY':break
        self.assertIsNotNone(initial)
        return owner,server,initial

    def test_child_socket_and_remote_emulator_advance_during_parent_gil_hold(self):
        owner,server,_=self.owner(prebuffer=30*480)
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        for i in range(48):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        before=snapshot(owner,lambda row:row['received']==48 and row['state']=='playing')
        hold_parent_gil(.25)
        after=snapshot(owner,lambda row:row['at']>before['at']+.2)
        self.assertEqual(after['state'],'playing')
        self.assertGreater(after['played'],before['played']+6000)
        self.assertGreater(after['rf_blocks'],before['rf_blocks']+50)
        result=owner.close();self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        remote=server.close();self.assertIsNone(remote['error'])
        self.assertEqual((remote['state'],remote['bits'],remote['rate']),(0,14,125000))
        gate=RfBarrier(block_size=None);gate.configure(1,0,0)
        for frame in result['rf_drained_on_close']:self.assertTrue(gate.consume(frame))
        self.assertEqual(gate.consumed,result['stats']['rf_blocks'])

    def test_tcp_config_barrier_and_original_profile_restore_are_observed_by_server(self):
        owner,server,initial=self.owner();gate=RfBarrier(block_size=None)
        gate.configure(1,0,initial['first_index'])
        snapshot(owner,lambda row:row['rf_blocks']>=10)
        owner.command('CONFIG',configuration=Configuration(14,40000));applied=event(owner,'CONFIG_APPLIED')
        gate.configure(applied['generation'],applied['rf_barrier'],applied['first_index'])
        consumed=[]
        while gate.consumed<=applied['rf_barrier']:
            frame=owner.rf.get(timeout=2);self.assertTrue(gate.consume(frame));consumed.append(frame)
        self.assertEqual(consumed[-1].first,0)
        result=owner.close();self.assertTrue(result['restored'])
        remote=server.close();self.assertIsNone(remote['error'])
        self.assertEqual((remote['state'],remote['rate']),(0,125000))
        self.assertEqual(len(consumed)+len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_remote_disconnect_is_fault_and_does_not_claim_restore(self):
        owner,server,_=self.owner();server.commands.send('disconnect')
        self.assertTrue(owner.terminal.poll(3))
        result=owner.close();self.assertEqual(result['reason'],'fault')
        self.assertFalse(result['restored']);self.assertIsNotNone(result['restoration_error'])
        self.assertTrue(result['model_only'])

    def test_remote_missing_ack_times_out_with_output_uncertain(self):
        owner,server,_=self.owner();server.commands.send('drop_acks')
        # Wait for command delivery while RF remains live; no audio command yet.
        time.sleep(.02)
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        self.assertTrue(owner.terminal.poll(3))
        result=owner.close();self.assertEqual(result['reason'],'fault')
        self.assertFalse(result['restored']);self.assertIn('ACK timeout',result['error'])
        remote=server.close();self.assertIsNone(remote['error'])

    def test_actual_parent_death_confirms_stop_over_tcp_and_child_exits(self):
        server=TcpModelServer();self.addCleanup(server.close)
        result=assert_orphan_exit(self,wire=('tcp',server.address))
        self.assertTrue(result['model_only']);self.assertTrue(result['restored'])
        remote=server.close();self.assertIsNone(remote['error'])
        self.assertEqual((remote['state'],remote['rate']),(0,125000))

    def test_peer_eof_before_ready_is_reported_without_claiming_restore(self):
        server=TcpModelServer();self.addCleanup(server.close)
        connected=server.connect();self.addCleanup(connected.close)
        server.commands.send('disconnect');self.assertTrue(server.result.poll(2))
        owner=ProcessSocketAudio(connected);self.addCleanup(owner.close)
        self.assertTrue(owner.terminal.poll(3))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertFalse(result['restored'])
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['config'],dict(generator=None,bits=None,rate=None))
