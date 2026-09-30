from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import iniciar_monitor as launcher


class LauncherTests(unittest.TestCase):
    def test_stable_default_and_explicit_experimental(self):
        for version in ('v6', 'v7'):
            args = ['iniciar_monitor.py'] + (['--version', version] if version == 'v7' else [])
            with self.subTest(version=version), patch('sys.argv', args), patch('iniciar_monitor.runpy.run_path') as run:
                launcher.main()
                run.assert_called_once_with(str(launcher.ROOT / 'monitor' / version / 'app.py'), run_name='__main__')

    def test_list_does_not_launch_monitor(self):
        with patch('sys.argv', ['iniciar_monitor.py', '--list']), patch('iniciar_monitor.runpy.run_path') as run:
            launcher.main()
            run.assert_not_called()
