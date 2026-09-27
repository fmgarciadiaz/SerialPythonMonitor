"""Comprueba reducción visual sin Qt: picos, cortes y detalle al ampliar."""
import ast
import math
import unittest
import numpy as np
from test_v6_roll import WINDOW

method = next(n for n in WINDOW.body if isinstance(n, ast.FunctionDef)
              and n.name == '_reduce_trace_for_display')
method.decorator_list = []
namespace = {'math': math, 'np': np}
exec(compile(ast.Module(body=[method], type_ignores=[]), '<display>', 'exec'), namespace)
reduce_trace = namespace['_reduce_trace_for_display']


class DisplayTests(unittest.TestCase):
    def test_preserves_peaks_order_and_endpoints(self):
        x = list(range(10000))
        y = [math.sin(i / 20) for i in x]
        y[3123], y[3124] = 70, -80
        xp, yp = reduce_trace(x, y, 0, 10000, 200)
        self.assertLessEqual(len(xp), 800)
        self.assertEqual(list(xp), sorted(xp))
        self.assertEqual((xp[0], xp[-1]), (0, 9999))
        self.assertEqual((min(yp), max(yp)), (-80, 70))
        self.assertTrue(all(y[int(i)] == v for i, v in zip(xp, yp)))
        for bucket in range(200):
            original = y[bucket * 50:(bucket + 1) * 50]
            actual = [v for i, v in zip(xp, yp) if i // 50 == bucket]
            self.assertEqual((min(actual), max(actual)), (min(original), max(original)))

    def test_gaps_remain_even_within_single_pixel(self):
        x = [i / 100 for i in range(100)]
        y = [1.] * 100
        y[40] = float('nan')
        y[41:] = [3.] * 59
        xp, yp = reduce_trace(x, y, 0, 100, 1)
        gap = next(i for i, v in enumerate(yp) if math.isnan(v))
        self.assertEqual(xp[gap], x[40])
        self.assertEqual((yp[gap-1], yp[gap+1]), (1, 3))
        self.assertEqual((xp[gap-1], xp[gap+1]), (x[39], x[41]))

    def test_zoom_retains_every_sample_and_step(self):
        x = [0, 1, 1, 2, 2, 3]
        y = [0, 0, 3, 3, 0, 0]
        xp, yp = reduce_trace(x, y, 0, 3, 100)
        self.assertIs(xp, x)
        self.assertIs(yp, y)

    def test_dense_steps_preserve_vertical_edge(self):
        x = [0.] * 100 + [1.] * 100
        y = [0.] * 50 + [3.] * 100 + [0.] * 50
        xp, yp = reduce_trace(x, y, 0, 2, 2)
        self.assertEqual(list(zip(xp, yp)), [(0, 0), (0, 3), (0, 3), (1, 3), (1, 0), (1, 0)])


if __name__ == '__main__':
    unittest.main()
