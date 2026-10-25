import unittest
import struct
import numpy as np
from types import SimpleNamespace
from unittest.mock import Mock
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver


class FrameServiceTests(unittest.TestCase):
    def test_priming_window_waits_for_chunk_acks_before_play(self):
        class Source:
            live=True
            credit_window=2
            target_blocks=2
            maximum_blocks=2
            def __len__(self):return 10000
            def __getitem__(self, key):return np.zeros(key.stop-key.start,dtype=np.uint16)
        connection=SimpleNamespace(socket=Mock())
        receiver=OutputReceiver(connection,lambda rows:None)
        receiver.wav_candidate=True;receiver.wav_codes=Source();receiver.wav_session=9
        receiver.wav_status=SimpleNamespace(session=9,free_blocks=30,accepted=0,queue_slots=30)
        receiver.service_wav()
        self.assertEqual(len(receiver.wav_inflight),2)
        self.assertFalse(receiver.wav_started)
        self.assertTrue(all(entry[1]==13 for entry in receiver.wav_inflight.values()))
        receiver.service_wav()
        self.assertEqual(connection.socket.sendall.call_count,2)
        # One chunk ACK is insufficient: PLAY must not clear the second credit.
        rid=next(iter(receiver.wav_inflight));del receiver.wav_inflight[rid]
        receiver.wav_pending=next((key,entry[0]) for key,entry in receiver.wav_inflight.items())
        receiver.wav_status=SimpleNamespace(session=9,free_blocks=29,accepted=480,queue_slots=30)
        receiver.service_wav()
        self.assertFalse(receiver.wav_started)
        self.assertEqual(connection.socket.sendall.call_count,2)
        receiver.wav_inflight.clear();receiver.wav_pending=None
        receiver.wav_status=SimpleNamespace(session=9,free_blocks=28,accepted=960,queue_slots=30)
        receiver.service_wav()
        self.assertTrue(receiver.wav_started)
        self.assertEqual(struct.unpack_from('<H',connection.socket.sendall.call_args.args[0],6)[0],11)

    def test_existing_gate_and_exact_private_profile_only(self):
        base=dict(bits=8,rate=1818181,channels=1,period=88,node_pairs=3488)
        cases=[(base,True,True),(base,False,False),
               (dict(base,channels=2),True,False),(dict(base,period=89),True,False),
               (dict(base,node_pairs=3456),True,False),
               (dict(base,bits=10,rate=1250000),True,True),
               (dict(base,bits=10,rate=909090),True,False),
               (dict(base,rate=1600000,period=100,node_pairs=3456),True,False)]
        for config,radio,expected in cases:
            with self.subTest(config=config,radio=radio):
                receiver=OutputReceiver(SimpleNamespace(socket=Mock()),lambda rows:None)
                receiver.config=SimpleNamespace(**config)
                receiver.wav_codes=SimpleNamespace(radio_audio=radio)
                receiver.decoder=SimpleNamespace(events=[]);receiver.service_wav=Mock()
                receiver._process_decoder_events()
                self.assertEqual(receiver.service_wav.call_count,int(expected))
