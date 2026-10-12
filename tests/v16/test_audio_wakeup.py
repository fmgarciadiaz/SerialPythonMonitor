import multiprocessing as mp
import socket
import unittest
from types import SimpleNamespace
from monitor.v16.synth_process import read_with_audio_wakeup

class AudioWakeupTests(unittest.TestCase):
    def test_worker_wakes_without_consuming_reply_and_socket_has_priority(self):
        left,right=socket.socketpair();parent,child=mp.Pipe()
        left.settimeout(.1)
        connection=SimpleNamespace(socket=left,read=lambda:left.recv(64))
        source=SimpleNamespace(audio_ready_handle=parent)
        try:
            child.send('block')
            self.assertEqual(read_with_audio_wakeup(connection,source),b'')
            right.sendall(b'ack')
            self.assertEqual(read_with_audio_wakeup(connection,source),b'ack')
            self.assertEqual(parent.recv(),'block')
            source.audio_ready_handle=None;right.sendall(b'adc')
            self.assertEqual(read_with_audio_wakeup(connection,source),b'adc')
        finally:
            left.close();right.close();parent.close();child.close()
