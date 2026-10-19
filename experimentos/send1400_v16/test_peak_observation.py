"""Instrumentation preserves decoding across fragmented reads and sticky peaks."""
import struct
import unittest
from experimentos.send1400_v16.qualify_margin import ObservedDecoder,OriginalDecoder,EVENTS
from experimentos.maxfreq_v16.test_contract import packet
from experimentos.maxfreq_v16.contract import seal

class ObservationTests(unittest.TestCase):
    def test_fragmentation_and_pre_measurement_peak(self):
        frames=[]
        for seq in range(12):
            index=seq*864
            p=bytearray(packet(8,114,3456,index,index//3456,seq,[seq]*864,index*114))
            struct.pack_into('<II',p,88,1,1 if seq<3 else 4)
            frames.append(seal(p))
        data=b''.join(frames)
        for chunk in (1,991,992,1500,len(data)):
            EVENTS.clear();plain=OriginalDecoder();observed=ObservedDecoder()
            for start in range(0,len(data),chunk):
                plain.feed(data[start:start+chunk]);observed.feed(data[start:start+chunk])
            for name in ('seq','profile','epoch','last','pairs','nodes','status','queue_hist','send_ticks','maxima'):
                self.assertEqual(getattr(plain,name),getattr(observed,name))
            observed.reset_metrics()
            self.assertEqual([e['status']['queue_peak'] for e in EVENTS if e['event']=='peak_change'],[1,4])
            self.assertEqual(EVENTS[-1]['event'],'measurement_start')
            self.assertEqual(EVENTS[-1]['status']['queue_peak'],4)
            self.assertFalse(observed.maxima)
    def test_rejections_preserved(self):
        first=packet(8,114,3456,0,0,0,[1]*864,0)
        corrupt=bytearray(first);corrupt[200]^=1
        gap=packet(8,114,3456,868,0,1,[1]*864,868*114)
        for data in (bytes(corrupt),first+gap):
            for decoder in (OriginalDecoder(),ObservedDecoder()):
                with self.assertRaises(ValueError):decoder.feed(data)
if __name__=='__main__':unittest.main()
