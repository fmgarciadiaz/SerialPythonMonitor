import ctypes
import multiprocessing as mp
from multiprocessing.connection import wait
from multiprocessing.reduction import DupFd
from multiprocessing import resource_tracker
from _multiprocessing import sem_unlink
import os
import queue
import struct
import time
import unittest
from monitor.v18.io.prototype import Prototype,Credits,Audio,Rf,RfBarrier,RequestJournal


def event(owner,op):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        value=owner.events.get(timeout=max(.001,deadline-time.monotonic()))
        if value['op']==op:return value
    raise AssertionError('Missing event '+op)


def snapshot(owner,predicate):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        try:value=owner.progress.get(timeout=max(.001,deadline-time.monotonic()))
        except queue.Empty:
            raise AssertionError('No progress: '+str(owner.close()['error']))
        if predicate(value):return value
    raise AssertionError('Missing progress condition')


def hold_parent_gil(seconds):
    """PyDLL C call retains the parent GIL; child has a different interpreter."""
    library=ctypes.PyDLL(None)
    call=library.usleep;call.argtypes=[ctypes.c_uint];call.restype=ctypes.c_int
    started=time.monotonic()
    call(round(seconds*1e6))
    if time.monotonic()-started<seconds*.95:raise AssertionError('GIL hold interrupted too early')


def orphan_parent(channel,wire=False):
    """Disposable real parent. Grandparent observes owner exit independently."""
    if wire:
        from monitor.v18.io.process_audio import ProcessAudio
        if isinstance(wire,tuple):
            import socket
            from monitor.v18.io.process_audio import ProcessSocketAudio
            owner=ProcessSocketAudio(socket.create_connection(wire[1],timeout=1))
        else:owner=ProcessAudio(rf_enabled=wire=='rf')
        event(owner,'READY')
        owner.command('BEGIN',1,11,total=96000);event(owner,'BEGIN')
    else:
        owner=Prototype();event(owner,'READY')
        owner.command('CONFIG');event(owner,'CONFIG')
        owner.command('BEGIN',1,11);event(owner,'BEGIN')
    for i in range(30):owner.send_audio(Audio(1,11,i*480,bytes(960)))
    snapshot(owner,lambda row:row['accepted']>=14400)
    if not wire:owner.command('PLAY',1,11);event(owner,'PLAY')
    # A forcibly killed creator cannot unlink its queue semaphores. Give the
    # supervisor only these test-owned names for cleanup after owner exit.
    names=[lock._semlock.name
           for channel_queue in (owner.control,owner.audio,owner.rf,owner.events,owner.progress)
           for lock in (channel_queue._rlock,channel_queue._wlock,channel_queue._sem)]
    channel.send((owner.terminal,DupFd(owner.process.sentinel),names))
    channel.recv() # Supervisor detaches handles before killing this process.
    while True:time.sleep(1)


def assert_orphan_exit(testcase,wire=False):
    ctx=mp.get_context('spawn');supervisor,child=ctx.Pipe()
    parent=ctx.Process(target=orphan_parent,args=(child,wire));parent.start();child.close()
    terminal=None;sentinel=None;names=[]
    try:
        testcase.assertTrue(supervisor.poll(5),'Disposable parent did not become ready')
        terminal,wrapped,names=supervisor.recv();sentinel=wrapped.detach()
        supervisor.send('handles detached')
        parent.terminate();parent.join(2)
        testcase.assertFalse(parent.is_alive())
        testcase.assertTrue(terminal.poll(2),'Owner did not report model restoration')
        result=terminal.recv()
        testcase.assertIn(result['reason'],('parent_lost','parent_disconnected'))
        testcase.assertTrue(result['restored'])
        expected=(dict(generator=False,bits=14,rate=125000) if wire=='rf' or isinstance(wire,tuple) else
                  dict(generator=False) if wire else dict(bits=14,rate=40000,generator=False))
        testcase.assertEqual(result['config'],expected)
        testcase.assertEqual(result['output_policy'],'abandon_on_parent_loss')
        testcase.assertTrue(wait([sentinel],2),'Orphan owner blocked flushing RF')
        return result
    finally:
        if parent.is_alive():parent.terminate();parent.join(2)
        if terminal is not None:terminal.close()
        if sentinel is not None:
            exited=bool(wait([sentinel],3));os.close(sentinel)
            if exited:
                for name in names:
                    try:sem_unlink(name)
                    except FileNotFoundError:pass
                    resource_tracker.unregister(name,'semaphore')
        supervisor.close();parent.close()



