"""Passive, bounded SCP1 ACK completion observer. Never issues commands."""
from collections import OrderedDict, deque
import struct
import zlib


class WireAckAudit:
    def __init__(self):
        self.buffer = bytearray()
        self.received = self.frames = self.reads = self.acks = self.matches = 0
        self.disabled = None
        self.pending = OrderedDict()
        self.top = []
        self.top_total = []
        self.recent = deque(maxlen=32)
        self.evicted = 0

    def feed(self, data, completed_at):
        if self.disabled or not data:
            return
        self.reads += 1
        previous_bytes = self.received
        self.received += len(data)
        self.buffer.extend(data)
        while len(self.buffer) >= 992:
            frame = bytes(self.buffer[:992])
            del self.buffer[:992]
            if struct.unpack_from('<4sHH',frame)[:2] != (b'SCP1',4) or struct.unpack_from('<I',frame,12)[0] != 972:
                self.disabled = 'Observer lost SCP1 framing; production decoder remains authoritative'
                self.buffer.clear()
                return
            self.frames += 1
            if struct.unpack_from('<H',frame,6)[0] != 12:
                continue
            if zlib.crc32(frame[:988]) != struct.unpack_from('<I',frame,988)[0]:
                self.disabled = 'ACK CRC invalid in observer; production decoder remains authoritative'
                self.buffer.clear()
                return
            rid, session = struct.unpack_from('<II',frame,16)
            self.acks += 1
            end_byte = self.received-len(self.buffer)
            self.pending[rid] = dict(request_id=rid,session=session,
                completed_recv_at=completed_at,read_number=self.reads,
                frame_number=self.frames,
                ack_start_offset_in_last_recv=max(0,end_byte-992-previous_bytes),
                ack_end_offset_in_last_recv=end_byte-previous_bytes)
            self.pending.move_to_end(rid)
            while len(self.pending) > 256:
                self.pending.popitem(last=False)
                self.evicted += 1

    def acknowledge(self, rid, session, observed_at, sent_at=None):
        record = self.pending.pop(rid,None)
        if record is None or record['session'] != session:
            return
        record['callback_at'] = observed_at
        record['complete_recv_to_callback_ms'] = (observed_at-record['completed_recv_at'])*1000
        record['more_reads_before_callback'] = self.reads-record['read_number']
        if sent_at is not None:
            record['sent_at'] = sent_at
            record['send_to_complete_recv_ms'] = (record['completed_recv_at']-sent_at)*1000
            record['send_to_callback_ms'] = (observed_at-sent_at)*1000
            self.top_total.append(record)
            self.top_total.sort(key=lambda item:item['send_to_callback_ms'],reverse=True)
            del self.top_total[8:]
        self.matches += 1
        self.recent.append(record)
        self.top.append(record)
        self.top.sort(key=lambda item:item['complete_recv_to_callback_ms'],reverse=True)
        del self.top[8:]

    def snapshot(self):
        return dict(reads=self.reads,frames=self.frames,acks=self.acks,matches=self.matches,
                    disabled=self.disabled,pending=len(self.pending),evicted=self.evicted,
                    buffered_bytes=len(self.buffer),top=list(self.top),top_total=list(self.top_total),recent=list(self.recent))
