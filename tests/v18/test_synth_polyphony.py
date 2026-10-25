import unittest
from dataclasses import replace
import numpy as np
from monitor.v18.fm_source import FMSource, FMParameters, MAX_VOICES

class SynthPolyphonyTests(unittest.TestCase):
    def test_twenty_notes_and_steal_preserve_held_voices(self):
        self.assertEqual(MAX_VOICES,20)
        p=FMParameters(waveform='sine',notes=tuple((n,100) for n in range(40,60)))
        source=FMSource(20000,p)
        audio=source._render(slice(0,480),quantize=False)
        self.assertTrue(np.isfinite(audio).all())
        self.assertGreater(np.max(np.abs(audio)),0)
        self.assertEqual(set(source.voices),set(range(40,60)))
        retained={n:source.voices[n] for n in range(41,60)}
        source.update(replace(p,notes=tuple((n,100) for n in range(41,61)),note_id=1))
        source[480:960]
        self.assertEqual(set(source.voices),set(range(41,61)))
        for note,voice in retained.items():self.assertIs(source.voices[note],voice)
        source.update(replace(p,notes=(),note_id=2))
        for start in range(960,4960,480):source[start:start+480]
        self.assertFalse(source.voices)

    def test_unbounded_input_rejected(self):
        with self.assertRaises(ValueError):
            FMSource(20000,FMParameters(notes=tuple((n,100) for n in range(40,61))))

    def test_sustained_chord_recycled_in_one_batch(self):
        p=FMParameters(waveform='sine',virtual_sustain=True,
                       notes=tuple((n,100) for n in range(40,60)))
        source=FMSource(20000,p);source[0:480]
        held={n:source.voices[n] for n in range(50,60)}
        chord=tuple((n,100) for n in range(50,70))
        source.update(replace(p,notes=chord,note_id=1));source[480:960]
        self.assertEqual(set(source.voices),set(range(50,70)))
        for note,voice in held.items():self.assertIs(source.voices[note],voice)
        source.update(replace(p,notes=(),virtual_sustain=False))
        for start in range(960,4960,480):
            self.assertTrue(np.isfinite(source._render(slice(start,start+480),quantize=False)).all())
        self.assertFalse(source.voices)