class ContractTests(unittest.TestCase):
    def test_confirmed_credits_do_not_return_with_wall_time_or_duplicate_ack(self):
        credits=Credits(2);credits.reserve(1,480);credits.reserve(2,960)
        self.assertEqual(credits.available,0)
        with self.assertRaises(ValueError):credits.reserve(3,1440)
        credits.acknowledge(1,1,480,0)
        self.assertEqual(credits.available,0)
        with self.assertRaises(ValueError):credits.acknowledge(1,2,480,0)
        self.assertEqual(len(credits.pending),1)

    def test_contradictory_ack_preserves_pending(self):
        credits=Credits(30);credits.reserve(1,480)
        with self.assertRaises(ValueError):credits.acknowledge(1,30,0,0)
        self.assertIn(1,credits.pending)

    def test_audio_ipc_payload_bound_and_dac_codes(self):
        for data in (bytearray(2),b'0',bytes(962),struct.pack('<H',4096)):
            with self.assertRaises(ValueError):Audio(1,1,0,data).validate()
        Audio(1,1,0,bytes(960)).validate()

    def test_query_requires_no_pending_commands_and_confirms_consumed_space(self):
        credits=Credits(2);credits.reserve(1,480)
        with self.assertRaises(ValueError):credits.query(2,480,480)
        credits.acknowledge(1,1,480,0)
        self.assertEqual(credits.available,1)
        credits.query(2,480,480)
        self.assertEqual(credits.available,2)


class JournalTests(unittest.TestCase):
    def test_cancelled_reply_does_not_credit_new_epoch_even_with_same_session(self):
        journal=RequestJournal();old=journal.reserve(1,11);journal.cancel()
        new=journal.reserve(2,11)
        self.assertFalse(journal.acknowledge(old,11,2))
        self.assertIn(new,journal.pending)
        self.assertTrue(journal.acknowledge(new,11,2))
        with self.assertRaises(ValueError):journal.acknowledge(new,11,2)

    def test_unknown_and_mismatched_reply_leave_pending_unchanged(self):
        journal=RequestJournal();rid=journal.reserve(1,11)
        for wrong_rid,session,epoch in ((rid,22,1),(rid,11,2),(rid+1,11,1)):
            with self.assertRaises(ValueError):journal.acknowledge(wrong_rid,session,epoch)
        self.assertEqual(journal.pending,{rid:(1,11)})

    def test_bounded_retirement_and_rid_exhaustion_never_reuse_identity(self):
        journal=RequestJournal(limit=2)
        for epoch in range(1,5):journal.reserve(epoch,11);journal.cancel()
        self.assertEqual(len(journal.retired),2)
        with self.assertRaises(ValueError):journal.acknowledge(1,11,4)
        self.assertFalse(journal.acknowledge(4,11,4))
        journal.next_rid=0xffffffff
        with self.assertRaises(ValueError):journal.reserve(5,11)
        self.assertEqual(journal.pending,{})

    def test_pending_limit_never_evicts_unresolved_requests(self):
        journal=RequestJournal(limit=1);rid=journal.reserve(1,11)
        with self.assertRaises(ValueError):journal.reserve(1,11)
        self.assertEqual(journal.pending,{rid:(1,11)})


