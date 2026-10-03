import struct
import unittest
import zlib
from unittest.mock import patch
from test_spi_native import adc_frame
from test_dual_output import reply, idle
from transport.unoq_receiver import LegacyDecoder, OutputReceiver
from transport.unoq_switch import Mode
from transport.unoq_usb import ProtocolError


def data(index, count=512):
    samples = b''.join(struct.pack('<IHH', i*32, 10, 20) for i in range(index, index+count))
    return b'DATA'+struct.pack('<BH', 1, count)+samples


class ReaderTests(unittest.TestCase):
    def test_fragmented_data_and_only_initial_resync(self):
        decoder = LegacyDecoder()
        packets = data(0)+data(512)
        batches = []
        for i in range(0, len(packets), 37):
            batches.extend(decoder.feed(packets[i:i+37]))
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[1][0][0], 512*32)
        decoder = LegacyDecoder()
        self.assertEqual(len(decoder.feed(b'partial'+data(0))), 1)
        with self.assertRaises(ProtocolError): decoder.feed(b'x'+data(512))

    def test_range_header_and_timestamp_errors(self):
        variants = [data(0, 511)]
        p = bytearray(data(0)); struct.pack_into('<H', p, 11, 16384); variants.append(p)
        p = bytearray(data(0)); struct.pack_into('<I', p, 15, 64); variants.append(p)
        for packet in variants:
            with self.assertRaises(ProtocolError): LegacyDecoder().feed(packet)


class FakeReader:
    def __init__(self, path):
        self.path = path
        self.records = []
        self.closed = False
    def drain(self):
        records, self.records = self.records, []
        return records
    def close(self): self.closed = True


class MCU:
    def __init__(self):
        self.socket = self
        self.sequence = 0
        self.frames = []
        self.index = 0
        self.on_switch = lambda mode: None
    def emit(self, frame):
        self.frames.append(frame)
        self.sequence += 1
    def samples(self, start, end):
        for index in range(start, end, 53):
            self.emit(adc_frame(seq=self.sequence, index=index, count=min(53, end-index), timestamp=index*32))
        self.index = end
    def sendall(self, p):
        rid = struct.unpack_from('<I', p, 8)[0]
        if p[6] == 4:
            self.on_switch(p[16])
            frame = bytearray(reply(self.sequence, p[16], self.index))
            struct.pack_into('<I', frame, 16, rid)
        else:
            frame = bytearray(idle(self.sequence))
            struct.pack_into('<I', frame, 16, rid)
        struct.pack_into('<I', frame, 508, zlib.crc32(frame[:508]))
        self.emit(bytes(frame))
    def read(self):
        if self.frames:
            item = self.frames.pop(0)
            if callable(item): item(); return b''
            return item
        self.emit(idle(self.sequence))
        return self.frames.pop(0)


class ReceiverTests(unittest.TestCase):
    def setup_receiver(self):
        mcu = MCU()
        samples = []
        receiver = OutputReceiver(mcu, samples.extend, reader_factory=FakeReader)
        receiver.select(Mode.SPI)
        return mcu, receiver, samples

    def test_live_switch_delayed_uart_boundary_and_one_timeline(self):
        mcu, receiver, samples = self.setup_receiver()
        mcu.samples(0, 2048)
        while mcu.frames: receiver.pump()
        with patch('transport.unoq_receiver.R4_BOOT_SECONDS', 0):
            receiver.select(Mode.UART, 'r4')
        # A USB UART tail can arrive after APPLIED and the first new SPI frame.
        receiver.r4.records = [(i*32, 10, 20) for i in range(2048, 3072)]
        receiver.pump()
        mcu.index = 4096
        receiver.pending = (0x80000100, Mode.SPI)
        mcu.emit(reply(mcu.sequence, Mode.SPI, 4096))
        mcu.samples(4096, 4149)
        receiver.pump()
        receiver.pump()
        self.assertEqual(len(samples), 3072)
        receiver.r4.records = [(i*32, 10, 20) for i in range(3072, 4096)]
        receiver.pump()
        self.assertEqual([r[3] for r in samples], list(range(4149)))
        self.assertEqual(receiver.mode, Mode.SPI)
        self.assertIsNone(receiver.uart_end)
        receiver.close()

    def test_uart_arriving_before_ack_is_preserved(self):
        mcu, receiver, samples = self.setup_receiver()
        mcu.samples(0, 2048)
        while mcu.frames: receiver.pump()
        def early(mode):
            if mode == Mode.UART:
                receiver.r4.records = [(i*32, 10, 20) for i in range(2048, 2560)]
        mcu.on_switch = early
        with patch('transport.unoq_receiver.R4_BOOT_SECONDS', 0):
            receiver.select(Mode.UART, 'r4')
        self.assertEqual(len(samples), 2560)
        self.assertEqual(samples[-1][3], 2559)
        receiver.close()

    def test_gap_between_transports_is_fatal(self):
        mcu, receiver, samples = self.setup_receiver()
        mcu.samples(0, 2048)
        while mcu.frames: receiver.pump()
        with patch('transport.unoq_receiver.R4_BOOT_SECONDS', 0):
            receiver.select(Mode.UART, 'r4')
        receiver.r4.records = [(2049*32, 10, 20)]
        with self.assertRaisesRegex(ProtocolError, 'Pérdida'):
            receiver.pump()
        receiver.close()

    def test_fresh_connection_can_recover_from_previous_uart(self):
        mcu = MCU(); mcu.index = 8192
        samples = []
        receiver = OutputReceiver(mcu, samples.extend)
        receiver.select(Mode.SPI)
        mcu.samples(8192, 8245)
        receiver.pump()
        self.assertEqual(samples[0][3], 8192)
        receiver.close()

    def test_switch_supersedes_heartbeat_that_could_be_hidden_by_control_reply(self):
        mcu, receiver, samples = self.setup_receiver()
        receiver.ping = (0x80000000, 0)
        receiver._switch(Mode.SPI)
        self.assertIsNone(receiver.ping)
        receiver.close()

    def test_switch_refusal_does_not_report_applied(self):
        mcu, receiver, samples = self.setup_receiver()
        def reject(p):
            rid = struct.unpack_from('<I', p, 8)[0]
            packet = bytearray(reply(mcu.sequence, Mode.UART, 0))
            struct.pack_into('<I', packet, 16, rid)
            packet[21] = Mode.SPI
            packet[22] = 3
            packet[23] = 4
            struct.pack_into('<I', packet, 508, zlib.crc32(packet[:508]))
            mcu.emit(bytes(packet))
        mcu.sendall = reject
        with self.assertRaisesRegex(RuntimeError, 'rechazó'):
            receiver._switch(Mode.UART)
        self.assertIsNone(receiver.applied)
        self.assertEqual(receiver.mode, Mode.SPI)
        receiver.close()
