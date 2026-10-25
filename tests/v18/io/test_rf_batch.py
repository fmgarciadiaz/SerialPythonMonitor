import pickle
import unittest
import numpy as np
from monitor.v18.io.rf_batch import RawRfBatch
from monitor.v18.numeric_batch import NumericBatch, SampleClock
from monitor.v18.receiver.unoq_acquisition import Configuration

class RawBatchTests(unittest.TestCase):
    def test_wire_width_roundtrip_and_wrap_are_exact(self):
        config=Configuration(8,1600000)
        count=32000
        for channels in (1,2):
            config=Configuration(8,1600000) if channels==1 else Configuration(14,40000)
            indices=np.arange(count,dtype=np.uint64)
            raw=np.zeros((count,4),dtype=np.uint32)
            raw[:,0]=(0xfffffff0+indices*config.period)&0xffffffff
            raw[:,1]=indices%config.maximum
            raw[:,2]=indices*2%config.maximum
            raw[:,3]=(0xfffffff0+indices)&0xffffffff
            original=NumericBatch(raw,config.maximum,SampleClock(config.timestamp_hz),channels)
            compact=RawRfBatch(raw,config,3,4,12.)
            restored=pickle.loads(pickle.dumps(compact)).materialize(SampleClock(config.timestamp_hz))
            for name in original.columns:
                np.testing.assert_array_equal(original.columns[name],restored.columns[name])
            self.assertEqual(restored.receiver_generation,3)
            self.assertEqual(restored.published_at,12.)
            self.assertLess(len(pickle.dumps(compact)),len(pickle.dumps(original)))

if __name__=='__main__':unittest.main()
