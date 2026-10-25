import unittest
from unittest.mock import patch
import numpy as np
from monitor.historico.v16.virtual_instruments import PianoStrings,InstrumentBody,warmup,modal_kernel
from monitor.historico.v16.piano_room import PianoRoom

class AttackTests(unittest.TestCase):
    def setUp(self):
        if modal_kernel is None:self.skipTest('Numba requerido')
        warmup()
    def test_strike_voicing_preserves_tail_and_treble(self):
        from monitor.historico.v16 import piano_calibration as calibration
        original=calibration.modal_correction
        def previous(frequency,velocity):
            correction=dict(original(frequency,velocity))
            correction['attack_gain']=correction['hammer_gain']=1.
            return correction
        for note in (36,48,60,72,84):
            frequency=440*2**((note-69)/12)
            with patch.object(calibration,'modal_correction',side_effect=previous):
                before=PianoStrings(20000,frequency,velocity=.6,calibrated=True).render(6000,brightness=.78)
            after=PianoStrings(20000,frequency,velocity=.6,calibrated=True).render(6000,brightness=.78)
            np.testing.assert_array_equal(before[2400:],after[2400:])
            if note>=72:
                np.testing.assert_array_equal(before,after)
            else:
                self.assertGreater(np.linalg.norm(after[:1200]),np.linalg.norm(before[:1200]))
    def test_restrike_preserves_ringing_state(self):
        s=PianoStrings(20000,261.625,calibrated=True);s.render(6000)
        state=s.state.copy();s.restrike(.6)
        np.testing.assert_array_equal(s.state,state)
        self.assertTrue(s.residual_strike)
        self.assertTrue(np.isfinite(s.render(4000)).all())
    def test_contact_envelope_matches_causal_convolution(self):
        from monitor.historico.v16.virtual_instruments import contact_envelope_kernel
        force=np.random.default_rng(42).normal(size=97)
        force.setflags(write=False)
        for count,pole in ((13,.9),(2400,.998),(4800,.9995)):
            expected=np.convolve(force,pole**np.arange(count))[:count]
            actual=contact_envelope_kernel(force,count,pole)
            np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)
    def test_shared_release_tail_is_chunk_continuous_and_expires(self):
        def prepared():
            body=InstrumentBody(20000,'piano');body.set_open_notes((60,))
            t=np.arange(10000)/20000
            body.render(.05*np.sin(2*np.pi*261.625565*t),.45,.2)
            body.set_open_notes(())
            self.assertIn(60,body.release_tracks)
            return body
        whole=prepared();expected=whole.render(np.zeros(16000),.45,.2)
        chunks=prepared()
        actual=np.concatenate([chunks.render(np.zeros(n),.45,.2) for n in (137,480,1000,4383,10000)])
        np.testing.assert_allclose(expected,actual,atol=1e-12,rtol=1e-12)
        self.assertGreater(np.max(abs(actual[12000:])),1e-6)
        chunks.render(np.zeros(80000),.45,.2)
        self.assertFalse(chunks.release_tracks)
        whole=prepared();expected=whole.render(np.zeros(80000),.45,.2)
        chunks=prepared()
        actual=np.concatenate([chunks.render(np.zeros(n),.45,.2) for n in (997,12000,37003,30000)])
        np.testing.assert_allclose(expected,actual,atol=1e-12,rtol=1e-12)
        self.assertFalse(chunks.release_tracks)

    def test_pedal_defers_release_tail_and_repress_recycles_it(self):
        body=InstrumentBody(20000,'piano');body.set_open_notes((60,),True)
        body.render(np.ones(4000)*.01,.45,.2,True)
        body.set_open_notes((),True)
        self.assertFalse(body.release_tracks)
        body.set_open_notes((),False)
        self.assertIn(60,body.release_tracks)
        body.set_open_notes((60,),False)
        self.assertNotIn(60,body.release_tracks)
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
