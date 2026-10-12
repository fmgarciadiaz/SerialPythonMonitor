import struct
import unittest
from unittest.mock import patch
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_usb import Connection
from experimentos.maxfreq_dual_v16.verify_production import MeasuredConnection


class MeasurementTests(unittest.TestCase):
    def test_fragmented_frames_count_send_once_per_node_and_ignore_old_profile(self):
        config=Configuration(8,597014)
        def packet(node, offset, send, bits=8):
            p=bytearray(992);struct.pack_into('<H',p,6,20)
            struct.pack_into('<IIIIHBBIII',p,48,config.rate,
                            (node*config.node_pairs+offset)&0xffffffff,
                            0,0,4,bits,2,config.period,node,0)
            struct.pack_into('<8I',p,84,config.node_pairs,1,2,100,100,500,send,1)
            return p
        node=(1<<32)//config.node_pairs
        data=packet(node,0,200)+packet(node,4,200)+packet(node+1,0,400)+packet(node+1,4,900,bits=10)
        chunks=[data[:5],data[5:1300],data[1300:]]
        c=MeasuredConnection.__new__(MeasuredConnection);c.reset_measurement(config)
        with patch.object(Connection,'read',side_effect=chunks):
            for chunk in chunks:self.assertEqual(c.read(),chunk)
        self.assertEqual(c.send_ticks,[200,400])
        self.assertEqual(c.queue_peak,2)
        self.assertEqual(c.slack_min,500)
        self.assertEqual(c.measure_buffer,b'')
