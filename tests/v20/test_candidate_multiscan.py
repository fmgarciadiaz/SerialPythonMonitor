import unittest
from monitor.v20.radio_multiscan import scan_profiles
from monitor.v20.receiver.unoq_acquisition import Configuration
from tools.private_rate_profiles_v20 import diagnostic_profiles


class CandidateScanTests(unittest.TestCase):
    def test_internal_2m_uses_qualified_spi40_auxiliaries(self):
        configs=scan_profiles(Configuration(8,2000000))
        self.assertEqual([c.rate for c in configs],[2000000,1600000,1403508])
        self.assertEqual([c.rate for c in scan_profiles(Configuration(8,1860465))],
                         [1860465,1600000,1403508])

    def test_more_bit_candidates_inherit_existing_auxiliaries(self):
        for bits,rates,anchor in ((10,(1379310,),1355932),(12,(1111111,1126760,1142857),1103448)):
            expected=scan_profiles(Configuration(bits,anchor))[1:]
            with diagnostic_profiles(bits,rates):
                for rate in rates:
                    configs=scan_profiles(Configuration(bits,rate))
                    self.assertEqual(len(configs),3)
                    self.assertEqual(configs[0],Configuration(bits,rate))
                    self.assertEqual(configs[1:],expected)
                    self.assertTrue(all(c.bits==bits and c.channels==1 for c in configs))