class BarrierTests(unittest.TestCase):
    def frame(self,n,generation=1,first=None):
        return Rf((n*864)&0xffffffff if first is None else first,864,bytes(864),generation,n)

    def test_config_event_overtakes_old_rf_without_changing_visible_generation(self):
        gate=RfBarrier();gate.configure(1,0)
        gate.configure(2,2)
        self.assertEqual(gate.generation,1)
        self.assertTrue(gate.consume(self.frame(0)))
        self.assertEqual(gate.generation,1)
        self.assertTrue(gate.consume(self.frame(1)))
        self.assertEqual(gate.generation,2)
        self.assertTrue(gate.consume(self.frame(2,2)))

    def test_rf_overtakes_config_is_retained_without_consumption(self):
        gate=RfBarrier();frame=self.frame(0)
        self.assertFalse(gate.consume(frame));self.assertEqual(gate.consumed,0)
        gate.configure(1,0)
        self.assertTrue(gate.consume(frame))

    def test_wrap_and_gaps_and_stale_generation(self):
        gate=RfBarrier();gate.configure(1,0)
        start=2**32-432
        self.assertTrue(gate.consume(self.frame(0,first=start)))
        self.assertTrue(gate.consume(self.frame(1,first=432)))
        with self.assertRaises(ValueError):gate.consume(self.frame(1,first=432))
        with self.assertRaises(ValueError):gate.configure(2,1)
        gate.configure(2,2)
        with self.assertRaises(ValueError):gate.consume(self.frame(2,first=1296))
        self.assertEqual(gate.consumed,2)



