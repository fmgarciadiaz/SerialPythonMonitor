"""Numerical checks with known signals and independent SciPy estimators."""
import unittest
import numpy as np
from scipy import signal
from monitor.historico.v14 import spectral_analysis as a


class SpectralAnalysisTests(unittest.TestCase):
    def test_psd_and_cross_density_match_scipy_welch(self):
        rng = np.random.default_rng(123)
        n,fs = 1024,32768
        x = rng.normal(size=n*4); y = .4*np.roll(x,3)+rng.normal(0,.02,len(x))
        for name in a.WINDOWS:
            for overlap in (0,.5,.75):
                hop = round(n*(1-overlap)); count = n+3*hop
                kwargs = dict(fs=fs,window=a.WINDOWS[name](n),nperseg=n,noverlap=n-hop,detrend='constant',scaling='density')
                expected_f,expected_psd = signal.welch(x[-count:],**kwargs)
                _,expected_csd = signal.csd(x[-count:],y[-count:],**kwargs)
                actual = a.analyze(x,fs,n,window=name,overlap=overlap,maximum=4)
                cross = a.transfer(x,y,fs,n,window=name,overlap=overlap,maximum=4)
                np.testing.assert_array_equal(actual.frequencies,expected_f)
                np.testing.assert_allclose(actual.psd,expected_psd,rtol=1e-12,atol=1e-15)
                np.testing.assert_allclose(cross['pxy'],expected_csd,rtol=1e-12,atol=1e-15)

    def test_amplitude_dc_nyquist_and_parseval(self):
        n,fs = 4096,4096
        t = np.arange(n)/fs
        x = 1.2+2*np.cos(2*np.pi*128*t)+.4*np.cos(np.pi*np.arange(n))
        result = a.analyze(x,fs,window='Rectangular',remove_dc=False,maximum=1)
        self.assertAlmostEqual(result.amplitude[0],1.2,places=12)
        self.assertAlmostEqual(result.amplitude[128],2,places=12)
        self.assertAlmostEqual(result.amplitude[-1],.4,places=12)
        self.assertAlmostEqual(a.band_power(result),np.mean(x*x),places=12)
        self.assertAlmostEqual(a.band_power(result,100,200),2,places=12)

    def test_hann_parseval_normalization_for_noise(self):
        x = np.random.default_rng(4).normal(size=8192)
        result = a.analyze(x,40000,maximum=1)
        w = np.hanning(len(x)); centered = x-x.mean()
        expected = np.sum((centered*w)**2)/np.sum(w*w)
        self.assertAlmostEqual(a.band_power(result),expected,places=12)
        self.assertAlmostEqual(result.enbw,result.df*1.5,delta=result.df*.001)

    def test_linear_averages_and_actual_segment_count(self):
        fs = 1024;n = 1024;t = np.arange(n)/fs
        x = np.concatenate((np.cos(2*np.pi*50*t),3*np.cos(2*np.pi*50*t)))
        result = a.analyze(x,fs,n,window='Rectangular',overlap=0,maximum=16)
        self.assertEqual(result.segments,2)
        self.assertAlmostEqual(result.amplitude[50],np.sqrt(5),places=12)
        self.assertAlmostEqual(result.psd[50]*result.df,2.5,places=12)
        self.assertEqual(a.analyze(x[:n],fs,n,maximum=16).segments,1)

    def test_off_bin_pure_tone_is_not_false_distortion(self):
        fs = 32768;n = 8192;t = np.arange(n)/fs
        for frequency in (1024.5,1000.123,997.3):
            result = a.distortion(1.65+np.cos(2*np.pi*frequency*t),fs)
            self.assertTrue(result['valid'],result)
            self.assertAlmostEqual(result['fundamental'],frequency,places=7)
            self.assertLess(result['thdn'],1e-9)

    def test_refined_frequency_accounts_for_higher_harmonics(self):
        fs = 32768;n = 8192;t = np.arange(n)/fs
        for frequency,order in ((12.03,4),(1000.123,4),(1000.123,7)):
            x = np.cos(2*np.pi*frequency*t)+.1*np.cos(2*np.pi*order*frequency*t)
            result = a.distortion(x,fs)
            self.assertTrue(result['valid'])
            self.assertAlmostEqual(result['fundamental'],frequency,places=7)
            self.assertAlmostEqual(result['thd'],.1,places=8)
            self.assertLess(result['noise_power'],1e-20)

    def test_nyquist_peak_can_be_dominant_with_other_tones(self):
        n=8192;fs=32768;t=np.arange(n)/fs
        x = (-1.)**np.arange(n)+.1*np.cos(2*np.pi*1024*t)
        result = a.analyze(x,fs,window='Rectangular',maximum=1)
        self.assertEqual(result.peaks[0]['frequency'],fs/2)
        self.assertAlmostEqual(result.peaks[0]['amplitude'],1,places=12)

    def test_harmonics_and_noise_have_correct_ratios(self):
        fs = 32768;n = 8192;t = np.arange(n)/fs;f = 1000.123
        noise = np.random.default_rng(8).normal(0,.005,n)
        x = np.cos(2*np.pi*f*t)+.1*np.cos(4*np.pi*f*t)+.05*np.sin(6*np.pi*f*t)+noise
        result = a.distortion(x,fs)
        self.assertTrue(result['valid'])
        self.assertAlmostEqual(result['thd'],np.sqrt(.1**2+.05**2),delta=.0003)
        self.assertAlmostEqual(result['snr_db'],10*np.log10(.5/.005**2),delta=.3)
        self.assertAlmostEqual(result['sinad_db'],10*np.log10(.5/(.5*(.1**2+.05**2)+.005**2)),delta=.1)
        self.assertGreater(result['thdn'],result['thd'])
        self.assertAlmostEqual(result['harmonics'][1]['dbc'],-20,delta=.05)

    def test_distortion_rejects_noise_short_cycles_zero_and_nyquist(self):
        fs = 32768;n = 8192;t = np.arange(n)/fs
        for seed in range(3): self.assertFalse(a.distortion(np.random.default_rng(seed).normal(size=n),fs)['valid'])
        self.assertFalse(a.distortion(np.zeros(n),fs)['valid'])
        self.assertFalse(a.distortion(np.cos(2*np.pi*8*t),fs,fundamental=8)['valid'])
        self.assertFalse(a.distortion(np.cos(np.pi*np.arange(n)),fs,fundamental=fs/2)['valid'])
        result = a.distortion(np.cos(2*np.pi*6000*t),fs,fundamental=6000)
        self.assertEqual([h['order'] for h in result['harmonics']],[1,2])

    def test_transfer_known_gain_phase_delay_and_coherence(self):
        fs=40000;n=1024;count=8192
        x = np.random.default_rng(5).normal(size=count); y=.5*np.roll(x,4)
        result = a.transfer(x,y,fs,n,maximum=16)
        self.assertEqual(result['segments'],15)
        middle = slice(10,-10)
        self.assertAlmostEqual(np.nanmedian(result['gain_db'][middle]),20*np.log10(.5),delta=.02)
        self.assertGreater(np.nanmedian(result['coherence'][middle]),.998)
        self.assertAlmostEqual(np.nanmedian(result['group_delay_s'][middle]),4/fs,delta=.5/fs)
        self.assertLess(np.nanmedian(result['phase_deg'][10:100]),0)

    def test_transfer_single_coherence_and_group_delay_are_unavailable(self):
        x = np.random.default_rng(9).normal(size=1024)
        result = a.transfer(x,.5*x,40000,maximum=16)
        self.assertTrue(np.all(np.isnan(result['coherence'])))
        self.assertTrue(np.all(np.isnan(result['group_delay_s'])))
        self.assertAlmostEqual(np.nanmedian(result['gain_db']),20*np.log10(.5),places=10)

    def test_uncorrelated_transfer_and_missing_reference_remain_invalid(self):
        rng = np.random.default_rng(11);x = rng.normal(size=16384);y = rng.normal(size=len(x))
        result = a.transfer(x,y,40000,1024,maximum=16)
        self.assertLess(np.nanmedian(result['coherence']),.1)
        self.assertTrue(np.all(np.isnan(result['group_delay_s'])))
        zero = a.transfer(np.zeros(1024),np.ones(1024),40000)
        self.assertTrue(np.all(np.isnan(zero['gain_db'])))
        zero_y = a.transfer(x,np.zeros_like(x),40000,1024,maximum=4)
        self.assertTrue(np.all(np.isneginf(zero_y['gain_db'])))
        self.assertTrue(np.all(np.isnan(zero_y['phase_deg'])))
        with self.assertRaises(ValueError): a.transfer(x,x[:-1],40000,1024,maximum=1)

    def test_invalid_blocks_and_bands_are_not_zero_measurements(self):
        for values in (np.zeros(3),np.array([1,np.nan,2,3])):
            with self.assertRaises(ValueError): a.analyze(values,40000)
        result = a.analyze(np.ones(1024),40000)
        self.assertTrue(np.isnan(a.band_power(result,1000,500)))
        self.assertTrue(np.isnan(a.power_metrics(result)['snr_db']))


if __name__ == '__main__': unittest.main()
