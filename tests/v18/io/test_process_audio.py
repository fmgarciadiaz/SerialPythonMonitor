import time
import unittest
from monitor.v18.io.process_audio import ProcessAudio
from monitor.v18.io.prototype import Audio
from tests.v18.io.test_prototype import event,snapshot,hold_parent_gil,assert_orphan_exit


class ProcessAudioTests(unittest.TestCase):
    def owner(self,**kwargs):
        owner=ProcessAudio(**kwargs);self.addCleanup(owner.close);event(owner,'READY');return owner

    def test_real_decoder_loop_and_simulated_audio_continue_during_parent_gil_hold(self):
        owner=self.owner(prebuffer=30*480)
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        for i in range(48):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        before=snapshot(owner,lambda row:row['received']==48 and row['state']=='playing')
        hold_parent_gil(.25)
        after=snapshot(owner,lambda row:row['at']>before['at']+.2)
        self.assertEqual(after['state'],'playing')
        self.assertGreater(after['played'],before['played']+6000)
        self.assertGreater(after['frames'],before['frames'])
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        self.assertTrue(result['model_only']);self.assertIsNone(result['restoration_error'])

    def test_partial_wire_writes_run_in_child_and_stop_is_confirmed_on_close(self):
        owner=self.owner(write_limit=37)
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        for i in range(12):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        snapshot(owner,lambda row:row['state']=='playing')
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        self.assertEqual(result['config'],dict(generator=False))
        self.assertIs(owner.close(),result)

    def test_stop_and_new_epoch_cancel_stale_audio_with_same_session_number(self):
        owner=self.owner();owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        snapshot(owner,lambda row:row['received']==1)
        owner.command('STOP',1,11);event(owner,'STOP')
        snapshot(owner,lambda row:row['state']=='stopped')
        owner.command('BEGIN',2,11,total=96000);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,480,bytes(960)))
        owner.send_audio(Audio(2,11,0,bytes(960)))
        after=snapshot(owner,lambda row:row['epoch']==2 and row['cancelled_audio']>=1 and row['received']==2)
        self.assertEqual(after['accepted'],480)
        self.assertEqual(owner.close()['reason'],'shutdown')

    def test_bad_offset_is_fault_with_model_stop_attempt(self):
        owner=self.owner();owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,480,bytes(960)))
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('gap',result['error'])
        self.assertTrue(result['restored']);self.assertTrue(result['model_only'])

    def test_liveness_eof_stops_model_and_releases_new_worker(self):
        owner=self.owner();owner.liveness.close()
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'parent_disconnected');self.assertTrue(result['restored'])
        self.assertFalse(owner.process.is_alive())

    def test_begin_without_pcm_does_not_play_and_shutdown_still_confirms_stop(self):
        owner=self.owner();owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        before=snapshot(owner,lambda row:row['state']=='buffering')
        time.sleep(.03)
        after=snapshot(owner,lambda row:row['at']>before['at']+.02)
        self.assertEqual(after['played'],0)
        self.assertEqual(owner.close()['reason'],'shutdown')

    def test_simulated_underrun_does_not_claim_successful_restoration(self):
        owner=self.owner();owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
        for i in range(2):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertFalse(result['restored'])
        self.assertIn('Device audio failure',result['error'])
        self.assertIn('uncertain',result['restoration_error'])

    def test_actual_parent_death_stops_wire_model_and_new_worker_exits(self):
        assert_orphan_exit(self,wire=True)
