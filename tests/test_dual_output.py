import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from test_spi_native import adc_frame
from transport.unoq_dual import DualDecoder
from transport.unoq_switch import Mode, Phase, switch_request
from transport.unoq_usb import ProtocolError

ROOT = Path(__file__).resolve().parents[1]


def reply(seq, active, boundary, phase=2):
    p = bytearray(512)
    struct.pack_into('<4sHHII', p, 0, b'SCP1', 2, 5, seq, 492)
    struct.pack_into('<IBBBBI', p, 16, 0x80000100, active, active, phase, 0, boundary)
    struct.pack_into('<I', p, 508, zlib.crc32(p[:508]))
    return bytes(p)


def idle(seq):
    p = adc_frame(seq=seq, count=0, index=0, timestamp=0)
    return bytes(p)


class DualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(cls.tmp.name)/'dual.c'
        cls.exe = Path(cls.tmp.name)/'dual'
        source.write_text('#define main verifier_main\n#include "diagnosticos/verificar_spi.c"\n'
                          '#undef main\n#include "transport/dual_protocol.h"\n'
                          'int main(int argc,char **argv) { (void)argv; init_crc(); adc_mode=true; '
                          'uint8_t p[BLOCK]; DualChecker c={0}; '
                          'while(fread(p,1,BLOCK,stdin)==BLOCK) '
                          'if(!(argc>1?dual_command(p):dual_feed(&c,p))) return 2; return 0; }\n')
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT),
                        str(source), '-lm', '-o', str(cls.exe)], check=True)

    def native(self, packets, command=False):
        return subprocess.run([str(self.exe)]+(['command'] if command else []),
                              input=b''.join(packets), capture_output=True).returncode == 0

    def stream(self):
        return [adc_frame(seq=0, index=2047, count=1, timestamp=65504),
                reply(1, Mode.UART, 2048), idle(2),
                reply(3, Mode.SPI, 4096),
                adc_frame(seq=4, index=4096, count=1, timestamp=131072),
                idle(5), adc_frame(seq=6, index=4097, count=1, timestamp=131104)]

    def test_cpp_python_accept_control_and_idle_without_false_sample_gaps(self):
        packets = self.stream()
        self.assertTrue(self.native(packets))
        decoder = DualDecoder()
        samples = []
        data = b''.join(packets)
        for offset in range(0, len(data), 37):
            samples.extend(decoder.feed(data[offset:offset+37]))
        self.assertEqual([s[3] for s in samples], [2047, 4096, 4097])
        self.assertEqual(decoder.mode, Mode.SPI)

    def test_crc_sequence_boundary_and_uart_data_rejected(self):
        variants = []
        packets = self.stream()
        bad = bytearray(packets[2]); bad[-1] ^= 1
        variants.append(packets[:2]+[bytes(bad)])
        variants.append([packets[0], idle(2)])
        variants.append(packets[:4]+[adc_frame(seq=4, index=4097, count=1, timestamp=131104)])
        variants.append(packets[:2]+[adc_frame(seq=2, index=2048, count=1, timestamp=65536)])
        variants.append([adc_frame(seq=0, index=0, count=1, timestamp=0),
                         idle(1), adc_frame(seq=2, index=2, count=1, timestamp=64)])
        for frames in variants:
            self.assertFalse(self.native(frames))
            with self.assertRaises(ProtocolError):
                DualDecoder().feed(b''.join(frames))

    def test_relay_accepts_switch_but_rejects_reserved_bytes(self):
        good = switch_request(0x80000100, Mode.UART)
        self.assertTrue(self.native([good], command=True))
        bad = bytearray(good); bad[17] = 1
        struct.pack_into('<I', bad, 508, zlib.crc32(bad[:508]))
        self.assertFalse(self.native([bytes(bad)], command=True))

class SessionTests(unittest.TestCase):
    def test_accepted_does_not_confirm_and_query_works_without_samples(self):
        from transport.unoq_dual import DualSession
        class MCU:
            def __init__(self):
                self.socket = self
                self.pending = []
                self.sequence = 0
            def sendall(self, request):
                rid = struct.unpack_from('<I', request, 8)[0]
                if request[6] == 4:
                    for phase, boundary in ((1, 0), (2, 2048)):
                        p = bytearray(reply(self.sequence, 1, boundary, phase))
                        struct.pack_into('<I', p, 16, rid)
                        if phase == 1: p[21] = 0
                        struct.pack_into('<I', p, 508, zlib.crc32(p[:508]))
                        self.pending.append(bytes(p)); self.sequence += 1
                else:
                    p = bytearray(idle(self.sequence))
                    struct.pack_into('<I', p, 16, rid)
                    struct.pack_into('<I', p, 508, zlib.crc32(p[:508]))
                    self.pending.append(bytes(p)); self.sequence += 1
            def read(self):
                return self.pending.pop(0) if self.pending else b''
        session = DualSession(MCU())
        result = session.select(Mode.UART)
        self.assertEqual(result.phase, Phase.APPLIED)
        self.assertEqual(result.boundary, 2048)
        self.assertEqual(session.decoder.mode, Mode.UART)
        self.assertEqual(session.query()['rate'], 31250)
        self.assertEqual(session.decoder.adc.pairs, 0)
