import unittest
from types import SimpleNamespace

from monitor.v18.receiver.unoq_acquisition import Configuration, SPI_RATES
from monitor.v18.receiver.unoq_native import PROFILES
from monitor.v18.io.rf_batch import should_compact_adc8_ipc
from monitor.v18.radio_output import acquisition_error


class Adc1818Tests(unittest.TestCase):
    def test_unique_public_profile_and_automatic_compact_transport(self):
        profiles=[p for p in PROFILES if p['bits']==8 and p['ticks']==88]
        self.assertEqual(len(profiles),1)
        config=Configuration(8,1818181)
        self.assertEqual((config.channels,config.period,config.node_pairs),(1,88,3488))
        self.assertIn(1818181,SPI_RATES)
        self.assertTrue(should_compact_adc8_ipc(config))
        self.assertFalse(should_compact_adc8_ipc(config,False))
        self.assertIsNone(acquisition_error(config))
        self.assertFalse(should_compact_adc8_ipc(Configuration(8,1600000)))

    def test_radio_exception_is_exact_and_requires_qualification(self):
        values=dict(bits=8,channels=1,period=88,node_pairs=3488,rate=1818181,
                    _native={'combined_qualified':True})
        for override in ({'node_pairs':3456},{'channels':2},{'period':89},{'_native':{}}):
            self.assertIsNotNone(acquisition_error(SimpleNamespace(**dict(values,**override))))


if __name__=='__main__':unittest.main()
