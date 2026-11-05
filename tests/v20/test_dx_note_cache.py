import hashlib,json,sys,types,unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from monitor.v20 import fm_source as current
ROOT=Path(__file__).resolve().parents[2]

class DxNoteCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'respaldos/host/v20_before_dx_note_cache_20261102'
        text=(folder/'fm_source.py').read_bytes()
        expected=json.loads((folder/'manifest.json').read_text())['before_sha256']
        if hashlib.sha256(text).hexdigest()!=expected:raise RuntimeError('Baseline source changed')
        name='monitor.v20._dx_original_test';cls.old=types.ModuleType(name);cls.old.__file__=str(folder/'fm_source.py')
        sys.modules[name]=cls.old;exec(compile(text,cls.old.__file__,'exec'),cls.old.__dict__)
        data=json.loads((ROOT/'tests/v20/fixtures/dx_piano_parameters.json').read_text())
        for key,value in data.items():
            if isinstance(value,list):data[key]=tuple(tuple(x) if isinstance(x,list) else x for x in value)
        cls.parameters=current.FMParameters(**data)

    def test_float_audio_exact_for_chords_note_changes_and_release(self):
        for rate in (20000,40000):
            p=replace(self.parameters,notes=tuple((n,100) for n in range(48,68)))
            a=self.old.FMSource(rate,p);b=current.FMSource(rate,p)
            for i in range(120):
                if i in (40,80,100):
                    notes=tuple((n,95) for n in range(49,69)) if i==40 else () if i==80 else tuple((n,110) for n in range(60,80))
                    p=replace(p,notes=notes,note_id=i);a.update(p);b.update(p)
                np.testing.assert_array_equal(a._render(slice(i*480,(i+1)*480),quantize=False),b._render(slice(i*480,(i+1)*480),quantize=False))
                self.assertEqual(set(a.voices),set(b.voices))

    def test_frequency_ramps_and_gate_changes_preserve_float_audio(self):
        for rate in (20000,40000):
            p=replace(self.parameters,notes=None,carrier=130.81,modulator=130.81)
            a=self.old.FMSource(rate,p);b=current.FMSource(rate,p)
            for i in range(60):
                if i in (20,30,40,50):
                    frequency={20:200.,30:400.,40:400.,50:55.}[i]
                    p=replace(p,carrier=frequency,modulator=frequency,gate=i!=40,note_id=i)
                    a.update(p);b.update(p)
                np.testing.assert_array_equal(a._render(slice(i*480,(i+1)*480),quantize=False),b._render(slice(i*480,(i+1)*480),quantize=False))

    def test_dac_codes_and_gain_state_preserved(self):
        p=replace(self.parameters,notes=tuple((n,100) for n in range(48,68)))
        a=self.old.FMSource(40000,p);b=current.FMSource(40000,p)
        for i in range(40):
            level=.5 if i<20 else 1.
            np.testing.assert_array_equal(a.render_dac_codes(i*480,(i+1)*480,level,1.65),b.render_dac_codes(i*480,(i+1)*480,level,1.65))
        self.assertEqual(a.compressor_gain,b.compressor_gain)

    def test_cache_has_fixed_bound_and_only_immutable_coefficients(self):
        current._dx_note_values.cache_clear()
        for i in range(400):
            values=current._dx_note_values(20.+i)
            self.assertEqual(len(values),2)
            self.assertTrue(all(np.isscalar(v) for v in values))
        self.assertEqual(current._dx_note_values.cache_info().currsize,256)
