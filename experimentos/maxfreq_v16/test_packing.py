import random
import subprocess
import tempfile
import unittest
from pathlib import Path

class PackingTests(unittest.TestCase):
    def test_cpp_matches_independent_bitstream(self):
        header = Path(__file__).resolve().parent / 'arduino/historico/v16/oscilloscope/sketch/sample_packing.h'
        source = '#include <cstdio>\n#include "' + str(header) + '"\nstruct Sample { uint16_t ch1; };\nint main(){unsigned bits,n; while(scanf("%u %u",&bits,&n)==2){Sample s[864]; uint8_t out[872]; for(unsigned i=0;i<n;i++) scanf("%hu",&s[i].ch1); unsigned used=maxfreq_packing::pack(out,s,n,bits); fwrite(out,1,used,stdout);}}\n'
        rng = random.Random(113)
        commands, expected = [], bytearray()
        for bits, capacity in ((8,864),(10,696),(14,496)):
            for count in (4,16,capacity):
                for values in ([0]*count,[(1<<bits)-1]*count,[rng.randrange(1<<bits) for _ in range(count)]):
                    commands.append(f'{bits} {count} ' + ' '.join(map(str,values)))
                    packed = sum(value << (i*bits) for i,value in enumerate(values))
                    expected.extend(packed.to_bytes(count*bits//8,'little'))
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder)/'packing.cpp'; cpp.write_text(source)
            binary = Path(folder)/'packing'
            subprocess.run(['c++','-O2','-std=c++11',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            result = subprocess.run([str(binary)],input=('\n'.join(commands)+'\n').encode(),capture_output=True,check=True)
        self.assertEqual(result.stdout,bytes(expected))