class OwnerTests(unittest.TestCase):
    def owner(self,**kwargs):
        owner=Prototype(**kwargs)
        self.addCleanup(owner.close)
        event(owner,'READY')
        owner.command('CONFIG');event(owner,'CONFIG')
        return owner

    def test_backend_disconnect_with_pending_chunk_restores_and_does_not_invent_ack(self):
        owner=self.owner(simulate_disconnect=True)
        owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault')
        self.assertIn('simulated_backend_disconnected',result['error'])
        self.assertTrue(result['restored']);self.assertIsNone(result['restoration_error'])
        self.assertEqual(result['stats']['chunks'],1);self.assertEqual(result['stats']['acks'],0)
        self.assertEqual(len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_restore_failure_is_reported_instead_of_successful_shutdown(self):
        owner=self.owner(simulate_restore_failure=True)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertFalse(result['restored'])
        self.assertIsNone(result['error'])
        self.assertIn('simulated_restore_failure',result['restoration_error'])
        self.assertNotEqual(result['config'],dict(bits=14,rate=40000,generator=False))
        self.assertIs(owner.close(),result)

    def test_disconnect_and_restore_failure_preserve_both_errors(self):
        owner=self.owner(simulate_disconnect=True,simulate_restore_failure=True)
        owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertFalse(result['restored'])
        self.assertIn('simulated_backend_disconnected',result['error'])
        self.assertIn('simulated_restore_failure',result['restoration_error'])

    def test_liveness_eof_stops_owner_and_drains_admitted_rf(self):
        owner=self.owner()
        owner.liveness.close()
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'parent_disconnected')
        self.assertTrue(result['restored'])
        self.assertEqual(result['output_policy'],'drain')
        self.assertEqual(len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_unexpected_liveness_data_is_explicit_fault(self):
        owner=self.owner();owner.liveness.send_bytes(b'unexpected')
        self.assertTrue(owner.terminal.poll(2))
        result=owner.close()
        self.assertEqual(result['reason'],'fault')
        self.assertIn('liveness',result['error']);self.assertTrue(result['restored'])

    def test_actual_parent_death_restores_model_and_owner_exits_without_rf_consumer(self):
        assert_orphan_exit(self)

    def test_child_advances_during_parent_gil_hold_and_rf_closes_without_gaps(self):
        owner=self.owner();before=snapshot(owner,lambda row:True)
        hold_parent_gil(.35)
        after=snapshot(owner,lambda row:row['at']>before['at']+.3)
        self.assertGreater(after['pumps'],before['pumps']+100)
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])
        frames=result['rf_drained_on_close']
        self.assertEqual(len(frames),result['stats']['rf_blocks'])
        self.assertEqual([frame.first for frame in frames],list(range(0,len(frames)*864,864)))
        self.assertIs(owner.close(),result)

    def test_reconfiguration_barrier_matches_actual_rf_fifo(self):
        owner=self.owner();gate=RfBarrier();gate.configure(1,0)
        snapshot(owner,lambda row:row['rf_blocks']>=10)
        owner.command('CONFIG');ack=event(owner,'CONFIG')
        self.assertGreater(ack['rf_barrier'],0)
        gate.configure(ack['generation'],ack['rf_barrier'])
        self.assertEqual(gate.generation,1)
        while gate.consumed<=ack['rf_barrier']:
            frame=owner.rf.get(timeout=1)
            self.assertTrue(gate.consume(frame))
        self.assertEqual(gate.generation,2)
        self.assertEqual(frame.generation,2)
        self.assertEqual(owner.close()['reason'],'shutdown')

    def test_audio_model_keeps_consuming_while_parent_is_blocked(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        for i in range(48):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        snapshot(owner,lambda row:row['accepted']>=960)
        owner.command('PLAY',1,11);event(owner,'PLAY')
        before=snapshot(owner,lambda row:row['playing'])
        hold_parent_gil(.25)
        after=snapshot(owner,lambda row:row['at']>before['at']+.2)
        self.assertGreater(after['played'],before['played']+6000)
        owner.command('STOP',1,11);event(owner,'STOP')
        result=owner.close();self.assertTrue(result['restored']);self.assertEqual(result['reason'],'shutdown')

    def test_rf_consumer_stall_is_explicit_overload_with_model_restore(self):
        owner=self.owner(rf_capacity=2)
        time.sleep(.03)
        result=owner.close()
        self.assertEqual(result['reason'],'fault')
        self.assertIn('rf_backpressure',result['error'])
        self.assertTrue(result['restored'])
        self.assertEqual(len(result['rf_drained_on_close']),result['stats']['rf_blocks'])

    def test_session_and_control_order_and_old_audio_are_explicit(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.command('STOP',1,11);event(owner,'STOP')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        snapshot(owner,lambda row:row['cancelled_audio']>=1)
        owner.command('BEGIN',2,22);reply=event(owner,'BEGIN')
        self.assertEqual((reply['sequence'],reply['epoch'],reply['session']),(4,2,22))
        result=owner.close();self.assertTrue(result['restored'])

    def test_bad_offset_faults_instead_of_silent_gap_or_repetition(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,480,bytes(960)))
        time.sleep(.02)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('offset',result['error'])
        self.assertTrue(result['restored'])

    def test_configuration_is_rejected_during_active_session_and_restores_exact_original(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.command('CONFIG')
        time.sleep(.02)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('CONFIG',result['error'])
        self.assertEqual(result['config'],dict(bits=14,rate=40000,generator=False))

    def test_stop_preempts_audio_waiting_for_confirmed_credit(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        for i in range(48):owner.send_audio(Audio(1,11,i*480,bytes(960)))
        snapshot(owner,lambda row:row['accepted']==14400 and row['pending']==0)
        owner.command('STOP',1,11);event(owner,'STOP')
        result=owner.close()
        self.assertEqual(result['reason'],'shutdown');self.assertTrue(result['restored'])

    def test_delayed_ack_of_old_epoch_cannot_credit_new_session(self):
        owner=self.owner(ack_delay=.08);owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        snapshot(owner,lambda row:row['chunks']>=1)
        owner.command('STOP',1,11);event(owner,'STOP')
        owner.command('BEGIN',2,22);event(owner,'BEGIN')
        owner.send_audio(Audio(2,22,0,bytes(960)))
        snapshot(owner,lambda row:row['cancelled_acks']>=1 and row['acks']>=1)
        result=owner.close();self.assertEqual(result['reason'],'shutdown')

    def test_missing_ack_times_out_without_creating_credits(self):
        owner=self.owner(drop_acks=True);owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        deadline=time.monotonic()+1.5
        while not owner.terminal.poll() and time.monotonic()<deadline:
            for _ in range(64):
                try:owner.rf.get_nowait()
                except queue.Empty:break
            time.sleep(.001)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('ACK_timeout',result['error'])
        self.assertEqual(result['stats']['acks'],0);self.assertEqual(result['stats']['chunks'],1)
        self.assertTrue(result['restored'])

    def test_play_without_required_confirmed_prebuffer_fails_closed(self):
        owner=self.owner();owner.command('BEGIN',1,11);event(owner,'BEGIN')
        owner.send_audio(Audio(1,11,0,bytes(960)))
        snapshot(owner,lambda row:row['accepted']>=480)
        owner.command('PLAY',1,11)
        time.sleep(.02)
        result=owner.close()
        self.assertEqual(result['reason'],'fault');self.assertIn('PLAY',result['error'])
        self.assertTrue(result['restored'])


if __name__=='__main__':unittest.main()
