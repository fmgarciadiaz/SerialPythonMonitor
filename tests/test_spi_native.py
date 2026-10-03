"""Compara el verificador C real con Python usando las mismas tramas corruptas."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

from diagnosticos.verificar_spi import Checker, HEADER, STATUS, VERSION, PAYLOAD_BYTES, pattern, ping

ROOT = Path(__file__).resolve().parents[1]


def frame(seq, ack=0xffffffff, errors=0, last_error=0, prep=0, check=0):
    data = (HEADER.pack(b'SCP1', VERSION, 1, seq, PAYLOAD_BYTES)
            + STATUS.pack(ack, errors, 0, 0, 512, last_error, prep, check)
            + pattern(seq)[STATUS.size:])
    return data + struct.pack('<I', zlib.crc32(data))


class NativeSPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.exe = Path(cls.tmp.name) / 'verificar_spi'
        source = ROOT / 'diagnosticos/verificar_spi.c'
        subprocess.run(['cc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(source), '-lm', '-o', str(cls.exe)], check=True)
        harness = Path(cls.tmp.name) / 'ping.c'
        harness.write_text('#define main verifier_main\n#include "verificar_spi.c"\n'
                           '#undef main\nint main(void) { uint8_t p[BLOCK]; init_crc(); '
                           'ping(p,0xfedcba98); return fwrite(p,1,BLOCK,stdout)==BLOCK?0:1; }\n')
        cls.ping_exe = Path(cls.tmp.name) / 'ping'
        subprocess.run(['cc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-I', str(source.parent), str(harness), '-lm', '-o', str(cls.ping_exe)], check=True)

    def compare(self, packets):
        checker = Checker()
        for i, packet in enumerate(packets):
            checker.feed(packet, i-1 if i else None)
        expected = checker.report(1)
        result = subprocess.run([str(self.exe), '--replay'], input=b''.join(packets), capture_output=True)
        actual = json.loads(result.stdout)
        keys = ('transfers', 'valid_blocks', 'bad_headers', 'bad_payloads', 'crc_errors',
                'missing_blocks', 'duplicates', 'out_of_order', 'ack_errors', 'counter_resets',
                'mcu_spi_errors', 'mcu_bad_commands', 'mcu_short_transfers', 'last_driver_result',
                'last_driver_error', 'mcu_prepare_us_mean', 'mcu_check_us_mean',
                'mcu_prepare_us_max', 'mcu_check_us_max', 'previous', 'integrity_pass')
        for key in keys:
            self.assertEqual(actual[key], expected[key], key)
        self.assertEqual(result.returncode, 0 if expected['integrity_pass'] else 1)
        return actual

    def test_native_ping_matches_python(self):
        result = subprocess.run([str(self.ping_exe)], capture_output=True, check=True)
        self.assertEqual(result.stdout, ping(0xfedcba98))

    def test_continuity_wrap_and_mcu_timings(self):
        result = self.compare([frame(0xffffffff, prep=17, check=9),
                               frame(0, 0, prep=23, check=11), frame(1, 1, prep=20, check=10)])
        self.assertEqual(result['mcu_prepare_us_mean'], 20)
        self.assertEqual(result['mcu_check_us_mean'], 10)

    def test_missing_duplicate_and_reverse(self):
        self.compare([frame(seq, i-1 if i else 0xffffffff)
                      for i, seq in enumerate((8, 10, 10, 9, 11))])

    def test_corrupt_header_crc_payload_and_partial(self):
        bad_header = bytearray(frame(2, 0)); bad_header[0] ^= 1
        bad_crc = bytearray(frame(3, 1)); bad_crc[100] ^= 1
        bad_pattern = bytearray(bad_crc)
        bad_pattern[-4:] = struct.pack('<I', zlib.crc32(bad_pattern[:-4]))
        self.compare([frame(1), bytes(bad_header), bytes(bad_crc), bytes(bad_pattern), frame(5)[:-1]])

    def test_ack_errors_driver_error_and_reset(self):
        result = self.compare([frame(1, errors=3), frame(2, 22, errors=4, last_error=-5),
                               frame(3, 1, errors=0, last_error=-5)])
        self.assertEqual(result['last_driver_error'], -5)

    def test_empty_fails(self):
        self.compare([])

    def test_replay_reports_ready_disabled(self):
        result = self.compare([frame(1)])
        self.assertFalse(result['ready_enabled'])
        self.assertEqual(result['ready_wait_s'], 0)

    def test_ready_cannot_be_combined_with_replay_or_invalid_line(self):
        for args in (['--ready-chip', '/dev/gpiochip1', '--gap-us', '0'],
                     ['--ready-line', '-1'], ['--ready-line', '1.5']):
            result = subprocess.run([str(self.exe), '--replay', *args], input=b'', capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_invalid_options_fail(self):
        for args in (['--seconds', 'nan'], ['--hz', '-1'], ['--gap-us', '-1']):
            result = subprocess.run([str(self.exe), '--replay', *args], input=b'', capture_output=True)
            self.assertEqual(result.returncode, 2)


def adc_frame(seq=0, index=0, count=53, timestamp=0xfffffff0, dropped=0, fatal=0):
    data = bytearray(512)
    HEADER.pack_into(data, 0, b'SCP1', VERSION, 3, seq, PAYLOAD_BYTES)
    STATUS.pack_into(data, 16, seq-1 if seq else 0xffffffff, 0, 0, 0, 512, 0, 0, 0)
    struct.pack_into('<IIIIHBBIII', data, 48, 31250, index, dropped, fatal,
                     count, 14, 2, 32, index//2048, bool(fatal))
    for i in range(count):
        struct.pack_into('<IHH', data, 80+i*8, (timestamp+i*32)&0xffffffff, i, 16383-i)
    data[-4:] = struct.pack('<I', zlib.crc32(data[:-4]))
    return data


class NativeADCSPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.exe = Path(cls.tmp.name)/'checker'
        subprocess.run(['cc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(ROOT/'diagnosticos/verificar_spi.c'), '-lm', '-o', str(cls.exe)], check=True)

    def check(self, packets, valid=True):
        result = subprocess.run([str(self.exe), '--adc', '--replay'],
                                input=b''.join(packets), capture_output=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['integrity_pass'], valid, report)
        self.assertEqual(result.returncode, 0 if valid else 1)
        return report

    def test_timestamps_wrap_and_node_boundary(self):
        a=adc_frame(index=2014, count=34)
        b=adc_frame(seq=1, index=2048, timestamp=(0xfffffff0+34*32)&0xffffffff)
        report=self.check([a,b])
        self.assertEqual(report['sample_pairs'], 87)
        self.assertEqual(report['verified_pattern_bytes'], 0)

    def test_sample_index_wrap_with_monotonic_node_index(self):
        a=adc_frame(index=0xffffffff,count=1)
        b=adc_frame(seq=1,index=0,count=1,timestamp=16)
        struct.pack_into('<I',b,72,0x200000)
        b[-4:]=struct.pack('<I',zlib.crc32(b[:-4]))
        self.check([a,b])

    def test_sample_gap_is_explicit(self):
        a=adc_frame(count=1)
        b=adc_frame(seq=1,index=2048,count=1,timestamp=(0xfffffff0+2048*32)&0xffffffff,dropped=1)
        report=self.check([a,b],False)
        self.assertEqual(report['sample_gaps'],2047)
        self.assertEqual(report['timestamp_errors'],0)
        self.assertEqual(report['dropped_nodes'],1)

    def test_bad_timestamp_or_adc_range(self):
        for offset,value,key in ((88,123,'timestamp_errors'),(84,16384,'adc_errors')):
            frame=adc_frame()
            struct.pack_into('<I' if offset==88 else '<H',frame,offset,value)
            frame[-4:]=struct.pack('<I',zlib.crc32(frame[:-4]))
            self.assertGreater(self.check([frame],False)[key],0)

    def test_fatal_heartbeat_fails(self):
        self.check([adc_frame(count=0,fatal=1)],False)

    def test_metadata_padding_crc_and_empty_rejected(self):
        self.check([],False)
        for offset,value in ((48,1),(64,54),(66,12),(67,1),(68,33),(72,1),(76,2),(507,1)):
            frame=adc_frame(); frame[offset]=value
            frame[-4:]=struct.pack('<I',zlib.crc32(frame[:-4]))
            self.assertGreater(self.check([frame],False)['bad_payloads'],0)
        frame=adc_frame(); frame[100]^=1
        self.assertEqual(self.check([frame],False)['crc_errors'],1)
