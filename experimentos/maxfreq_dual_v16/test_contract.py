import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from experimentos.maxfreq_dual_v16.contract import Decoder, frame, seal, valid

ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent


def packet(bits,ticks,n,index,seq):
    p=frame(20,seq)
    struct.pack_into('<i',p,32,992)
    count=4
    struct.pack_into('<IIIIHBBIII',p,48,160000000//ticks,index,0,0,count,bits,2,ticks,0,0)
    struct.pack_into('<I',p,80,(0xfffffff0+index*ticks)&0xffffffff)
    struct.pack_into('<8I',p,84,n,1,2,100,100,100,100,1)
    values=[0,(1<<bits)-1,1,(1<<bits)-2]*2
    used=count*bits*2//8
    p[116:116+used]=sum(v<<(i*bits) for i,v in enumerate(values)).to_bytes(used,'little')
    return seal(p)


class DualContractTests(unittest.TestCase):
    def test_channels_clock_and_native_relay(self):
        base=EXP/'arduino/v16/relay/base_verifier.c'
        header=base.with_name('config_relay_protocol.h')
        source=f'#define main baseline_main\n#include "{base}"\n#undef main\n#include "{header}"\nint main(int argc,char**argv){{(void)argc;init_crc();DualChecker d={{.bits=(unsigned)atoi(argv[1]),.period=(uint32_t)strtoul(argv[2],0,10)}};uint8_t p[BLOCK];while(fread(p,1,BLOCK,stdin)==BLOCK)if(!dual_feed(&d,p))return 1;return 0;}}'
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'relay.c';src.write_text(source);binary=src.with_suffix('')
            subprocess.run(['cc','-O2','-std=c11',str(src),'-lm','-o',str(binary)],check=True,capture_output=True)
            for bits in (8,10,12,14,16):
                ticks=2400 if bits==16 else 400
                packets=packet(bits,ticks,1728,0,0)+packet(bits,ticks,1728,4,1)
                d=Decoder();d.feed(packets)
                self.assertEqual(d.pairs,8)
                self.assertEqual(d.last, (7,(0xfffffff0+7*ticks)&0xffffffff))
                subprocess.run([str(binary),str(bits),str(0x80000000|(1728<<16)|ticks)],input=packets,check=True)
                broken=bytearray(packet(bits,ticks,1728,0,0));broken[67]=1
                with self.assertRaises(ValueError):Decoder().feed(seal(broken))

    def test_bounds(self):
        self.assertTrue(valid(16,2134,3456))
        self.assertTrue(valid(10,345,4176))
        self.assertFalse(valid(10,345,4192))
        self.assertFalse(valid(16,2047,3456))
        self.assertFalse(valid(14,155,1984))
        self.assertFalse(valid(12,400,4097))
