import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]


class LayoutTests(unittest.TestCase):
    def test_runtime_does_not_import_v17_or_experiment_packages(self):
        for path in (ROOT/'monitor/v18').rglob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                names=([node.module] if isinstance(node,ast.ImportFrom) else
                       [alias.name for alias in node.names] if isinstance(node,ast.Import) else [])
                for name in names:
                    self.assertFalse(name and name.startswith(('monitor.v17','experimentos.')),str(path)+': '+str(name))

    def test_v18_static_local_imports_resolve(self):
        for path in (ROOT/'monitor/v18').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('monitor.v18'):
                    self.assertIsNotNone(importlib.util.find_spec(node.module),node.module)

    def test_default_entrypoint_reports_integration_without_opening_q(self):
        result=subprocess.run([sys.executable,'-m','monitor.v18'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=5)
        state=json.loads(result.stdout)
        self.assertEqual(state['version'],18)
        self.assertTrue(state['gui_integrated']);self.assertTrue(state['physical_q_enabled'])
        self.assertFalse(state['firmware_changes'])
