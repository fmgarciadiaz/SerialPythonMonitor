import unittest
import numpy as np
from experimentos.radio_ipc_compact_v17.peak_selection import strongest
from experimentos.radio_ipc_compact_v17.peak_selection import make_analyze_candidate


class SelectionTests(unittest.TestCase):
    def test_exact_stable_order_random_ties_and_infinities(self):
        rng=np.random.default_rng(1234)
        for size in (0,1,4,5,6,10,100,10000):
            for _ in range(20):
                amplitude=rng.integers(0,20,size=size).astype(float)
                if size > 10:
                    amplitude[::11]=np.inf
                candidates=rng.permutation(size)
                expected=candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]
                np.testing.assert_array_equal(strongest(candidates,amplitude),expected)

    def test_input_is_unchanged_and_strided_views_work(self):
        amplitude=np.arange(1000,dtype=float)[::-2]
        candidates=np.arange(len(amplitude))[::2]
        before=amplitude.copy(); indices=candidates.copy()
        expected=candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]
        np.testing.assert_array_equal(strongest(candidates,amplitude),expected)
        np.testing.assert_array_equal(amplitude,before)
        np.testing.assert_array_equal(candidates,indices)

    def test_nan_fallback_preserves_original_sort_semantics(self):
        amplitude=np.array([np.nan,2.,1.,np.nan,5.,4.,3.,np.inf])
        candidates=np.arange(len(amplitude))
        expected=candidates[np.argsort(-amplitude[candidates],kind='stable')[:5]]
        np.testing.assert_array_equal(strongest(candidates,amplitude),expected)

    def test_full_analysis_exact_for_windows_rates_and_segment_counts(self):
        from monitor.v17.spectral_analysis import analyze
        candidate=make_analyze_candidate(analyze)
        rng=np.random.default_rng(251)
        for n in (65,1024,65536):
            for window in ('Hann','Rectangular'):
                for fs in (40000,1600000):
                    values=rng.normal(0,.1,n*2)
                    before=values.copy()
                    expected=analyze(values,fs,n=n,window=window)
                    actual=candidate(values,fs,n=n,window=window)
                    for field in ('frequencies','amplitude','phase','psd'):
                        np.testing.assert_array_equal(getattr(actual,field),getattr(expected,field))
                    self.assertEqual(actual.peaks,expected.peaks)
                    np.testing.assert_array_equal(values,before)

    def test_later_fft_instrumentation_remains_visible(self):
        from unittest.mock import patch
        from monitor.v17 import spectral_analysis
        candidate=make_analyze_candidate(spectral_analysis.analyze)
        with patch.object(spectral_analysis,'_fft',wraps=spectral_analysis._fft) as measured:
            candidate(np.arange(128,dtype=float),40000,n=128)
        self.assertEqual(measured.call_count,1)


if __name__=='__main__':
    unittest.main()
