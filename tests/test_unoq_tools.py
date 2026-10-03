import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.unoq import Board, source_files, main


class UnoQTests(unittest.TestCase):
    def test_ready_boot_changes_gpio_only_while_mcu_is_reset(self):
        board = Board.__new__(Board)
        board.config = {'ready_boot': {'chip': 'gpiochip1', 'ready_line': 70, 'reset_line': 38}}
        board.remote = '/app'
        history = Mock()
        board.cli = history.cli
        board.shell = history.shell
        board.start()
        self.assertEqual(history.mock_calls, [
            call.cli('app', 'stop', '/app'),
            call.shell('gpioset', '-c', 'gpiochip1', '-t0', '38=0'),
            call.shell('gpioset', '-c', 'gpiochip1', '-t0', '70=1'),
            call.shell('gpioset', '-c', 'gpiochip1', '-t0', '38=1'),
            call.cli('app', 'start', '/app')])

    def test_ready_boot_releases_reset_if_gpio_setup_fails(self):
        board = Board.__new__(Board)
        board.config = {'ready_boot': {'chip': 'gpiochip1', 'ready_line': 70, 'reset_line': 38}}
        board.remote = '/app'
        board.cli = Mock()
        board.shell = Mock(side_effect=[None, RuntimeError('GPIO busy'), None])
        with self.assertRaises(RuntimeError):
            board.start()
        self.assertEqual(board.shell.call_args.args[-1], '38=1')
        board.cli.assert_called_once_with('app', 'stop', '/app')

    def test_normal_start_does_not_touch_gpio(self):
        board = Board.__new__(Board)
        board.config = {}
        board.remote = '/app'
        board.cli, board.shell = Mock(), Mock()
        board.start()
        board.cli.assert_called_once_with('app', 'start', '/app')
        board.shell.assert_not_called()

    def test_ready_stop_restores_loader_level_for_other_variants(self):
        board = Board.__new__(Board)
        board.config = {'ready_boot': {'chip': 'gpiochip1', 'ready_line': 70, 'reset_line': 38}}
        board.remote = '/app'
        board.cli, board.shell = Mock(), Mock()
        board.stop()
        board.cli.assert_called_once_with('app', 'stop', '/app')
        self.assertEqual([c.args[-1] for c in board.shell.call_args_list], ['38=0', '70=1', '38=1'])

    def test_adc_is_separate_and_preserves_ready_boot(self):
        with patch('sys.argv', ['unoq.py', 'compile', '--version', 'v6_adc']), patch('tools.unoq.Board') as board:
            self.assertEqual(main(), 0)
            config = board.call_args.args[0]
            self.assertEqual(config['local_app'], 'arduino/historico/v6_adc/oscilloscope')
            self.assertEqual(config['ready_boot']['ready_line'], 70)
            board.return_value.compile.assert_called_once()
            board.return_value.deploy.assert_not_called()

    def test_irq_ready_is_a_separate_target(self):
        with patch('sys.argv', ['unoq.py', 'compile', '--version', 'v6_irq']), patch('tools.unoq.Board') as board:
            self.assertEqual(main(), 0)
            config = board.call_args.args[0]
            self.assertEqual(config['local_app'], 'arduino/historico/v6_irq/spi_benchmark')
            self.assertTrue(config['remote_app'].endswith('/scope-spi-irq-ready-v6'))
            board.return_value.compile.assert_called_once()
            board.return_value.deploy.assert_not_called()

    def test_dma_is_a_separate_target(self):
        with patch('sys.argv', ['unoq.py', 'compile', '--version', 'v6_dma']), patch('tools.unoq.Board') as board:
            self.assertEqual(main(), 0)
            config = board.call_args.args[0]
            self.assertEqual(config['local_app'], 'arduino/historico/v6_dma/spi_benchmark')
            self.assertTrue(config['remote_app'].endswith('/scope-spi-dma-v6'))
            board.return_value.compile.assert_called_once()
            board.return_value.deploy.assert_not_called()

    def test_register_polling_is_a_separate_target(self):
        with patch('sys.argv', ['unoq.py', 'compile', '--version', 'v6_polling']), patch('tools.unoq.Board') as board:
            self.assertEqual(main(), 0)
            config = board.call_args.args[0]
            self.assertEqual(config['local_app'], 'arduino/historico/v6_polling/spi_benchmark')
            self.assertTrue(config['remote_app'].endswith('/scope-spi-polling-v6'))
            board.return_value.compile.assert_called_once()
            board.return_value.deploy.assert_not_called()

    def test_spi_benchmark_is_an_independent_explicit_target(self):
        with patch('sys.argv', ['unoq.py', 'compile', '--version', 'v6']), patch('tools.unoq.Board') as board:
            self.assertEqual(main(), 0)
            config = board.call_args.args[0]
            self.assertEqual(config['local_app'], 'arduino/historico/v6/spi_benchmark')
            self.assertTrue(config['remote_app'].endswith('/scope-spi-benchmark-v6'))
            board.return_value.compile.assert_called_once()
            board.return_value.deploy.assert_not_called()

    def test_default_and_experimental_targets_are_separate(self):
        for version in ('v8_config', 'v6_adc', 'v4', 'v5'):
            args = ['unoq.py', 'compile'] + (['--version', version] if version != 'v8_config' else [])
            with self.subTest(version=version), patch('sys.argv', args), patch('tools.unoq.Board') as board:
                self.assertEqual(main(), 0)
                config = board.call_args.args[0]
                self.assertEqual(config['local_app'], f'arduino/{"historico/" if version != "v8_config" else ""}{version}/oscilloscope')
                self.assertTrue(config['remote_app'].endswith({'v6_adc':'-v6','v8_config':'-v8'}.get(version, '-' + version)))
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
