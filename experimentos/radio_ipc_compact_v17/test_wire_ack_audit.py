import struct
import unittest
import zlib
from experimentos.radio_ipc_compact_v17.wire_ack_audit import WireAckAudit


def frame(kind=12,rid=100,session=1):
    data=bytearray(992)
    struct.pack_into('<4sHHII',data,0,b'SCP1',4,kind,8,972)
    struct.pack_into('<II',data,16,rid,session)
    struct.pack_into('<I',data,988,zlib.crc32(data[:988]))
    return bytes(data)


class AuditTests(unittest.TestCase):
    def test_fragmented_ack_uses_final_recv_and_records_ahead_bytes(self):
        audit=WireAckAudit(); data=frame(kind=20)+frame()
        audit.feed(data[:1100],10)
        audit.feed(data[1100:],11)
        audit.acknowledge(100,1,11.03)
        row=audit.snapshot()['top'][0]
        self.assertAlmostEqual(row['complete_recv_to_callback_ms'],30)
        self.assertEqual(row['ack_start_offset_in_last_recv'],0)
        self.assertEqual(row['ack_end_offset_in_last_recv'],884)

    def test_multiple_frames_order_and_more_reads(self):
        audit=WireAckAudit(); audit.feed(frame(kind=20)*3+frame(),1)
        audit.feed(frame(kind=20),2)
        audit.acknowledge(100,1,2.01)
        row=audit.snapshot()['top'][0]
        self.assertEqual(row['ack_start_offset_in_last_recv'],2976)
        self.assertEqual(row['more_reads_before_callback'],1)

    def test_session_mismatch_and_duplicates_do_not_create_matches(self):
        audit=WireAckAudit(); audit.feed(frame(),1)
        audit.acknowledge(100,2,2)
        audit.acknowledge(100,1,3)
        self.assertEqual(audit.matches,0)

    def test_corruption_disables_observer_without_raising(self):
        for location in (0,100):
            data=bytearray(frame());data[location]^=1
            audit=WireAckAudit();audit.feed(data,1)
            self.assertIsNotNone(audit.disabled)
            audit.feed(frame()*100,2)
            self.assertEqual(len(audit.buffer),0)

    def test_storage_bounds(self):
        audit=WireAckAudit()
        for i in range(1000):
            audit.feed(frame(rid=i),i)
        self.assertEqual(len(audit.pending),256)
        for i in range(744,1000):
            audit.acknowledge(i,1,1001)
        self.assertEqual(len(audit.top),8)
        self.assertEqual(len(audit.recent),32)

    def test_same_rid_splits_total_duration_without_mixing_maxima(self):
        audit=WireAckAudit();audit.feed(frame(),10)
        audit.acknowledge(100,1,10.02,9.9)
        row=audit.snapshot()['top_total'][0]
        self.assertAlmostEqual(row['send_to_complete_recv_ms'],100)
        self.assertAlmostEqual(row['complete_recv_to_callback_ms'],20)
        self.assertAlmostEqual(row['send_to_callback_ms'],120)


if __name__=='__main__':
    unittest.main()
