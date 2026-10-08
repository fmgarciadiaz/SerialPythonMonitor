import ast,struct,subprocess,tempfile,unittest
from pathlib import Path
from monitor.v13.receiver.unoq_generator import GeneratorConfig
ROOT=Path(__file__).resolve().parents[2]
class PulseUsTests(unittest.TestCase):
 def test_protocol_limits_and_units(self):
  c=GeneratorConfig(wave=4,duration=100,duration_us=1)
  self.assertEqual(c.pack()[3],1)
  self.assertEqual(struct.unpack_from('<I',c.pack(),16)[0],100)
  for width in (99,65536):
   with self.assertRaises(ValueError):GeneratorConfig(wave=4,duration=width,duration_us=1)
  with self.assertRaises(ValueError):GeneratorConfig(wave=1,duration=100,duration_us=1)
 def test_real_generator_uses_hardware_completion(self):
  tree=ast.parse((ROOT/'tests/test_generator.py').read_text())
  stub=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STUB' for t in n.targets))
  before,after=stub.split('#include "generator.h"')
  code=before+'''namespace generator_hw {
static bool done=false;static unsigned width=0;
static bool pulse(unsigned high,unsigned,unsigned us){width=us;regs.DHR12R1=high;done=false;return true;}
static bool pulse_finished(){return done;}
}
#include "generator.h"
#include <cassert>
int main(){(void)&generator::submit;assert(generator::start());
auto c=scope_gen::defaults();c.wave=4;c.duration_us=1;c.duration=100;
assert(scope_gen::valid(c));assert(generator::apply(c));assert(generator_hw::width==100);
now=100000;generator::tick(nullptr);assert(generator::running);
generator_hw::done=true;generator::tick(nullptr);assert(!generator::running);
assert(regs.DHR12R1==c.low);
c.wave=1;c.duration_us=0;c.duration=1000;assert(generator::apply(c));assert(generator::running);
}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'pulse.cpp';p.write_text(code);exe=Path(folder)/'pulse'
   subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v13_pulse/oscilloscope/sketch'),str(p),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
