"""Exercise optimized sample loops at tails, wraps and corruption positions."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SKETCH = Path(__file__).resolve().parent/'arduino/historico/v16/oscilloscope/sketch'

class ValidationTests(unittest.TestCase):
    def test_single_validation_and_adc8_packing(self):
        source = f'''#include "{SKETCH/'node_validation.h'}"
#include "{SKETCH/'sample_packing.h'}"
#include <vector>
#include <cassert>
struct Sample {{uint16_t ch1;}};
int main() {{
 for (unsigned count: {{1U,3U,4U,7U,8U,9U,257U,416U,864U,8192U}}) {{
  std::vector<uint16_t> adc(count);
  std::vector<uint32_t> ts(count);
  std::vector<Sample> out(count);
  std::vector<uint8_t> bytes(count+8,0xaa);
  const uint32_t first=0xfffffff0U,period=114;
  for(unsigned i=0;i<count;++i) {{adc[i]=i&255;ts[i]=first+i*period;}}
  auto check=[&]() {{return scope_validation::validate_node<true,true>(adc.data(),ts.data(),count,8,period,true,first-period,out.data());}};
  assert(check());
  for(unsigned i=0;i<count;++i)assert(out[i].ch1==adc[i]);
  assert(maxfreq_packing::pack(bytes.data(),out.data(),count,8)==count);
  for(unsigned i=0;i<count;++i)assert(bytes[i]==adc[i]);
  for(unsigned i=count;i<count+8;++i)assert(bytes[i]==0xaa);
  for(unsigned i=0;i<count;++i) {{
   ts[i]^=1;assert(!check());ts[i]^=1;
   auto saved=adc[i];adc[i]=256;assert(!check());adc[i]=saved;
  }}
  assert(check());out[0].ch1=12345;
  assert((scope_validation::validate_node<false,true>(adc.data(),ts.data(),count,8,period,true,first-period,out.data())));
  assert(out[0].ch1==12345);
 }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'validation.cpp';src.write_text(source)
            exe=src.with_suffix('')
            subprocess.run(['c++','-O3','-std=c++17',str(src),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True)

if __name__=='__main__': unittest.main()
