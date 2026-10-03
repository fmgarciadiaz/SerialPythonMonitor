"""Interop real C++/Python y detección de fallos del benchmark SPI, sin placa."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

from diagnosticos.verificar_spi import Checker, HEADER, STATUS, VERSION, PAYLOAD_BYTES, pattern, ping

ROOT = Path(__file__).resolve().parents[1]


def data_frame(seq, ack=0xffffffff, errors=0, bad_ping=0, shorts=0, result=512):
    data = (HEADER.pack(b'SCP1', VERSION, 1, seq, PAYLOAD_BYTES) +
            STATUS.pack(ack, errors, bad_ping, shorts, result, 0, 0, 0) + pattern(seq)[STATUS.size:])
    return data + struct.pack('<I', zlib.crc32(data))


class SPIProtocolTests(unittest.TestCase):
    def test_irq_ready_keeps_the_baseline_wire_protocol(self):
        self.assertEqual((ROOT/'arduino/historico/v6/spi_benchmark/sketch/benchmark_protocol.h').read_bytes(),
                         (ROOT/'arduino/historico/v6_irq/spi_benchmark/sketch/benchmark_protocol.h').read_bytes())

    def test_dma_uses_identical_protocol_to_interrupt_baseline(self):
        self.assertEqual((ROOT/'arduino/historico/v6/spi_benchmark/sketch/benchmark_protocol.h').read_bytes(),
                         (ROOT/'arduino/historico/v6_dma/spi_benchmark/sketch/benchmark_protocol.h').read_bytes())

    def test_polling_uses_identical_protocol_to_interrupt_baseline(self):
        self.assertEqual((ROOT/'arduino/historico/v6/spi_benchmark/sketch/benchmark_protocol.h').read_bytes(),
                         (ROOT/'arduino/historico/v6_polling/spi_benchmark/sketch/benchmark_protocol.h').read_bytes())

    def test_optimized_pattern_matches_wire_definition(self):
        for seq in (0, 1, 2, 31, 255, 256, 65535, 65536, 0x12345678, 0xfffffffe, 0xffffffff):
            seed = seq * 0x9e3779b1 & 0xffffffff
            expected = bytes(((seed >> (8 * (i & 3))) ^ (i * 17 + 0x5a)) & 255
                             for i in range(PAYLOAD_BYTES))
            self.assertEqual(pattern(seq), expected)

    def test_cpp_python_interoperate_and_reject_corrupt_commands(self):
        program = r'''
#include <cassert>
#include <cstdio>
#include "benchmark_protocol.h"
using namespace scope_bench;
int main() {
    assert(crc32(reinterpret_cast<const uint8_t *>("123456789"), 9)==0xCBF43926U);
    uint8_t packet[BLOCK_BYTES];
    assert(fread(packet, 1, BLOCK_BYTES, stdin)==BLOCK_BYTES);
    assert(valid_ping(packet));
    assert(get32(packet+8)==0xFEDCBA98U);
    packet[17] ^= 1;
    assert(!valid_ping(packet));
    seal(packet); // CRC correcto no debe ocultar un payload incorrecto.
    assert(!valid_ping(packet));
    data_frame(packet, 0x87654321U, 0xFEDCBA98U, 2, 3, 4, -5);
    assert(fwrite(packet, 1, BLOCK_BYTES, stdout)==BLOCK_BYTES);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp, exe = Path(folder)/'protocol.cpp', Path(folder)/'protocol'
            cpp.write_text(program)
            subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-I',
                            str(ROOT/'arduino/historico/v6/spi_benchmark/sketch'), str(cpp), '-o', str(exe)], check=True)
            output = subprocess.run([str(exe)], input=ping(0xfedcba98), capture_output=True, check=True).stdout
        self.assertEqual(output, data_frame(0x87654321, 0xfedcba98, 2, 3, 4, -5))

    def test_continuity_wrap_and_delayed_ack(self):
        c = Checker()
        for seq, ack in ((0xfffffffe, 40), (0xffffffff, 41), (0, 42), (1, 43)):
            c.feed(data_frame(seq, ack), ack)
        self.assertTrue(c.report(1)['integrity_pass'])
        self.assertEqual(c.valid_blocks, 4)

    def test_missing_duplicate_and_out_of_order(self):
        c = Checker()
        for seq in (8, 10, 10, 9, 11):
            c.feed(data_frame(seq))
        self.assertEqual((c.missing_blocks, c.duplicates, c.out_of_order), (1, 1, 1))
        self.assertFalse(c.report(1)['integrity_pass'])

    def test_bad_header_crc_payload_and_truncation(self):
        original = data_frame(3)
        c = Checker()
        c.feed(original[:-1])
        bad = bytearray(original); bad[0] ^= 1
        c.feed(bad)
        bad = bytearray(original); bad[100] ^= 1
        c.feed(bad)
        bad[-4:] = struct.pack('<I', zlib.crc32(bad[:-4]))
        c.feed(bad)
        self.assertEqual((c.bad_headers, c.crc_errors, c.bad_payloads), (2, 2, 1))
        self.assertFalse(c.report(1)['integrity_pass'])

    def test_mcu_counters_and_wrong_ack_fail_report(self):
        c = Checker()
        c.feed(data_frame(20, 1, 4, 5, 6))
        c.feed(data_frame(21, 2, 5, 7, 9), expected_ack=3)
        self.assertEqual((c.mcu_spi_errors, c.mcu_bad_commands, c.mcu_short_transfers, c.ack_errors),
                         (1, 2, 3, 1))
        self.assertFalse(c.report(1)['integrity_pass'])

    def test_counter_reset_and_no_data_fail(self):
        c = Checker()
        self.assertFalse(c.report(1)['integrity_pass'])
        c.feed(data_frame(1, errors=100))
        c.feed(data_frame(2, errors=0))
        self.assertEqual(c.counter_resets, 1)
        self.assertFalse(c.report(1)['integrity_pass'])
