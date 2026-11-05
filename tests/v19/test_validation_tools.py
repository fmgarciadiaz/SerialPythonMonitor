import signal
import subprocess
import unittest
from unittest.mock import Mock,patch
from tools import validate_v19


class ValidationToolTests(unittest.TestCase):
    def test_timeout_requests_restore_instead_of_killing_owner(self):
        process=Mock(returncode=0)
        process.wait.side_effect=[subprocess.TimeoutExpired('probe',1),0]
        with patch.object(validate_v19.subprocess,'Popen',return_value=process):
            self.assertEqual(validate_v19.run_case(['probe'],Mock(),1),1)
        process.send_signal.assert_called_once_with(signal.SIGTERM)
        process.kill.assert_not_called()

    def test_unresponsive_owner_stops_matrix_without_forced_kill(self):
        process=Mock();process.wait.side_effect=subprocess.TimeoutExpired('probe',1)
        with patch.object(validate_v19.subprocess,'Popen',return_value=process):
            with self.assertRaisesRegex(RuntimeError,'sigue activo'):
                validate_v19.run_case(['probe'],Mock(),1)
        process.kill.assert_not_called()

    def test_catalogue_and_retired_entrypoints_cannot_restore_historical_pair(self):
        self.assertTrue(all(row[1]=='v19' for row in validate_v19.CASES))
        from tools import run_stack_diag_v19,probe_v19_normal_pair
        for module in (run_stack_diag_v19,probe_v19_normal_pair):
            with patch.object(module,'Q') as board:
                with self.assertRaisesRegex(RuntimeError,'histórica retirada'):module.run(Mock())
                board.assert_not_called()
