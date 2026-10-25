import queue
import time
import unittest
import numpy as np
from monitor.v18.io.process_audio import ProcessAudio
from monitor.v18.io.prototype import Audio,RfBarrier
from tests.v18.io.test_prototype import event,snapshot,hold_parent_gil,assert_orphan_exit
from monitor.v18.receiver.unoq_acquisition import Configuration


class AcquisitionProcessTests(unittest.TestCase):
    def owner(self,**kwargs):
        owner=ProcessAudio(rf_enabled=True,**kwargs);self.addCleanup(owner.close)
        bootstrap=None
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            row=owner.events.get(timeout=2)
            if row['op']=='CONFIG_APPLIED':bootstrap=row
            if row['op']=='READY':break
        self.assertIsNotNone(bootstrap)
        return owner,bootstrap

    def test_applied_event_can_overtake_old_rf_and_resets_index_only_after_barrier(self):
        owner,initial=self.owner();gate=RfBarrier(block_size=None)
        gate.configure(initial['generation'],initial['rf_barrier'],initial['first_index'])
        snapshot(owner,lambda row:row['rf_blocks']>=10)
        owner.command('CONFIG',configuration=Configuration(14,40000))
        applied=event(owner,'CONFIG_APPLIED')
        self.assertEqual(applied['config'],Configuration(14,40000))
        self.assertGreater(applied['rf_barrier'],0)
        gate.configure(applied['generation'],applied['rf_barrier'],applied['first_index'])
        self.assertEqual(gate.generation,1)
        frames=[]
        while gate.consumed<=applied['rf_barrier']:
            frame=owner.rf.get(timeout=2);frames.append(frame)
            self.assertTrue(gate.consume(frame))
        self.assertEqual(gate.generation,2)
        self.assertEqual(frames[-1].first,0)
        self.assertIsInstance(frames[-1].payload,np.ndarray)
        self.assertEqual(frames[-1].payload.dtype,np.dtype(np.uint32))
        np.testing.assert_array_equal(frames[-1].payload[0],(0,123,456,0))
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        self.assertEqual(result['config'],dict(generator=False,bits=14,rate=125000))
        self.assertEqual(len(frames)+len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_rf_and_audio_share_child_while_parent_holds_gil(self):
        owner,_=self.owner(prebuffer=30*480)
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        for i in range(48):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        before=snapshot(owner,lambda row:row['received']==48 and row['state']=='playing')
        hold_parent_gil(.25)
        after=snapshot(owner,lambda row:row['at']>before['at']+.2)
        self.assertEqual(after['state'],'playing')
        self.assertGreater(after['played'],before['played']+6000)
        self.assertGreater(after['rf_blocks'],before['rf_blocks']+50)
        result=owner.close();self.assertTrue(result['restored'])
        gate=RfBarrier(block_size=None);gate.configure(1,0,0)
        for frame in result['rf_drained_on_close']:self.assertTrue(gate.consume(frame))
        self.assertEqual(gate.consumed,result['stats']['rf_blocks'])

    def test_rf_overflow_is_fault_without_silent_loss_or_false_restore(self):
        owner,_=self.owner(rf_capacity=2)
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('RF backpressure',result['error'])
        self.assertFalse(result['restored'])
        self.assertEqual(len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_config_during_audio_is_rejected_and_model_stop_is_attempted(self):
        owner,_=self.owner()
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        snapshot(owner,lambda row:row['state']=='buffering')
        owner.command('CONFIG',configuration=Configuration(14,40000))
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('confirmed idle',result['error'])
        self.assertTrue(result['restored'])

    def test_model_profile_limit_rejects_unmodelled_rate_before_control_enqueue(self):
        owner,_=self.owner()
        with self.assertRaises(ValueError):owner.command('CONFIG',configuration=Configuration(8,1600000))
        self.assertEqual(owner.sequence,0)
        self.assertEqual(owner.close()['reason'],'shutdown')

    def test_parent_death_with_rf_does_not_block_model_stop_on_dead_consumer(self):
        assert_orphan_exit(self,wire='rf')

    def test_shutdown_waits_for_partial_config_then_restores_original_profile(self):
        owner,_=self.owner(write_limit=37)
        owner.command('CONFIG',configuration=Configuration(14,40000));event(owner,'CONFIG')
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        self.assertEqual(result['config'],dict(generator=False,bits=14,rate=125000))
        self.assertEqual(len(result['rf_drained_on_close']),result['stats']['rf_blocks'])


class AcquisitionPathTests(unittest.TestCase):
    def path(self):
        from monitor.v18.io.acquisition_path import AcquisitionPath
        from monitor.v18.io.audio_pump import AudioPump
        from monitor.v18.io.local_transport import LocalTransport
        pump=AudioPump(LocalTransport());pump.control.state='ready'
        path=AcquisitionPath(pump,queue.Queue(4),queue.Queue(4))
        path.configure(Configuration(14,40000),0)
        return path

    def reply(self,path,phase):
        from monitor.v18.receiver.unoq_acquisition import AcquisitionReply
        from monitor.v18.receiver.unoq_switch import Reason
        return AcquisitionReply(path.pending[0],14,Configuration(14,40000),phase,Reason.OK,25,2)

    def test_accepted_does_not_publish_until_applied(self):
        from monitor.v18.receiver.unoq_switch import Phase
        path=self.path();path.event('configuration',self.reply(path,Phase.ACCEPTED))
        self.assertIsNotNone(path.pending);self.assertEqual(path.generation,0)
        self.assertTrue(path.events.empty())
        path.event('configuration',self.reply(path,Phase.APPLIED))
        self.assertIsNone(path.pending);self.assertEqual(path.generation,1)
        self.assertEqual(path.events.get_nowait()['first_index'],0)

    def test_wrong_request_or_profile_cannot_publish_configuration(self):
        from dataclasses import replace
        from monitor.v18.receiver.unoq_switch import Phase
        for changes in ({'request_id':0x80000099},{'requested_period':8}):
            path=self.path();reply=replace(self.reply(path,Phase.APPLIED),**changes)
            with self.assertRaises(ValueError):path.event('configuration',reply)
            self.assertEqual(path.generation,0);self.assertIsNotNone(path.pending)

    def test_missing_applied_has_deadline_even_after_accepted(self):
        from monitor.v18.receiver.unoq_switch import Phase
        path=self.path();path.event('configuration',self.reply(path,Phase.ACCEPTED))
        with self.assertRaises(TimeoutError):path.tick(.51)
        self.assertEqual(path.generation,0)
