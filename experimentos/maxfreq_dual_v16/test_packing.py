import random
import subprocess
import tempfile
import unittest
from pathlib import Path

class PackingTests(unittest.TestCase):
    def test_cpp_matches_independent_bitstream(self):
        header = Path(__file__).resolve().parent / 'arduino/v16/oscilloscope/sketch/sample_packing.h'
        source = '#include <cstdio>\n#include "' + str(header) + '"\nstruct Sample { uint16_t ch1,ch2; };\nint main(){unsigned bits,n; while(scanf("%u %u",&bits,&n)==2){Sample s[864]; uint8_t out[872]; for(unsigned i=0;i<n;i++) scanf("%hu %hu",&s[i].ch1,&s[i].ch2); unsigned used=maxfreq_packing::pack(out,s,n,bits); fwrite(out,1,used,stdout);}}\n'
        rng = random.Random(113)
        commands, expected = [], bytearray()
        for bits, capacity in ((8,432),(10,348),(12,288),(14,248),(16,216)):
            for count in (4,16,capacity):
                for values in ([0]*(count*2),[(1<<bits)-1]*(count*2),[rng.randrange(1<<bits) for _ in range(count*2)]):
                    commands.append(f'{bits} {count} ' + ' '.join(map(str,values)))
                    packed = sum(value << (i*bits) for i,value in enumerate(values))
                    expected.extend(packed.to_bytes(count*bits*2//8,'little'))
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder)/'packing.cpp'; cpp.write_text(source)
            binary = Path(folder)/'packing'
            subprocess.run(['c++','-O2','-std=c++11',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            result = subprocess.run([str(binary)],input=('\n'.join(commands)+'\n').encode(),capture_output=True,check=True)
        self.assertEqual(result.stdout,bytes(expected))
