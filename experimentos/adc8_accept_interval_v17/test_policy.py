from pathlib import Path
import subprocess
import tempfile
import unittest


class AcceptPolicyTests(unittest.TestCase):
    def test_active_idle_and_counter_wrap(self):
        folder=Path(__file__).resolve().parent/'arduino/v16/relay'
        code='''#include <assert.h>
#include "accept_policy.h"
int main(void) {
 unsigned count=0;
 for(uint32_t i=0;i<1024;i++) {
  assert(accept_due(0,i,1));
  assert(accept_due(-1,i,1));assert(accept_due(-1,i,16));
  assert(accept_due(7,i,16)==(i%16==0));
  count+=accept_due(7,i,16);
 }
 assert(count==64);
 for(uint32_t i=0xfffffff0U;;i++) {
  assert(accept_due(7,i,16)==(i%16==0));
  if(i==15)break;
 }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'check.c';source.write_text(code)
            binary=Path(directory)/'check'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(folder),str(source),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
