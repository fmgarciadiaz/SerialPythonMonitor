"""Compare the actual split CRC with independent zlib, including every changed bit."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest
import zlib

SKETCH=Path(__file__).resolve().parent/'arduino/historico/v16/oscilloscope/sketch'
class SplitCrcTests(unittest.TestCase):
    def test_all_positions_and_reused_payloads(self):
        source=f'''#include "{SKETCH.parents[3]/'rejected_split_crc/split_crc.h'}"
#include <cstdio>
int main() {{uint8_t frame[988];while(fread(frame,1,988,stdin)==988) {{
 const auto payload=scope_crc_fast::compute(frame+48,940);
 uint32_t result=scope_crc_split::checksum(frame,payload);
 fwrite(&result,4,1,stdout);
}}}}
'''
        rng=random.Random(1400)
        frames=[bytes(988),bytes([255])*988,bytes(rng.randrange(256) for _ in range(988))]
        original=frames[-1]
        for bit in range(988*8):
            changed=bytearray(original);changed[bit//8]^=1<<(bit%8);frames.append(bytes(changed))
        # Vary control/sequence/diagnostic headers without touching a prebuilt payload.
        for _ in range(100):frames.append(bytes(rng.randrange(256) for _ in range(48))+original[48:])
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'crc.cpp';src.write_text(source);exe=src.with_suffix('')
            subprocess.run(['c++','-O2','-std=c++17','-I',str(SKETCH),str(src),'-o',str(exe)],check=True,capture_output=True)
            result=subprocess.run([str(exe)],input=b''.join(frames),capture_output=True,check=True).stdout
        self.assertEqual(len(result),len(frames)*4)
        for frame,(crc,) in zip(frames,struct.iter_unpack('<I',result)):
            self.assertEqual(crc,zlib.crc32(frame))
if __name__=='__main__':unittest.main()
