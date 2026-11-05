import unittest
import numpy as np
from monitor.v20.fm_source import FMParameters,FMSource
from tools.synth_transition_scenario_v20 import synth_probe_parameters
from tools.probe_working_v20_gui import command
from pathlib import Path

class SustainedProbeTests(unittest.TestCase):
    def test_panel_parameters_are_preserved_except_requested_notes(self):
        original=FMParameters(preset='Manual',waveform='sine',envelope=(.02,.1,0.,.3),index=3.)
        actual=synth_probe_parameters(original,20)
        from dataclasses import replace
        self.assertEqual(replace(actual,notes=original.notes),original)
        self.assertEqual(len(actual.notes),20)

    def test_rejects_invalid_profile_and_voice_count(self):
        for count,profile in ((0,'panel'),(21,'panel'),(True,'panel'),(20,'unknown')):
            with self.assertRaises(ValueError):synth_probe_parameters(FMParameters(),count,profile)

    def test_real_engine_keeps_twenty_voices_in_sustain_at_both_rates(self):
        for rate in (20000,40000):
            with self.subTest(rate=rate):
                source=FMSource(rate,synth_probe_parameters(FMParameters(),20,'sustained-fm'))
                for start in range(0,rate*3,480):
                    codes=source[start:min(start+480,rate*3)]
                    self.assertEqual(len(source.voices),20)
                    self.assertEqual(codes.dtype,np.dtype('uint16'))
                self.assertTrue(all(v.envelope_stage=='sustain' and v.envelope_value>.5 for v in source.voices.values()))
                self.assertGreater(float(np.std(codes.astype(float))),1.)

    def test_sustained_check_rejects_missing_or_decaying_voice_observations(self):
        from tools.synth_transition_scenario_v20 import SynthTransition
        state=SynthTransition();self.assertFalse(state.observed_voices_match(20))
        state.phase='playing';state.observe_voices(20)
        self.assertTrue(state.observed_voices_match(20))
        state.observe_voices(0);self.assertFalse(state.observed_voices_match(20))

    def test_low_rate_control_is_explicit_and_keeps_frequency_in_band(self):
        cmd=command('serial',Path('/tmp/report.json'),20,radio_rate=40000)
        self.assertEqual(cmd[cmd.index('--rate')+1],'40000')
        self.assertEqual(cmd[cmd.index('--frequency-khz')+1],'10')

    def test_wrapper_passes_explicit_profile_without_altering_radio_default(self):
        default=command('serial',Path('/tmp/report.json'),20)
        self.assertNotIn('--synth-profile',default)
        active=command('serial',Path('/tmp/report.json'),20,fm=True,voices=20,synth_hold=60,synth_rate=40000,synth_profile='sustained-fm')
        self.assertEqual(active[active.index('--synth-profile')+1],'sustained-fm')

if __name__=='__main__':unittest.main()
