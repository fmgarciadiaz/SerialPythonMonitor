"""First control milestone: PC-originated PING and MCU-acknowledged status.

No transmitter/settings command is implemented yet. The request reuses the
validated MCU PING contract; Linux must return the original ADC/status frame.
"""
import secrets
import struct
import time
import zlib
from experimentos.tasas_spi.receiver.unoq_usb import BLOCK, Decoder


def status_request(request_id):
    if not 0x80000000 <= request_id < 0xffffffff:
        raise ValueError('Los identificadores del PC usan el bit alto')
    seed = (request_id*0x9e3779b1)&0xffffffff
    payload = bytes(((seed >> (8*(i&3))) ^ (i*17+0x5a))&255 for i in range(492))
    frame = struct.pack('<4sHHII',b'SCP1',2,2,request_id,492)+payload
    return frame+struct.pack('<I',zlib.crc32(frame))


class StatusSession:
    def __init__(self, connection):
        self.connection = connection
        # ACKs alternate between Linux PINGs and explicitly matched PC nonces.
        # All data checks remain active; query() verifies the requested ACK.
        self.decoder = Decoder(check_ack_sequence=False)
        self.buffer = bytearray()
        self.next_id = secrets.randbelow(0x7fffffff)|0x80000000

    def query(self, timeout=2, fragmented=False):
        request_id = self.next_id
        self.next_id = ((self.next_id+1)&0x7fffffff)|0x80000000
        if self.next_id == 0xffffffff:
            self.next_id = 0x80000000
        request = status_request(request_id)
        started = time.monotonic()
        if fragmented:
            # Force partial TCP commands for the integration test.
            for chunk in (request[:1], request[1:17], request[17:173], request[173:]):
                self.connection.socket.sendall(chunk)
                time.sleep(0.005)
        else:
            self.connection.socket.sendall(request)
        while time.monotonic()-started < timeout:
            while len(self.buffer) >= BLOCK:
                packet = bytes(self.buffer[:BLOCK]); del self.buffer[:BLOCK]
                self.decoder.frame(packet)
                ack = struct.unpack_from('<I',packet,16)[0]
                if ack != request_id:
                    continue
                rate,index,dropped,fatal,count,bits,channels,period,node,flags = struct.unpack_from('<IIIIHBBIII',packet,48)
                return dict(request_id=request_id,ack=ack,latency_ms=(time.monotonic()-started)*1000,
                            sample_rate_hz=rate,adc_bits=bits,channels=channels,period_us=period,
                            sample_index=index,dropped_nodes=dropped,acquisition_errors=fatal,
                            sequence=struct.unpack_from('<I',packet,8)[0])
            self.buffer.extend(self.connection.read())
        raise TimeoutError(f'El MCU no confirmó la consulta {request_id:#x}')
