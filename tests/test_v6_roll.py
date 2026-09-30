"""Pruebas del cabezal visual sin requerir Qt ni hardware serial."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / 'monitor/v6/app.py').read_text())
WINDOW = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'SerialMonitorWindow')
METHOD = next(n for n in WINDOW.body if isinstance(n, ast.FunctionDef) and n.name == '_roll_end_position')
CONSTANT = next(n.value.value for n in TREE.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'ROLL_SMOOTH_SECONDS' for t in n.targets))
NS = {'math': math, 'ROLL_SMOOTH_SECONDS': CONSTANT}
exec(compile(ast.Module(body=[METHOD], type_ignores=[]), '<roll>', 'exec'), NS)
advance = NS['_roll_end_position']


class RollTests(unittest.TestCase):
    def window(self):
        return SimpleNamespace(h_scale=9000, h_pos=0, x_axis_time_mode=False,
                               sample_counter=20000, _roll_position=None,
                               _roll_time=None, _roll_context=None)

    def test_batch_moves_across_frames_and_settles_without_overshoot(self):
        w = self.window()
        self.assertEqual(advance(w, 20000, 0), 20000)
        w.sample_counter += 512
        positions = [advance(w, 20512, i * .016) for i in range(1, 101)]
        self.assertTrue(20000 < positions[0] < 20512)
        self.assertTrue(all(a <= b <= 20512 for a, b in zip(positions, positions[1:])))
        self.assertEqual(positions[-1], 20512)
        self.assertEqual(w.sample_counter, 20512)

    def test_full_buffer_keeps_absolute_motion(self):
        w = self.window()
        w.sample_counter = 110000
        advance(w, 110000, 0)
        w.sample_counter += 512
        relative = advance(w, 110000, .016)
        self.assertTrue(110000 < relative + 512 < 110512)
        self.assertTrue(w.h_scale <= relative <= 110000)

    def test_controls_and_long_pause_reposition(self):
        for field, value in [('h_scale', 20000), ('h_pos', -20), ('x_axis_time_mode', True)]:
            w = self.window()
            advance(w, 20000, 0)
            w.sample_counter += 512
            setattr(w, field, value)
            self.assertEqual(advance(w, 20512, .016), 20512)
        w = self.window()
        advance(w, 20000, 0)
        w.sample_counter += 512
        self.assertEqual(advance(w, 20512, 1), 20512)

    def test_buffer_boundary_and_reset(self):
        w = self.window()
        w.sample_counter = 300000
        w.h_scale = 20000
        w._roll_position = 100
        w._roll_context = (20000, 0, False)
        w._roll_time = 0
        self.assertEqual(advance(w, 110000, .016), 20000)
        w._roll_position = None
        w.sample_counter = 20000
        self.assertEqual(advance(w, 20000, .032), 20000)

    def test_acquisition_recording_and_trace_processing_unchanged(self):
        old = ast.parse((ROOT / 'monitor/historico/SerialMonitorAppQt_V5.py').read_text())
        old_classes = {n.name: n for n in old.body if isinstance(n, ast.ClassDef)}
        new_classes = {n.name: n for n in TREE.body if isinstance(n, ast.ClassDef)}
        self.assertEqual(ast.dump(old_classes['SerialWorker']), ast.dump(new_classes['SerialWorker']))
        methods = lambda c: {n.name: ast.dump(n) for n in c.body if isinstance(n, ast.FunctionDef)}
        old_methods = methods(old_classes['SerialMonitorWindow'])
        new_methods = methods(WINDOW)
        for name in old_methods:
            if ('record' in name and name != 'start_recording') or name in ('handle_batch', '_prepare_trace_data'):
                self.assertEqual(old_methods[name], new_methods[name], name)


if __name__ == '__main__':
    unittest.main()
