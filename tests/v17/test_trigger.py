"""Equivalence to the original trigger search, including NaN lookbacks."""
import unittest
import numpy as np
from monitor.v17.trigger import last_trigger_crossing


def reference_crossing(values, level, rising, hysteresis):
    crosses = ((values[1:] >= level) & (values[:-1] < level)) if rising else (
        (values[1:] <= level) & (values[:-1] > level))
    for i in (np.flatnonzero(crosses)+1)[::-1]:
        prior = values[max(0, i-10):i]
        if (np.min(prior) <= level-hysteresis if rising else
                np.max(prior) >= level+hysteresis):
            return int(i)
    return None


class TriggerTests(unittest.TestCase):
    def test_reference_equivalence_noise_bursts_am_and_nonfinite(self):
        rng = np.random.default_rng(1729)
        for count in (0,1,2,9,10,11,80,4000):
            t = np.arange(count)
            tone = np.sin(t*.31)*(1+.5*np.sin(t*.013))
            noise = rng.normal(0,1e-6,count)
            outlier = noise.copy()
            if count:
                outlier[count//3] = -.5
                outlier[count//2] = .5
            nonfinite = tone.copy()
            if count>11:
                nonfinite[::13] = np.nan
                nonfinite[2] = np.inf
                nonfinite[4] = -np.inf
            for values in (tone,noise,outlier,nonfinite,np.zeros(count)):
                for rising in (False,True):
                    for level,hysteresis in ((0.,.015),(.08,.015),(0.,20.)):
                        with self.subTest(count=count,rising=rising,level=level,hysteresis=hysteresis):
                            self.assertEqual(last_trigger_crossing(values,level,rising,hysteresis),
                                             reference_crossing(values,level,rising,hysteresis))

    def test_nan_invalidates_whole_lookback_even_with_arming_sample(self):
        for sign,rising in ((1,True),(-1,False)):
            values=sign*np.array([-.5,np.nan,-.001,.001])
            self.assertIsNone(last_trigger_crossing(values,0.,rising,.015))
            values=sign*np.array([-.5,-.001,.001])
            self.assertEqual(last_trigger_crossing(values,0.,rising,.015),2)


if __name__ == '__main__':
    unittest.main()
