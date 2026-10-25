import queue
import unittest
import numpy as np
from monitor.v18.io.acquisition_path import AcquisitionPath
from monitor.v18.io.audio_pump import AudioPump
from monitor.v18.io.local_transport import LocalTransport
from monitor.v18.io.prototype import Rf,RfBarrier
from monitor.v18.io.wire_adapter import ProtocolIngress
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_native import PROFILES,code
from tests.v18.io.rf_vectors import native_frame
from tests.v18.io.protocol_vectors import packet


class NumericRfTests(unittest.TestCase):
    def test_native_profiles_keep_exact_columns_wrap_fragmentation_and_frame_boundaries(self):
        for bits,channels in sorted({(p['bits'],p['channels']) for p in PROFILES}):
            profile=next(p for p in PROFILES if (p['bits'],p['channels'])==(bits,channels))
            config=Configuration.from_wire(bits,code(profile))
            with self.subTest(bits=bits,channels=channels):
                first,expected_first=native_frame(config,index=0xfffffffc,timestamp=0xfffffff0,sequence=0xffffffff)
                second,expected_second=native_frame(config,timestamp=(0xfffffff0+4*config.period)&0xffffffff)
                pump=AudioPump(LocalTransport());rf=queue.Queue(4);events=queue.Queue(4)
                path=AcquisitionPath(pump,rf,events);pump.ingress.on_event=path.event
                stream=first+second
                for offset in range(0,len(stream),137):pump.ingress.feed(stream[offset:offset+137])
                frames=[rf.get_nowait(),rf.get_nowait()]
                self.assertTrue(rf.empty());self.assertEqual(path.emitted,2)
                announcement=events.get_nowait();gate=RfBarrier(block_size=None)
                gate.configure(announcement['generation'],announcement['rf_barrier'],announcement['first_index'])
                for ordinal,(frame,expected) in enumerate(zip(frames,(expected_first,expected_second))):
                    self.assertIsInstance(frame.payload,np.ndarray)
                    self.assertEqual(frame.payload.dtype,np.dtype(np.uint32))
                    self.assertEqual(frame.payload.shape,(4,4))
                    np.testing.assert_array_equal(frame.payload,expected)
                    self.assertFalse(frame.payload.flags.writeable)
                    self.assertEqual((frame.generation,frame.ordinal),(1,ordinal))
                    self.assertTrue(gate.consume(frame))
                # Later decoding must not overwrite an array already published.
                np.testing.assert_array_equal(frames[0].payload,expected_first)

    def test_legacy_dual_frames_also_publish_numeric_columns(self):
        events=[];ingress=ProtocolIngress(lambda kind,value:events.append((kind,value)))
        ingress.feed(packet(count=2))
        self.assertIsInstance(events[0][1].array,np.ndarray)
        np.testing.assert_array_equal(events[0][1].array,np.asarray([(0,123,456,0),(8,123,456,1)],dtype=np.uint32))

    def test_numeric_barrier_rejects_invalid_dtype_shape_or_first_index(self):
        for payload in (np.zeros((4,4),dtype=np.float64),np.zeros((4,3),dtype=np.uint32),
                        np.ones((4,4),dtype=np.uint32)):
            with self.subTest(dtype=payload.dtype,shape=payload.shape):
                gate=RfBarrier(block_size=None);gate.configure(1,0,0)
                with self.assertRaises(ValueError):gate.consume(Rf(0,4,payload,1,0))
                self.assertEqual(gate.consumed,0)
