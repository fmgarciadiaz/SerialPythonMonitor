import unittest,tempfile,subprocess,struct,zlib,random
from pathlib import Path
class FastCRCTests(unittest.TestCase):
 def test_reference_random_lengths_and_alignment(self):
  header=Path(__file__).resolve().parents[2]/'arduino/v16/oscilloscope/sketch/crc32_fast.h'
  source=f'''#include "{header}"\n#include <cstdio>\nint main(){{uint32_t n;uint8_t p[8193];while(fread(&n,4,1,stdin)==1){{if(n>8192 || fread(p+1,1,n,stdin)!=n)return 2;uint32_t c=scope_crc_fast::compute(p+1,n);fwrite(&c,4,1,stdout);}}}}'''
  rng=random.Random(333);vectors=[b'',b'123456789',bytes(988),bytes([255])*988]
  vectors+=[rng.randbytes(n) for n in (*range(64),226,972,988,992,1023,2048,4096,8192)]
  with tempfile.TemporaryDirectory() as directory:
   src=Path(directory)/'crc.cpp';src.write_text(source);exe=src.with_suffix('')
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True,capture_output=True)
   output=subprocess.run([str(exe)],input=b''.join(struct.pack('<I',len(v))+v for v in vectors),capture_output=True,check=True).stdout
   self.assertEqual(list(struct.unpack('<'+'I'*len(vectors),output)),[zlib.crc32(v) for v in vectors])
