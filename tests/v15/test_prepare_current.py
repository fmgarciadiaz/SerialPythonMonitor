import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TOOLS = Path(__file__).resolve().parents[2] / 'tools'

class PrepareQTests(unittest.TestCase):
    def load(self):
        with patch.dict(sys.modules, unoq=MagicMock(), usb_stream=MagicMock()):
            spec = importlib.util.spec_from_file_location('prepare_q', TOOLS / 'prepare_q.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        module.config_path.return_value = MagicMock(read_text=lambda: '{}')
        module.config_path.return_value.parents = [None, None, TOOLS.parent]
        board = module.Board.return_value
        board.config = {'name': 'Scope Pulse US V13 Experimental'}
        return module, board

    def test_new_q_installs_and_targets_selected_serial(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": []}'
        with patch.object(module.subprocess, 'run') as run, patch.dict(module.os.environ):
            module.prepare('another-q','v13_pulse')
            self.assertEqual(module.os.environ['UNOQ_SERIAL'], 'another-q')
        board.compile.assert_called_once()
        board.create.assert_called_once()
        board.backup.assert_not_called()
        module.binary.assert_called_once_with(board, p992=True, audio=True)
        self.assertEqual(run.call_args.args[0][-3:], ['start', '--firmware', 'v13_pulse'])

    def test_existing_app_backed_up_and_updated(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Scope Pulse US V13 Experimental", "status": "stopped"}]}'
        with patch.object(module.subprocess, 'run'), patch.dict(module.os.environ):
            module.prepare('q','v13_pulse')
        board.backup.assert_called_once()
        board.push_sources.assert_called_once()
        board.create.assert_not_called()

    def test_other_running_app_blocks_changes(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Other", "status": "running"}]}'
        with patch.dict(module.os.environ), self.assertRaisesRegex(RuntimeError, 'otra aplicación'):
            module.prepare('q','v13_pulse')
        board.compile.assert_not_called()
        module.stop.assert_not_called()

    def test_pulse_firmware_is_selected_explicitly(self):
        module, board = self.load()
        board.config = {'name':'Scope Pulse US V13 Experimental'}
        board.cli.return_value.stdout = '{"apps": []}'
        with patch.object(module.subprocess,'run') as run,patch.dict(module.os.environ):
            module.prepare('q','v13_pulse')
        module.config_path.assert_any_call('v13_pulse')
        self.assertEqual(run.call_args.args[0][-3:],['start','--firmware','v13_pulse'])

    def test_missing_relay_is_compiled(self):
        module,board = self.load()
        board.cli.return_value.stdout = '{"apps": []}'
        module.binary.side_effect = [module.subprocess.CalledProcessError(1,['test']),'/relay']
        with patch.object(module.subprocess,'run'),patch.dict(module.os.environ):
            module.prepare('q','v13_pulse')
        self.assertEqual(module.binary.call_count,2)
        module.binary.assert_called_with(board,build=True,p992=True,audio=True)

    def test_relay_failure_does_not_stop_existing_app(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Scope Pulse US V13 Experimental", "status": "running"}]}'
        module.binary.side_effect = [module.subprocess.CalledProcessError(1,['test']),RuntimeError('compile failed')]
        with patch.dict(module.os.environ), self.assertRaisesRegex(RuntimeError,'compile failed'):
            module.prepare('q','v13_pulse')
        board.stop.assert_not_called();module.stop.assert_not_called()
        board.push_sources.assert_not_called()

    def test_late_failure_reports_backup_and_no_success(self):
        import io
        from contextlib import redirect_stdout
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Scope Pulse US V13 Experimental", "status": "stopped"}]}'
        board.backup.return_value='/backup.zip'
        board.push_sources.side_effect=RuntimeError('push failed')
        output=io.StringIO()
        with redirect_stdout(output), patch.dict(module.os.environ), self.assertRaisesRegex(RuntimeError,'push failed'):
            module.prepare('q','v13_pulse')
        self.assertIn('/backup.zip',output.getvalue())
        self.assertIn('sin confirmar',output.getvalue())
        self.assertNotIn('Q preparado:',output.getvalue())
