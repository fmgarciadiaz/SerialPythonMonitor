import unittest
import numpy as np
from tools.calibrate_bode import profiles, reference_from
from monitor.v13.receiver.unoq_acquisition import Configuration

class CalibrationMatrixTests(unittest.TestCase):
    def setUp(self):
        self.config=Configuration(14,40000)
        self.identity={'board_serial':'synthetic','app':'test','firmware_sha256':'0'*64}
        f=np.geomspace(20,5000,25)
        self.data=np.column_stack((f,np.full(25,.15),np.full(25,3.)))

    def test_all_supported_profiles_without_invalid_16_bit_rates(self):
        configs=list(profiles())
        self.assertEqual(len(configs),86)
        self.assertEqual(len(set(configs)),86)
        self.assertTrue(all(c.rate<=62500 for c in configs if c.bits==16))

    def test_independent_capture_accepts_repeatable_reference(self):
        ref=reference_from([self.data]*3,self.identity,self.config,'tone')
        self.assertTrue(ref['validation']['accepted'])
        self.assertEqual(ref['instrument'],self.identity)
        self.assertEqual(ref['acquisition'],{'bits':14,'rate':40000})

    def test_validation_does_not_fit_held_out_gain_or_phase(self):
        for column,error in ((1,2),(2,12)):
            check=self.data.copy();check[:,column]+=error
            ref=reference_from([self.data,self.data,check],self.identity,self.config,'sweep')
            self.assertFalse(ref['validation']['accepted'])

    def test_low_coverage_rejects_reference(self):
        check=self.data.copy();check[::2,2]=np.nan
        ref=reference_from([self.data,self.data,check],self.identity,self.config,'pulse_h1')
        self.assertFalse(ref['validation']['accepted'])

    def test_wrapped_phase_is_averaged_as_same_phase(self):
        a=self.data.copy();b=self.data.copy();a[:,2]=179;b[:,2]=-179
        ref=reference_from([a,b,a],self.identity,self.config,'chirp')
        self.assertTrue(ref['validation']['accepted'])
        self.assertAlmostEqual(abs(ref['points'][0][2]),180)

class CalibrationIsolationTests(unittest.TestCase):
    def test_stream_failure_is_recorded_and_completed_profiles_are_not_repeated(self):
        import json
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools import calibrate_bode_matrix as matrix
        with tempfile.TemporaryDirectory() as folder:
            report=Path(folder)/'report.json'
            done=[dict(bits=10,rate=40000,method=m,accepted=True) for m in matrix.METHODS]
            report.write_text(json.dumps(dict(instrument={'app':'scope-pulse-us-v13-main-1'},results=done)))
            args=['calibrate_bode_matrix.py','--report',str(report),'--loopback-confirmed']
            with patch('sys.argv',args), patch.object(matrix,'profiles',return_value=[Configuration(8,125000),Configuration(10,40000)]), patch.object(matrix,'adb',return_value='integrity failure'), patch.object(matrix.subprocess,'run',side_effect=[SimpleNamespace(returncode=1),SimpleNamespace(returncode=0),SimpleNamespace(returncode=0)]) as run:
                matrix.main()
            rows=json.loads(report.read_text())['results']
            rejected=[r for r in rows if r['bits']==8]
            self.assertEqual(len(rejected),4)
            self.assertTrue(all(not r['accepted'] for r in rejected))
            self.assertTrue(all(r['relay_log']=='integrity failure' for r in rejected))
            self.assertEqual(run.call_count,3)
            self.assertIn('--restore-only',run.call_args.args[0])
