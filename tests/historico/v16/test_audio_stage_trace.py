import unittest
import numpy as np
from dataclasses import replace
from monitor.historico.v16.fm_source import FMSource,FMParameters
from monitor.historico.v16.transport_trace import NumericTransportTrace
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from types import SimpleNamespace

class AudioStageTraceTests(unittest.TestCase):
    def test_instrumentation_preserves_samples_across_chords_pedal_and_release(self):
        p=FMParameters(preset='Piano Virtual',waveform='virtual',virtual_model='piano',notes=((48,100),(60,90)),oscillator_levels=(1.,0.,0.))
        plain=FMSource(20000,p);traced=FMSource(20000,p)
        r=OutputReceiver(SimpleNamespace(),lambda data:None);r.transport_trace=NumericTransportTrace(1000)
        traced.audio_trace=r._trace_transport
        for i in range(12):
            if i==3:p=replace(p,notes=((67,110),),note_id=1,virtual_sustain=True)
            if i==6:p=replace(p,notes=(),virtual_sustain=False)
            plain.update(p);traced.update(p)
            np.testing.assert_array_equal(plain.render_dac_codes(i*480,(i+1)*480,1.,1.65),traced.render_dac_codes(i*480,(i+1)*480,1.,1.65))
        stages={e[0] for e in r.transport_trace.export()['events']}
        self.assertTrue({'source_render','voice_prepare','voice_render','piano_post','dac_convert'}<=stages)
        self.assertTrue(all(v.audio_trace is None for v in traced.voices.values()))

if __name__=='__main__':unittest.main()
