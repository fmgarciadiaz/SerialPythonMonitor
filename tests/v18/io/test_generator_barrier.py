import struct
import unittest
from unittest.mock import patch
from monitor.v18.io.local_transport import LocalTransport
from monitor.v18.io.process_audio import ProcessAudio
from monitor.v18.io.prototype import Prototype,Rf,RfBarrier
from monitor.v18.receiver.unoq_generator import GeneratorConfig


def _ack_between_frames_owner(*args):
    from monitor.v18.io import process_audio
    class Transport(LocalTransport):
        def __init__(self,**kwargs):
            super().__init__(**kwargs);self.bootstrapped=False;self.injected=False
        def advance(self,now):
            if not self.bootstrapped:
                LocalTransport.advance(self,self.next_rf)
                self.rf_enabled=False;self.bootstrapped=True
        def send(self,data):
            before=self.frame_count;count=super().send(data)
            if self.frame_count!=before and struct.unpack_from('<H',self.frames[-1],6)[0]==10 and not self.injected:
                # ACK + following RF are read together by the owner's ingress.
                self.injected=True;self.rf_enabled=True
                LocalTransport.advance(self,self.next_rf);self.rf_enabled=False
            return count
    with patch.object(process_audio,'LocalTransport',Transport):process_audio._audio_owner(*args)


class GeneratorBarrierTests(unittest.TestCase):
    def gate(self):
        from monitor.v18.io.generator_path import GeneratorReadbackGate
        return GeneratorReadbackGate()

    def readback(self,rid=0x80000001,barrier=1,generation=1):
        return dict(op='GENERATOR_READBACK',request_id=rid,config=GeneratorConfig(enabled=0),running=False,
                    rf_barrier=barrier,rf_generation=generation,epoch=0,session=0)

    def rf(self):
        gate=RfBarrier(block_size=4);gate.configure(1,0,0);return gate

    def test_owner_captures_barrier_at_ack_before_rf_in_same_read(self):
        owner=ProcessAudio.__new__(ProcessAudio)
        Prototype.__init__(owner,_target=_ack_between_frames_owner,
                           _options=dict(prebuffer=960,write_limit=992,rf_enabled=True))
        self.addCleanup(owner.close);startup=[]
        while True:
            row=owner.events.get(timeout=2);startup.append(row)
            if row['op']=='READY':break
        readback=next(row for row in startup if row['op']=='GENERATOR_READBACK')
        self.assertEqual((readback['rf_barrier'],readback['rf_generation']),(1,1))
        self.assertEqual((readback['epoch'],readback['session']),(0,0))
        frames=[owner.rf.get(timeout=2),owner.rf.get(timeout=2)]
        self.assertEqual([frame.ordinal for frame in frames],[0,1])
        gate=self.gate();rf=RfBarrier(block_size=None);rf.configure(1,0,0)
        self.assertFalse(gate.release(readback,rf.consumed))
        self.assertTrue(rf.consume(frames[0]));self.assertTrue(gate.release(readback,rf.consumed))
        self.assertTrue(rf.consume(frames[1]));self.assertEqual((rf.generation,rf.next_first),(1,452))
        self.assertTrue(owner.close()['restored'])

    def test_ack_first_waits_for_preceding_rf_without_reconfiguring(self):
        gate=self.gate();rf=self.rf();ack=self.readback()
        self.assertFalse(gate.release(ack,rf.consumed))
        self.assertTrue(rf.consume(Rf(0,4,bytes(4),1,0)))
        self.assertTrue(gate.release(ack,rf.consumed))
        self.assertEqual((rf.generation,rf.next_first,rf.pending),(1,4,None))

    def test_rf_first_and_multiple_readbacks_at_same_ordinal(self):
        gate=self.gate();rf=self.rf();rf.consume(Rf(0,4,bytes(4),1,0))
        for rid in (0x80000001,0x80000009):
            self.assertTrue(gate.release(self.readback(rid),rf.consumed))

    def test_config_can_be_processed_while_caller_retains_readback(self):
        gate=self.gate();rf=self.rf();ack=self.readback(barrier=2)
        self.assertFalse(gate.release(ack,rf.consumed))
        # CONFIG is delivered after the generator event but before RF catches up.
        rf.configure(2,2,0)
        for ordinal in range(2):self.assertTrue(rf.consume(Rf(ordinal*4,4,bytes(4),1,ordinal)))
        self.assertEqual(rf.generation,2)
        self.assertTrue(gate.release(ack,rf.consumed)) # Historical RF generation 1 is valid.
        self.assertTrue(rf.consume(Rf(0,4,bytes(4),2,2)))

    def test_duplicate_reordered_or_regressing_events_fail_without_publication(self):
        gate=self.gate();ack=self.readback();self.assertTrue(gate.release(ack,1))
        for bad in (ack,self.readback(0x80000000),self.readback(0x80000002,barrier=0)):
            with self.assertRaises(ValueError):gate.release(bad,1)
        self.assertTrue(gate.release(self.readback(0x80000003,barrier=1),1))
        with self.assertRaises(ValueError):gate.release(self.readback(0x80000004),0)

    def test_malformed_events_fail_and_no_rf_readback_releases_at_zero(self):
        for changes in ({'rf_barrier':True},{'rf_barrier':-1},{'rf_generation':-1},
                        {'rf_generation':0},{'request_id':1},{'running':0},
                        {'epoch':-1},{'session':2**32},{'config':{}},{'op':'CONFIG_APPLIED'}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.gate().release(dict(self.readback(),**changes),1)
        ack=self.readback();del ack['rf_barrier']
        with self.assertRaises(ValueError):self.gate().release(ack,1)
        self.assertTrue(self.gate().release(self.readback(barrier=0,generation=0),0))
