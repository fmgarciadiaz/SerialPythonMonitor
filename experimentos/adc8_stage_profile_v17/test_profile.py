import struct
import unittest
import zlib
from experimentos.adc8_stage_profile_v17.decoder import ProfileDecoder
from experimentos.adc8_stage_profile_v17.run import relay_summary


def packet(sequence,tag,value):
    p=bytearray(992)
    struct.pack_into('<4sHHII',p,0,b'SCP1',4,20,sequence,972)
    struct.pack_into('<II',p,40,0xd17a0000|tag,value)
    struct.pack_into('<IIIIHBBIII',p,48,160000000//114,0,0,0,0,8,1,114,0,2)
    struct.pack_into('<8I',p,84,3456,1,1,0,0,1000,0,0)
    struct.pack_into('<I',p,988,zlib.crc32(p[:988]))
    return bytes(p)


class ProfileTests(unittest.TestCase):
    def test_fragmentation_coherent_triplets_and_counter_wrap(self):
        d=ProfileDecoder()
        stream=b''.join(packet(i,tag,value) for i,(tag,value) in enumerate(
            [(0,10),(1,0xfffffff0),(2,40),(0,12),(1,0x30),(2,45)]))
        for i in range(0,len(stream),77):d.feed(stream[i:i+77])
        self.assertEqual(d.profile,(8,114,3456))
        row=d.summary()['cache']
        self.assertEqual(row['count'],2)
        self.assertEqual(row['sum_ticks'],64)
        self.assertAlmostEqual(row['mean_us'],.2)
        self.assertEqual(row['maximum_since_boot_ticks'],45)
        d.reset_metrics()
        self.assertEqual(d.summary(),{})

    def test_invalid_crc_never_populates_timings(self):
        d=ProfileDecoder()
        p=bytearray(packet(0,0,99));p[100]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):d.feed(p)
        self.assertEqual(d.previous,{})

    def test_relay_discards_startup_window(self):
        import json
        log='\n'.join('PROFILE_RELAY '+json.dumps(dict(stage=i,start_s=start,
            end_s=start+10,count=10,sum_ns=total,max_ns=total//2))
            for start,total in ((0,1000000),(10,1000),(20,3000)) for i in range(6))
        result=relay_summary(log)
        self.assertEqual(result['spi_ioctl']['count'],20)
        self.assertEqual(result['spi_ioctl']['mean_us'],.2)
        self.assertEqual(result['spi_ioctl']['maximum_us'],1.5)


if __name__=='__main__':unittest.main()
