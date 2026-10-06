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
        board.config = {'name': 'Scope WAV V12 Audio'}
        return module, board

    def test_new_q_installs_and_targets_selected_serial(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": []}'
        with patch.object(module.subprocess, 'run') as run, patch.dict(module.os.environ):
            module.prepare('another-q')
            self.assertEqual(module.os.environ['UNOQ_SERIAL'], 'another-q')
        board.compile.assert_called_once()
        board.create.assert_called_once()
        board.backup.assert_not_called()
        module.binary.assert_called_once_with(board, build=True, p992=True, audio=True)
        self.assertEqual(run.call_args.args[0][-3:], ['start', '--firmware', 'v12_audio'])

    def test_existing_app_backed_up_and_updated(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Scope WAV V12 Audio", "status": "stopped"}]}'
        with patch.object(module.subprocess, 'run'), patch.dict(module.os.environ):
            module.prepare('q')
        board.backup.assert_called_once()
        board.push_sources.assert_called_once()
        board.create.assert_not_called()

    def test_other_running_app_blocks_changes(self):
        module, board = self.load()
        board.cli.return_value.stdout = '{"apps": [{"name": "Other", "status": "running"}]}'
        with patch.dict(module.os.environ), self.assertRaisesRegex(RuntimeError, 'otra aplicación'):
            module.prepare('q')
        board.compile.assert_not_called()
        module.stop.assert_not_called()
