"""Prueba el paquete real del firmware y las escrituras parciales, sin placa."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKETCH = ROOT / 'arduino/v4/oscilloscope/sketch'


class ProtocolTests(unittest.TestCase):
    def test_wire_compatibility_and_partial_writes(self):
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler, 'Se necesita un compilador C++ para esta prueba')
        config = (SKETCH / 'scope_config.h').read_text()
        count = re.search(r'SERIAL_BLOCK_PAIRS = (\d+)U', config).group(1)
        source = (SKETCH / 'sketch.ino').read_text()
        begin = source.index('static Packet tx =')
        end = source.index('// Validar el destino', begin)
        transport = source[begin:end]
        program = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <vector>
constexpr uint16_t SERIAL_BLOCK_PAIRS = COUNT;
#include "scope_protocol.h"
int sleeps = 0;
#define K_MSEC(n) (n)
void k_sleep(int) { ++sleeps; }
struct SerialMock {
    std::vector<uint8_t> bytes;
    unsigned calls = 0;
    size_t limit = 13;
    size_t write(const uint8_t *p, size_t n) {
        ++calls;
        if (limit == 13 && calls % 3 == 0) return 0;
        n = std::min(n, limit);
        bytes.insert(bytes.end(), p, p + n);
        return n;
    }
} Serial1;
TRANSPORT
int main() {
    std::vector<uint8_t> expected = {'D', 'A', 'T', 'A', 1,
        static_cast<uint8_t>(SERIAL_BLOCK_PAIRS & 255),
        static_cast<uint8_t>(SERIAL_BLOCK_PAIRS >> 8)};
    for (uint32_t i = 0; i < SERIAL_BLOCK_PAIRS; ++i) {
        const uint32_t timestamp = 0xffff0000U + i * 100U;
        tx.samples[i] = {timestamp, static_cast<uint16_t>(i), static_cast<uint16_t>(16383 - i)};
        for (unsigned shift = 0; shift < 32; shift += 8) expected.push_back(timestamp >> shift);
        expected.push_back(i); expected.push_back(i >> 8);
        expected.push_back(16383-i); expected.push_back((16383-i) >> 8);
    }
    write_packet();
    assert(Serial1.bytes == expected);
    assert(sleeps > 0);
    Serial1.bytes.clear(); Serial1.calls = 0; Serial1.limit = sizeof(Packet);
    write_packet();
    assert(Serial1.bytes == expected);
    assert(Serial1.calls == 1);
}
'''.replace('COUNT', count).replace('TRANSPORT', transport)
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'protocol.cpp'
            exe = Path(directory) / 'protocol'
            cpp.write_text(program)
            subprocess.run([compiler, '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-I', str(SKETCH), str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
