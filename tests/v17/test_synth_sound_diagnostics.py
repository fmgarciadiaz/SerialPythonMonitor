import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from unittest.mock import patch
from monitor.v17.fm_source import FMSource,FMParameters

class SoundDiagnosticTests(unittest.TestCase):
    def test_sustained_gesture_does_not_pump_with_changing_block_peaks(self):
        from dataclasses import replace
        source=FMSource(20000,FMParameters(waveform='sine',notes=((48,90),(55,94))))
        tone=np.sin(np.arange(480)*2*np.pi/80)
        with patch.object(source,'_render',return_value=tone*4):
            source.render_dac_codes(0,480,2.5,1.65)
        held_gain=source.compressor_gain
        for i in range(1,5):
            with patch.object(source,'_render',return_value=tone):
                source.render_dac_codes(i*480,(i+1)*480,2.5,1.65)
            self.assertEqual(source.compressor_gain,held_gain)
        source.update(replace(source.parameters,notes=(),gate=False))
        with patch.object(source,'_render',return_value=tone):
            source.render_dac_codes(2400,2880,2.5,1.65)
        self.assertGreater(source.compressor_gain,held_gain)

    def test_clean_sine_preset_has_only_one_linear_oscillator(self):
        from diagnosticos.synth_presets_v16 import panel_presets
        p=panel_presets(['Seno limpio'])['Seno limpio']
        self.assertEqual(p.waveform,'sine')
        self.assertEqual(p.oscillator_levels,(1.,0.,0.))
        self.assertEqual(p.filter_type,'off')
        self.assertEqual((p.index,p.feedback,p.osc2_feedback,p.osc3_feedback),(0.,0.,0.,0.))
        self.assertEqual(p.room_mix,0.)

    def test_loud_attack_is_scaled_without_flattening_or_soft_limiting(self):
        source=FMSource(20000)
        # A sudden high transient used to escape the 3 ms compressor attack.
        audio=np.sin(np.arange(480)*2*np.pi/80)*4
        source.diagnostic_path=Path('/tmp/unused_sound_metrics')
        with patch.object(source,'_render',return_value=audio):
            actual=source.render_dac_codes(0,480,2.5,1.65)
        volts=actual.astype(float)*3.3/4095-1.65
        np.testing.assert_allclose(volts,audio*(1.28/4),atol=3.3/4095/2+1e-12)
        self.assertEqual(source.soft_limited_samples,0)

    def test_quiet_audio_keeps_unity_gain_and_offset_headroom_is_respected(self):
        for offset in (1.65,1.0,2.0):
            source=FMSource(20000)
            audio=np.sin(np.arange(480)*2*np.pi/80)*.1
            with patch.object(source,'_render',return_value=audio):
                actual=source.render_dac_codes(0,480,1.,offset)
            expected=np.rint((audio*.5+offset)*4095/3.3).astype('<u2')
            np.testing.assert_array_equal(actual,expected)
            self.assertEqual(source.compressor_gain,1.)
            with patch.object(source,'_render',return_value=audio*100):
                actual=source.render_dac_codes(480,960,3.3,offset)
            volts=actual.astype(float)*3.3/4095
            self.assertGreaterEqual(float(volts.min()),.35)
            self.assertLessEqual(float(volts.max()),2.95)

    def test_sound_metadata_preserves_dac_and_records_output_controls(self):
        p=FMParameters(waveform='sine',notes=((69,100),),oscillator_levels=(1.,0.,0.))
        reference=FMSource(20000,p);source=FMSource(20000,p)
        with tempfile.TemporaryDirectory() as folder:
            source.diagnostic_path=Path(folder)/'sound.jsonl'
            expected=reference.render_dac_codes(0,480,.5,1.65)
            actual=source.render_dac_codes(0,480,.5,1.65)
            np.testing.assert_array_equal(actual,expected)
            source.observe_status(SimpleNamespace(state=2,reason=0,accepted=480,played=0,free_blocks=15,rate=20000))
            record=json.loads(source.diagnostic_path.read_text())
            self.assertEqual(record['held_notes'],[[69,100]])
            self.assertEqual(record['oscillator_levels'],[1.,0.,0.])
            self.assertEqual(record['output_amplitude'],.5)
            self.assertGreater(record['last_ac_peak_v'],0.)
            self.assertEqual(record['soft_limited_samples'],0)
