"""The dual transport exception must never enable CH1-only validation."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class DualTransportTests(unittest.TestCase):
 def test_transport_scope_is_exact_and_independent_of_validation(self):
  with tempfile.TemporaryDirectory() as folder:
   src=Path(folder)/'policy.c';exe=src.with_suffix('')
   src.write_text(f'''#include "{ROOT/'arduino/v17/relay/transport_policy.h'}"
int main(void) {{
 if(!scope_fast_transport(10,2,308,4176) || scope_high_rate(10,2,308,4176))return 1;
 if(!scope_fast_transport(8,1,114,3456))return 2;
 for(unsigned bits=8;bits<=16;bits+=2)
  for(unsigned channels=1;channels<=2;channels++)
   for(unsigned ticks=307;ticks<=309;ticks++)
    for(unsigned pairs=4175;pairs<=4177;pairs++)
     if(scope_fast_transport(bits,channels,ticks,pairs)!=(bits==10 && channels==2 && ticks==308 && pairs==4176))return 3;
 return 0;
}}''')
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
