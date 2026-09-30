"""Temporización real V5 y compatibilidad con timestamps de 32 us."""
import ast
from collections import deque
from pathlib import Path
import struct
import re
import subprocess
import tempfile
import time
from types import SimpleNamespace
from typing import Tuple
import unittest

from diagnosticos.verificar_enlace import Checker

ROOT = Path(__file__).resolve().parents[1]


def timestamp(i):
    return i * 32


def packet(first):
    return b'DATA\x01\x00\x02' + b''.join(
        struct.pack('<IHH', (0xfffff000 + timestamp(i)) & 0xffffffff, i % 16384, 1234)
        for i in range(first, first + 512))


class ThirtyOneKhzTests(unittest.TestCase):
    def test_polling_transmitter_keeps_wire_packet(self):
        sketch = ROOT / 'arduino/v5/oscilloscope/sketch'
        source = (sketch / 'sketch.ino').read_text()
        transport = source[source.index('static Packet tx ='):source.index('// Validar el destino')]
        program = '''#include <cstdint>
#include <cassert>
#include <vector>
constexpr uint16_t SERIAL_BLOCK_PAIRS = 512;
#include "scope_protocol.h"
struct device {};
device mock_uart;
#define DEVICE_DT_GET(...) (&mock_uart)
std::vector<uint8_t> sent;
void uart_poll_out(const device *dev, unsigned char byte) {
    assert(dev == &mock_uart);
    sent.push_back(byte);
}
''' + transport + '''
int main() {
    std::vector<uint8_t> expected = {'D','A','T','A',1,0,2};
    for (uint32_t i = 0; i < 512; ++i) {
        const uint32_t ts = 0xfffff000U + i * 32U;
        tx.samples[i] = {ts, static_cast<uint16_t>(i), static_cast<uint16_t>(16383-i)};
        for (unsigned j=0; j<32; j+=8) expected.push_back(ts >> j);
        expected.push_back(i); expected.push_back(i >> 8);
        expected.push_back(16383-i); expected.push_back((16383-i) >> 8);
    }
    write_packet();
    assert(sent == expected);
    write_packet();
    const auto second = expected;
    expected.insert(expected.end(), second.begin(), second.end());
    assert(sent == expected);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp, exe = Path(folder) / 'tx.cpp', Path(folder) / 'tx'
            cpp.write_text(program)
            subprocess.run(['c++', '-std=c++11', '-Wall', '-Werror', '-I', str(sketch),
                            str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

    def test_timer_configuration_and_transport_budget(self):
        config = (ROOT / 'arduino/v5/oscilloscope/sketch/scope_config.h').read_text()
        config = '\n'.join(line for line in config.splitlines()
                           if not line.startswith(('#include', '#pragma')))
        source = '''#include <cstdint>
#define CONFIG_SOC_STM32U585XX 1
#define CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC 160000000U
#define CONFIG_DCACHE_LINE_SIZE 32
constexpr int A0=0, A1=1, A2=2;
''' + config + '''
static_assert(TIM2_PRESCALER == 159 && TIM2_AUTORELOAD == 31, "31.25 kHz timer");
static_assert(TIM5_PRESCALER == 159, "Microsecond protocol unchanged");
static_assert(SERIAL_BAUD == 3000000, "3 Mbps transport");
static_assert(SAMPLE_RATE_HZ == 31250 && SAMPLE_PERIOD_US == 32, "Rate");
static_assert(SERIAL_REQUIRED_BPS > 2504000 && SERIAL_REQUIRED_BPS < 2505000, "Budget");
int main() {}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder) / 'timing.cpp'
            cpp.write_text(source)
            subprocess.run(['c++', '-std=c++11', '-Wall', '-Werror', '-Wno-unused-const-variable', '-fsyntax-only', str(cpp)], check=True)

    def test_bridge_and_monitor_use_same_baud(self):
        bridge = (ROOT / 'arduino/v5/r4_bridge_v5/r4_bridge_v5.ino').read_text()
        baud = int(re.search(r'LINK_BAUD = (\d+)', bridge).group(1))
        tree = ast.parse((ROOT / 'monitor/v7/app.py').read_text())
        monitor_baud = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == 'BAUD_DEFAULT' for t in n.targets))
        self.assertEqual(baud, 3000000)
        self.assertEqual(monitor_baud, baud)

    def test_wrap_and_fragmentation_are_not_losses(self):
        checker = Checker(31250)
        data = packet(0) + packet(512)
        for start in range(0, len(data), 37):
            checker.feed(data[start:start+37])
        self.assertEqual((checker.samples, checker.bad_dt, checker.lost_sync, checker.bad_adc),
                         (1024, 0, 0, 0))

    def test_missing_sample_is_detected_at_32us(self):
        checker = Checker(31250)
        checker.feed(packet(0) + packet(513))
        self.assertEqual(checker.bad_dt, 1)

    def test_monitor_reports_31250hz_from_timestamps(self):
        tree = ast.parse((ROOT / 'monitor/v7/app.py').read_text())
        window = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SerialMonitorWindow')
        method = next(n for n in window.body if isinstance(n, ast.FunctionDef) and n.name == '_calculate_sample_rate')
        ns = {'Tuple': Tuple, 'time': time}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<sample-rate>', 'exec'), ns)
        state = SimpleNamespace(series={'Tiempo (us)': deque(timestamp(i) for i in range(1000))})
        fs, dt, label = ns['_calculate_sample_rate'](state)
        self.assertAlmostEqual(fs, 31250, delta=.001)
        self.assertAlmostEqual(dt, 32, delta=.001)
        self.assertEqual(label, '31.25 kS/s')
