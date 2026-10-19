"""Compare optimized relay decisions against the previous strict checker."""
import random
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from experimentos.maxfreq_v16.test_contract import packet
from experimentos.maxfreq_v16.contract import seal

ROOT = Path(__file__).resolve().parents[2]


class RelayTests(unittest.TestCase):
    def test_valid_corrupt_and_wrapped_frames_match_previous_checker(self):
        rng = random.Random(1400)
        with tempfile.TemporaryDirectory() as folder:
            programs = []
            for name in ('maxfreq_v16', 'send1400_v16'):
                relay = ROOT/'experimentos'/name/'arduino/v16/relay'
                source = f'''#define main old_main
#include "{relay/'base_verifier.c'}"
#undef main
#include "{relay/'config_relay_protocol.h'}"
int main(void) {{ uint8_t p[BLOCK]; init_crc();
while(fread(p,1,BLOCK,stdin)==BLOCK) {{
DualChecker d={{.bits=8,.period=(6912U<<16)|114U}};
d.adc.have_sample=true; d.adc.previous_sample=get32(p+52)-1;
d.adc.previous_timestamp=get32(p+80)-114U;
printf("%d\\n",dual_feed(&d,p)); }} return 0; }}'''
                cpp = Path(folder)/(name+'.c');cpp.write_text(source)
                binary = cpp.with_suffix('')
                subprocess.run(['cc','-O2','-std=c11',str(cpp),'-lm','-o',str(binary)],check=True,capture_output=True)
                programs.append(binary)
            frames = []
            for node in (0, 1, (1<<32)//6912, (1<<32)-1):
                for count in (4, 16, 864):
                    base = packet(8,114,6912,node*6912,node,0,
                                  [rng.randrange(256) for _ in range(count)],0xfffffff0)
                    frames.append(base)
                    for offset in (4,6,12,20,24,28,32,36,56,60,64,66,67,68,76,84,88,92,987):
                        bad = bytearray(base);bad[offset] ^= 255
                        frames.append(seal(bad))
                    bad=bytearray(base);bad[120]^=1;frames.append(bytes(bad))
            data = b''.join(frames)
            results = [subprocess.run([str(p)],input=data,capture_output=True,check=True).stdout for p in programs]
            self.assertEqual(results[0],results[1])
            self.assertIn(b'1\n',results[1]);self.assertIn(b'0\n',results[1])


if __name__ == '__main__':
    unittest.main()
