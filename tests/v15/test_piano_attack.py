import unittest
import numpy as np
from monitor.historico.v15.virtual_instruments import PianoStrings,InstrumentBody,warmup,modal_kernel
from monitor.historico.v15.piano_room import PianoRoom

class AttackTests(unittest.TestCase):
    def setUp(self):
        if modal_kernel is None:self.skipTest('Numba requerido')
        warmup()
    def test_restrike_preserves_ringing_state(self):
        s=PianoStrings(20000,261.625,calibrated=True);s.render(6000)
        state=s.state.copy();s.restrike(.6)
        np.testing.assert_array_equal(s.state,state)
        self.assertTrue(s.residual_strike)
        self.assertTrue(np.isfinite(s.render(4000)).all())
    def test_room_chunk_invariance_and_decay(self):
        x=np.zeros(100000);x[0]=1
        a=PianoRoom(20000).render(x,.1,1.2)
        room=PianoRoom(20000)
        b=np.concatenate([room.render(x[i:i+480],.1,1.2) for i in range(0,len(x),480)])
        np.testing.assert_array_equal(a,b)
        self.assertGreater(np.max(abs(a[600:5000])),1e-4)
        self.assertLess(np.max(abs(a[-20000:])),1e-6)
    def test_room_zero_mix_is_dry(self):
        x=np.random.default_rng(4).normal(size=4000)
        np.testing.assert_array_equal(PianoRoom(20000).render(x,0),x)
    def test_open_key_changes_sympathetic_decay(self):
        x=np.zeros(4000);x[0]=1
        closed=InstrumentBody(20000,'piano');opened=InstrumentBody(20000,'piano')
        opened.set_open_notes((60,))
        a=closed.render(x,.45,.2);b=opened.render(x,.45,.2)
        self.assertTrue(np.isfinite(b).all());self.assertGreater(np.max(abs(a-b)),1e-8)
