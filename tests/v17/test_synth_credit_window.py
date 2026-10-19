import unittest,struct
from unittest.mock import MagicMock
from types import SimpleNamespace
import numpy as np
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.fm_source import FMSource

class SynthCreditWindowTests(unittest.TestCase):
    def receiver(self,codes):
        socket=MagicMock();r=OutputReceiver(SimpleNamespace(socket=socket,read=lambda:b''),lambda _:None)
        r.wav_candidate=True;r.wav_codes=codes;r.wav_session=123;r.wav_started=True;r.wav_live_credits=3
        r.wav_status=SimpleNamespace(session=123,free_blocks=16,accepted=0)
        return r,socket
    def test_three_pending_chunks_offsets_ack_and_serialized_stop(self):
        r,socket=self.receiver(FMSource(rate=20000));r.service_wav();r.service_wav()
        frames=[c.args[0] for c in socket.sendall.call_args_list]
        self.assertEqual(len(r.wav_inflight),3)
        self.assertEqual([struct.unpack_from('<I',f,20)[0] for f in frames],[0,480,960])
        first=struct.unpack_from('<I',frames[0],8)[0]
        r.decoder=MagicMock();r.decoder.events=[('wav',SimpleNamespace(request_id=first,session=123,rate=20000,reason=0,state=2,accepted=480,free_blocks=15))]
        r.pump();self.assertEqual(len(r.wav_inflight),3)
        self.assertEqual(struct.unpack_from('<I',socket.sendall.call_args.args[0],20)[0],1440)
        r.wav_request(3);self.assertEqual(len(r.wav_inflight),1)
        r.pump();self.assertEqual(len(r.wav_inflight),1)
    def test_file_wav_still_serializes_and_target_bounds_reservations(self):
        r,socket=self.receiver(np.zeros(4800,dtype='<u2'));r.service_wav();r.service_wav()
        self.assertEqual(len(r.wav_inflight),1)
        r,socket=self.receiver(FMSource(rate=20000));r.wav_status.free_blocks=12
        r.service_wav();r.service_wav();self.assertEqual(len(r.wav_inflight),1)
        self.assertEqual(r.wav_codes.target_blocks,5)

    def test_explicit_short_block_offsets_keep_credit_bounds(self):
        r,socket=self.receiver(FMSource(rate=20000));r.wav_chunk_points=240
        r.service_wav();r.service_wav()
        frames=[c.args[0] for c in socket.sendall.call_args_list]
        self.assertEqual(len(r.wav_inflight),3)
        self.assertEqual([struct.unpack_from('<I',f,20)[0] for f in frames],[0,240,480])
        self.assertEqual([struct.unpack_from('<H',f,24)[0] for f in frames],[240]*3)
        self.assertEqual(r.wav_next_offset,720)

    def test_four_short_credits_stay_bounded_and_stop_supersedes(self):
        r,socket=self.receiver(FMSource(rate=20000))
        r.wav_chunk_points=240;r.wav_live_credits=4
        r.service_wav();r.service_wav()
        frames=[c.args[0] for c in socket.sendall.call_args_list]
        self.assertEqual(len(r.wav_inflight),4)
        self.assertEqual([struct.unpack_from('<I',f,20)[0] for f in frames],[0,240,480,720])
        r.wav_request(3);self.assertEqual(len(r.wav_inflight),1)
