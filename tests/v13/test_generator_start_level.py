import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class GeneratorStartLevelTests(unittest.TestCase):
    def test_all_modes_start_inside_signal_range_and_off_stays_zero(self):
        tree = ast.parse((ROOT / 'tests/test_generator.py').read_text())
        stub = next(ast.literal_eval(n.value) for n in tree.body
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STUB' for t in n.targets))
        stub = '#include <vector>\nstatic std::vector<unsigned> stops;\n' + stub
        stub = stub.replace('enabled=false;regs.DHR12R1=level;', 'stops.push_back(level);enabled=false;regs.DHR12R1=level;')
        code = stub + '''
#include <cassert>
int main() {
    (void)&generator::submit;assert(generator::start());
    for(unsigned mode=0;mode<3;++mode) for(unsigned wave=0;wave<5;++wave) {
        if(wave==4 && mode) continue;
        auto c=scope_gen::defaults(); c.mode=mode;c.wave=wave;c.enabled=1;c.low=800;c.high=3200;
        stops.clear();assert(generator::apply(c));assert(!stops.empty());
        assert(stops[0]==generator::value(c.wave,0,c.low,c.high));
        for(auto level:stops) assert(level>=c.low && level<=c.high);
        if(mode) {
            now=10000;assert(generator::apply(c));
            now=9999;generator::tick(nullptr);assert(generator::running);
            now=10000+generator::steps;generator::tick(nullptr);assert(!generator::running);
        }
        c.enabled=0;stops.clear();assert(generator::apply(c));assert(stops[0]==0);
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'test.cpp';exe=Path(folder)/'test';source.write_text(code)
            subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v12_audio/oscilloscope/sketch'),str(source),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
