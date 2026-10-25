import unittest
from diagnosticos.wav_cases_v17 import select_cases, near_eof_delta
from monitor.v17.receiver.unoq_acquisition import Configuration


class WavDiagnosticCasesTests(unittest.TestCase):
    def test_eof_seek_uses_actual_file_length_and_playhead(self):
        for duration in (179.5933125,229.7846875):
            delta=near_eof_delta(duration,150000,50000)
            self.assertAlmostEqual(150000/50000+delta,duration-3)
        self.assertEqual(near_eof_delta(2,50000,50000),-1)

    def test_matrix_uses_supported_public_acquisition_and_output_rates(self):
        cases,duration = select_cases(['--stability-matrix','--seconds','60'])
        self.assertEqual(duration,60)
        self.assertEqual([case[0] for case in cases],[8,10,12,14,16])
        for bits,rate,audio in cases:
            self.assertLessEqual(Configuration(bits,rate).rate,100000)
            self.assertEqual(audio,50000)

    def test_explicit_case_and_selection_only_preserve_rate_guard(self):
        self.assertEqual(select_cases(['--case','12','100000','40000','--seconds','120']),(((12,100000,40000),),120))
        cases,duration = select_cases(['--select-only'])
        self.assertEqual((cases,duration),(((8,1600000,50000),),10))
        for args in (['--case','8','1600000','50000'],['--case','8'],
                     ['--seconds','nan'],['--case','8','40000','48000'],
                     ['--stability-matrix','--controls'],['--stability-matrix','--case','8','40000','50000']):
            with self.subTest(args=args),self.assertRaises(ValueError): select_cases(args)
