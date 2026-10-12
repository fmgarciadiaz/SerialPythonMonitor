import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.v16.test_ch1_fast import extract

ROOT=Path(__file__).resolve().parents[2]


class UartScratchTests(unittest.TestCase):
    def test_actual_builder_preserves_every_data_field_and_wrap(self):
        sketch=ROOT/'arduino/v16/oscilloscope/sketch'
        body=extract(sketch/'sketch.ino','build_uart_samples')
        source=f'''#include "{sketch/'benchmark_protocol.h'}"
#include <cstring>
#include <cstdio>
using namespace scope_bench;
constexpr unsigned SERIAL_BLOCK_PAIRS=512;
namespace acquisition{{struct Pair{{uint16_t ch1,ch2;}};struct Node{{uint32_t index,timestamp;Pair samples[2048];}};unsigned period=32;}}
{body}
int main(){{acquisition::Node node{{0,0xfffffff0U,{{}}}};
for(unsigned i=0;i<2048;++i)node.samples[i]={{uint16_t(i*13%16384),uint16_t(i*29%16384)}};
uint8_t p[4103];build_uart_samples(p,&node,512);fwrite(p,1,sizeof(p),stdout);}}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp=Path(folder)/'uart.cpp';cpp.write_text(source);binary=cpp.with_suffix('')
            subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            output=subprocess.run([str(binary)],check=True,capture_output=True).stdout
        expected=b'DATA'+struct.pack('<BH',1,512)
        expected+=b''.join(struct.pack('<IHH',(0xfffffff0+i*32)&0xffffffff,
                                      i*13%16384,i*29%16384) for i in range(512,1024))
        self.assertEqual(output,expected)
