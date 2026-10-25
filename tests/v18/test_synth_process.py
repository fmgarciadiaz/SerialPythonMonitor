from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import multiprocessing as mp
import unittest
from unittest.mock import Mock, patch
import numpy as np
from monitor.v18.fm_source import FMSource,FMParameters
from monitor.v18.synth_process import prepare,render,initialize_worker

class SynthProcessTests(unittest.TestCase):
    def test_worker_activity_off_does_not_create_guard(self):
        with patch('monitor.v18.process_activity.MacActivity') as guard, \
             patch('monitor.v18.process_activity.acquisition_activity_mode', return_value='off'), \
             patch('multiprocessing.util.Finalize') as finalizer:
            initialize_worker()
        guard.assert_not_called()
        finalizer.assert_not_called()

    def test_worker_activity_has_process_exit_cleanup(self):
        activity = Mock()
        with patch('monitor.v18.process_activity.MacActivity', return_value=activity) as guard, \
             patch('monitor.v18.process_activity.acquisition_activity_mode', return_value='user') as mode, \
             patch('multiprocessing.util.Finalize') as finalizer:
            initialize_worker()
        mode.assert_called_once_with('synth')
        guard.assert_called_once_with('user')
        finalizer.assert_called_once_with(None, activity.close, exitpriority=10)
        finalizer.call_args.args[1]()
        activity.close.assert_called_once()

    def test_twenty_voice_renderer_matches_local_and_live_updates(self):
        params=FMParameters(notes=tuple((note,100) for note in range(48,68)))
        local=FMSource(20000,params)
        local.prepare_audio()
        with ProcessPoolExecutor(max_workers=1,mp_context=mp.get_context('spawn')) as pool:
            self.assertTrue(pool.submit(prepare,20000,params).result(30))
            for start in (0,480):
                if start:
                    params=replace(params,notes=tuple((note,90) for note in range(49,69)))
                    local.update(params)
                expected=local.render_dac_codes(start,start+480,1.,1.65)
                actual,metrics=pool.submit(render,start,start+480,params,(1.,1.65)).result(10)
                np.testing.assert_array_equal(actual,expected)
                self.assertEqual(len(metrics['active_notes']),20)
                self.assertEqual(metrics['position'],start+480)

if __name__=='__main__':unittest.main()
