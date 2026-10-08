import unittest
from dataclasses import replace
import numpy as np
from monitor.v15.fm_feedback import warmup, modulate
from monitor.v15.fm_source import FMSource, FMParameters

class FeedbackTests(unittest.TestCase):
    def test_compiled_envelopes_match_numpy_during_live_changes(self):
        from unittest.mock import patch
        if not warmup(): self.skipTest('Numba no instalado')
        params=FMParameters(envelope=(.002,.01,.4,.05),osc3_mix=.3,
                            osc3_envelope=(.003,.02,.7,.08))
        compiled=FMSource(rate=20000,parameters=params)
        reference=FMSource(rate=20000,parameters=params)
        for i in range(0,6000,480):
            if i==1440:
                params=replace(params,gate=False)
                compiled.update(params);reference.update(params)
            if i==2400:
                params=replace(params,envelope=(.001,.01,.2,.01))
                compiled.update(params);reference.update(params)
            actual=compiled[i:i+480]
            with patch('monitor.v15.fm_source.envelope_kernel',None):
                expected=reference[i:i+480]
            self.assertLessEqual(np.max(abs(actual.astype(int)-expected.astype(int))),1)
            self.assertEqual(compiled.envelope_stage,reference.envelope_stage)

    def test_feedback_state_is_continuous_between_blocks(self):
        if not warmup(): self.skipTest('Numba no instalado')
        phase=np.arange(10000)*.073
        whole=modulate(phase,4,np.zeros(2))
        state=np.zeros(2)
        parts=np.concatenate([modulate(phase[i:i+480],4,state) for i in range(0,len(phase),480)])
        np.testing.assert_array_equal(whole,parts)
        self.assertGreater(np.std(whole-np.sin(phase)),.05)
        self.assertLessEqual(np.max(abs(whole)),1)

    def test_third_oscillator_feedback_release_and_stream(self):
        if not warmup(): self.skipTest('Numba no instalado')
        params=FMParameters(notes=((60,127),),osc3_mix=.4,osc3_feedback=4,
                            envelope=(.001,.01,0,.01),osc3_envelope=(.001,.02,1,.2))
        source=FMSource(rate=20000,parameters=params)
        source[0:2000]
        self.assertEqual(len(source.voices),1)
        source.update(replace(params,notes=()))
        for i in range(2000,10000,480): source[i:min(i+480,10000)]
        self.assertEqual(len(source.voices),0)

    def test_three_pairs_chunk_continuity(self):
        if not warmup(): self.skipTest('Numba no instalado')
        params=FMParameters(osc3_mix=.26,osc3_feedback=4,osc2_wave='fm',osc2_mix=.25,
                            osc2_fm_ratio=14,osc2_fm_amount=.55,envelope=(.003,2.8,0,.2))
        whole=FMSource(rate=20000,parameters=params)[0:4800]
        source=FMSource(rate=20000,parameters=params)
        parts=np.concatenate([source[i:i+480] for i in range(0,4800,480)])
        self.assertLessEqual(np.max(abs(whole.astype(int)-parts.astype(int))),1)
