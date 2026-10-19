import unittest
import numpy as np
from monitor.v17.radio_scan import scan_carriers,SCAN_SIZE,SCAN_BLOCKS


class ScanTests(unittest.TestCase):
    def test_weak_carrier_sidebands_and_transient(self):
        rate=160000000/114
        n=SCAN_SIZE*SCAN_BLOCKS;t=np.arange(n)/rate
        rng=np.random.default_rng(4)
        x=rng.normal(0,.015,n)
        x+=(1+.4*np.sin(2*np.pi*1000*t))*np.cos(2*np.pi*100000*t)
        x+=.04*np.cos(2*np.pi*300000*t)
        x[:SCAN_SIZE]+=.7*np.cos(2*np.pi*450000*t[:SCAN_SIZE])
        peaks=scan_carriers(x,rate)
        self.assertEqual(len(peaks),2,peaks)
        np.testing.assert_allclose([p['frequency'] for p in peaks],[100000,300000],atol=3)

    def test_scan_excludes_carriers_without_room_for_both_sidebands(self):
        from monitor.v17.radio_am import radio_tuning_max
        rate=160000000/267;t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/rate
        values=np.random.default_rng(91).normal(0,.001,len(t))
        values+=.5*np.cos(2*np.pi*50000*t)+np.cos(2*np.pi*(rate/2-1000)*t)
        peaks=scan_carriers(values,rate)
        self.assertTrue(any(abs(p['frequency']-50000)<5 for p in peaks))
        self.assertTrue(all(p['frequency']<=radio_tuning_max(rate) for p in peaks))

    def test_noise_and_invalid_input(self):
        values=np.random.default_rng(7).normal(size=SCAN_SIZE*SCAN_BLOCKS)
        self.assertEqual(scan_carriers(values,160000000/114),[])
        with self.assertRaises(ValueError):scan_carriers(values[:1024],1403508)

    def test_strict_thresholds_preserve_strong_and_reject_weak_carrier(self):
        rate=160000000/114;t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/rate
        rf=np.random.default_rng(29).normal(0,.015,len(t))
        rf+=.5*np.cos(2*np.pi*100000*t)+.003*np.cos(2*np.pi*300000*t)
        normal=scan_carriers(rf,rate,12)
        strict=scan_carriers(rf,rate,60,3)
        self.assertTrue(any(abs(p['frequency']-300000)<3 for p in normal))
        self.assertTrue(any(abs(p['frequency']-100000)<3 for p in strict))
        self.assertFalse(any(abs(p['frequency']-300000)<3 for p in strict))
        with self.assertRaises(ValueError):scan_carriers(rf,rate,61)
