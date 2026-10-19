import random
import unittest
from unittest.mock import patch
from monitor.v17.receiver.native_unpack import unpack_native


class NativeUnpackTests(unittest.TestCase):
    def test_exact_samples_extremes_random_and_uint32_wrap(self):
        rng=random.Random(17)
        for bits in (8,10,12,14,16):
            for channels in (1,2):
                for count in (4,64,432):
                    maximum=(1<<bits)-1
                    values=[rng.randrange(maximum+1) for _ in range(count*channels)]
                    values[:4]=[0,maximum,1,maximum-1]
                    group=4 if bits in (10,14) else 2 if bits==12 else 1
                    payload=b''.join(sum(v<<(bits*j) for j,v in enumerate(values[i:i+group])).to_bytes(group*bits//8,'little') for i in range(0,len(values),group))
                    timestamp,index,period=0xfffffff0,0xfffffff0,2099
                    expected=[((timestamp+i*period)&0xffffffff,values[i*channels],values[i*channels+1] if channels==2 else 0,(index+i)&0xffffffff) for i in range(count)]
                    with self.subTest(bits=bits,channels=channels,count=count):
                        self.assertEqual(unpack_native(payload,bits,channels,count,timestamp,period,index),expected)
                        numeric=unpack_native(payload,bits,channels,count,timestamp,period,index,numeric=True)
                        self.assertEqual(list(numeric),expected)
                        self.assertEqual(numeric[0],expected[0])
                        self.assertEqual(numeric[-1],expected[-1])
    def test_missing_numpy_uses_existing_decoder_fallback(self):
        with patch('monitor.v17.receiver.native_unpack.np',None):
            self.assertIsNone(unpack_native(b'',8,1,0,0,1,0))
