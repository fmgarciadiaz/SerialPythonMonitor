"""Host C++ differential verification of the independent P512 experiment."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'experimentos/tasas_spi/opt125/p512'
class P512Tests(unittest.TestCase):
    def test_differential_cpp(self):
        compiler=shutil.which('c++') or shutil.which('g++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'differential'
            subprocess.run([compiler,'-std=c++17','-O0','-Wall','-Wextra','-Werror',str(BASE/'tests/differential.cpp'),'-o',str(exe)],check=True)
            result=subprocess.run([str(exe)],check=True,text=True,capture_output=True)
            self.assertIn('10240 differential cases passed',result.stdout)
    def test_identity_and_isolation(self):
        import json
        cfg=json.loads((BASE/'unoq.json').read_text())
        self.assertEqual(cfg['tcp_port'],8766)
        self.assertEqual(cfg['name'],'Scope Opt125 P512')
        for file in (BASE/'receiver').glob('*.py'):
            self.assertNotIn('from experimentos.tasas_spi.receiver.',file.read_text())
if __name__=='__main__': unittest.main()
