import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.unoq import Board, source_files, main


class UnoQTests(unittest.TestCase):
    def test_default_and_experimental_targets_are_separate(self):
        for version in ('v4', 'v5'):
            args = ['unoq.py', 'compile'] + (['--version', version] if version == 'v5' else [])
            with self.subTest(version=version), patch('sys.argv', args), patch('tools.unoq.Board') as board:
                self.assertEqual(main(), 0)
                config = board.call_args.args[0]
                self.assertEqual(config['local_app'], f'arduino/{version}/oscilloscope')
                self.assertTrue(config['remote_app'].endswith('-' + version))
                board.return_value.compile.assert_called_once()
                board.return_value.deploy.assert_not_called()

    def test_deploy_does_not_touch_app_when_compile_fails(self):
        board = Board.__new__(Board)
        board.compile = Mock(side_effect=RuntimeError('compile failed'))
        board.backup = Mock()
        board.cli = Mock()
        with self.assertRaises(RuntimeError):
            board.deploy()
        board.backup.assert_not_called()
        board.cli.assert_not_called()

    def test_backup_failure_prevents_stop_and_upload(self):
        board = Board.__new__(Board)
        board.compile = Mock()
        board.backup = Mock(side_effect=RuntimeError('backup failed'))
        board.cli = Mock()
        board.push_sources = Mock()
        with self.assertRaises(RuntimeError):
            board.deploy()
        board.cli.assert_not_called()
        board.push_sources.assert_not_called()

    def test_compile_failure_cleans_only_temporary_directory(self):
        board = Board.__new__(Board)
        board.config = {'fqbn': 'arduino:zephyr:unoq'}
        board.check_sources = Mock(return_value=[])
        board.push_sources = Mock()
        board.shell = Mock(side_effect=[None, subprocess.CalledProcessError(1, 'compile'), None])
        with self.assertRaises(subprocess.CalledProcessError):
            board.compile()
        stage = board.push_sources.call_args.args[1]
        self.assertTrue(stage.startswith('/tmp/serialmonitor-build-'))
        self.assertEqual(board.shell.call_args.args[-1], stage)
        compile_args = board.shell.call_args_list[1].args
        self.assertNotIn('--upload', compile_args)

    def test_source_filter_preserves_assets_excludes_runtime_and_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('python/main.py', 'assets/index.html', '.cache/build.bin', 'data/samples.csv', 'python/__pycache__/x.pyc'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('')
            (root / 'link').symlink_to(root / 'python/main.py')
            self.assertEqual([str(p.relative_to(root)) for p in source_files(root)],
                             ['assets/index.html', 'python/main.py'])

    def test_remote_arguments_are_shell_quoted(self):
        board = Board.__new__(Board)
        board.run = Mock()
        board.shell('test', 'path with spaces', '$(unexpected)')
        self.assertEqual(board.run.call_args.args, ('shell', "test 'path with spaces' '$(unexpected)'"))


if __name__ == '__main__':
    unittest.main()
