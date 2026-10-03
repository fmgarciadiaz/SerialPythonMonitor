"""Compara los vértices optimizados con el trazado original, incluidos huecos."""
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def prepare(path):
    tree = ast.parse(path.read_text())
    window = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SerialMonitorWindow')
    method = next(n for n in window.body if isinstance(n, ast.FunctionDef) and n.name == '_prepare_trace_data')
    namespace = {'np': np, 'List': List, 'Tuple': Tuple}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['_prepare_trace_data']


class TraceTests(unittest.TestCase):
    def test_vertices_match_original_in_both_versions(self):
        reference = prepare(ROOT / 'monitor/historico/SerialMonitorAppQt_V5.py')
        rng = np.random.default_rng(42)
        inputs = [([], []), ([1], [3]), ([0, 1, 2], [5, 8]),
                  ([0, 1, 4000, 4001, 9000], [1, 5, np.nan, -3, 8]),
                  ([0, 4000, 3000, 3000, 9000], [1, 2, 3, 4, 5]),
                  (np.cumsum(rng.choice([1, 40, 2500, 9000], 500)).tolist(), rng.normal(size=500).tolist())]
        for version in ('v6', 'v7'):
            actual = prepare(ROOT / 'monitor' / 'historico' / version / 'app.py')
            for step in ('Escalón', 'Línea'):
                for cut in (False, True):
                    for time_mode, dt in ((False, 0), (True, 0), (True, 40), (True, 5000)):
                        state = SimpleNamespace(trace_mode=step, auto_gap_cut=cut,
                                                x_axis_time_mode=time_mode, current_dt_us=dt)
                        for x, y in inputs:
                            with self.subTest(version=version, step=step, cut=cut, time=time_mode, dt=dt, n=len(x)):
                                expected = reference(state, x, y)
                                result = actual(state, x, y)
                                np.testing.assert_equal(result[0], expected[0])
                                np.testing.assert_equal(result[1], expected[1])


if __name__ == '__main__':
    unittest.main()
