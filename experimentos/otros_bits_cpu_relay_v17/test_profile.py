"""Compile the actual candidate policy and check its exact scope."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class PolicyTests(unittest.TestCase):
 def test_exact_scope(self):
  code='''#include <cassert>
#include "cpu_profile.h"
int main(){
for(unsigned i=0;i<1000;++i){
 assert(bool(scope_cpu_profile(10,1,i,5568))==(i==137));
 assert(bool(scope_cpu_profile(12,1,i,4608))==(i==163));
 assert(bool(scope_cpu_profile(14,1,i,1984))==(i==188));
 assert(!scope_cpu_profile(16,1,i,3456));
 assert(!scope_cpu_profile(10,2,i,5568));
}
assert(scope_cpu_profile(8,1,100,3456));
assert(scope_cpu_profile(8,1,112,3456));
assert(!scope_cpu_profile(10,1,140,2784));
assert(!scope_cpu_profile(12,1,172,4608));
assert(!scope_cpu_profile(14,1,192,1984));
}
'''
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'test.cpp';src.write_text(code);exe=Path(d)/'test'
   subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'relay'),str(src),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
if __name__=='__main__':unittest.main()
