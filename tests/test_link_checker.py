import struct
import unittest
from diagnosticos.verificar_enlace import Checker


def packet(start):
    return b'DATA\x01\x00\x02' + b''.join(
        struct.pack('<IHH', (start + i * 50) & 0xffffffff, i, 16383-i)
        for i in range(512))


class LinkTests(unittest.TestCase):
    def test_fragmented_stream_and_timestamp_wrap(self):
        checker = Checker()
        data = b'partial' + packet(0xfffff000) + packet(0xfffff000 + 512*50)
        for i in range(0, len(data), 13):
            checker.feed(data[i:i+13])
        self.assertEqual((checker.samples, checker.bad_dt, checker.bad_adc, checker.skipped),
                         (1024, 0, 0, 7))

    def test_missing_packet(self):
        checker = Checker()
        checker.feed(packet(0) + packet(1024*50))
        self.assertEqual(checker.bad_dt, 1)

    def test_wrong_sample_rate(self):
        checker = Checker(10000)
        checker.feed(packet(0))
        self.assertEqual(checker.bad_dt, 511)

    def test_garbage_between_valid_packets(self):
        checker = Checker()
        checker.feed(packet(0) + b'garbage' + packet(512*50))
        self.assertEqual(checker.bad_dt, 0)
        self.assertEqual(checker.lost_sync, 7)


if __name__ == '__main__':
    unittest.main()
