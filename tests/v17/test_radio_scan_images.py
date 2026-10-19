import unittest
import numpy as np
from monitor.v17.radio_scan import scan_carriers,SCAN_SIZE,SCAN_BLOCKS

class ScanImageTests(unittest.TestCase):
    def test_dac_images_remain_candidates_in_normal_search(self):
        fs=160000000/114
        t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/fs
        dac_time=np.floor(t*256000)/256000
        rf=(np.cos(2*np.pi*20000*dac_time)+np.cos(2*np.pi*40000*dac_time))
        rf+=np.random.default_rng(8).normal(0,.01,len(t))
        wide=scan_carriers(rf,fs)
        self.assertGreater(len(wide),2)
        self.assertTrue(any(abs(x['frequency']-20000)<3 for x in wide))
        self.assertTrue(any(abs(x['frequency']-40000)<3 for x in wide))
        self.assertTrue(all('dbfs' in x and x['persistence']>=2 for x in wide))

    def test_adc8_weak_station_not_hidden_by_strong_station(self):
        fs=160000000/114;t=np.arange(SCAN_SIZE*SCAN_BLOCKS)/fs
        signal=1.65+.5*np.cos(2*np.pi*100000*t)+.001*np.cos(2*np.pi*300000*t)
        signal+=np.random.default_rng(17).normal(0,.015,len(t))
        adc=np.rint(signal*255/3.3)*3.3/255
        peaks=scan_carriers(adc,fs,12)
        self.assertTrue(any(abs(p['frequency']-100000)<3 for p in peaks))
        self.assertTrue(any(abs(p['frequency']-300000)<3 for p in peaks),peaks)
