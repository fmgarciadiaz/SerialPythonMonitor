"""Cross-language P992 wire tests; no hardware required."""
from pathlib import Path
import struct,subprocess,tempfile,unittest,zlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from monitor.v12.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v12.receiver.unoq_usb import ProtocolError
from monitor.v12.receiver.unoq_control import status_request
from monitor.v12.receiver.unoq_switch import switch_request
from monitor.v12.receiver.unoq_acquisition import acquisition_request,Configuration
from monitor.v12.receiver.unoq_generator import generator_request,GeneratorConfig
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'arduino/v11_p992'
def seal(p):
    p=bytearray(p);struct.pack_into('<I',p,988,zlib.crc32(p[:988]));return bytes(p)
class P992Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();folder=Path(cls.tmp.name)
        cpp=folder/'golden';cls.mcu=cpp;cls.checker=folder/'checker'
        subprocess.run(['c++','-std=c++17','-O0','-Wall','-Wextra','-Werror',str(BASE/'tests/golden.cpp'),'-o',str(cpp)],check=True)
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(BASE/'tests/checker.c'),'-lm','-o',str(cls.checker)],check=True)
        stream=subprocess.check_output([str(cpp)]);cls.frames=[stream[i:i+992] for i in range(0,len(stream),992)]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def c_accept(self,frames):
        return [line=='1' for line in subprocess.check_output([str(self.checker)],input=b''.join(frames)).decode().splitlines()]
    def test_golden_commands_and_responses(self):
        self.assertEqual(self.frames[0],status_request(0x80000001))
        commands=[status_request(0x80000001),switch_request(0x80000001,0),acquisition_request(0x80000001,Configuration(14,125000)),generator_request(0x80000001,None),generator_request(0x80000001,GeneratorConfig())]
        self.assertTrue(all(self.c_accept(commands+self.frames)))
        for frame in self.frames[1:]: ConfigurationDecoder().feed(frame)
        self.assertEqual(self.frames[1][984:988],bytes(4))
        self.assertEqual(self.frames[2][192:988],bytes(796))
    def test_mcu_decodes_python_commands(self):
        commands=[status_request(0x80000001),switch_request(0x80000001,0),acquisition_request(0x80000001,Configuration(14,125000)),generator_request(0x80000001,None),generator_request(0x80000001,GeneratorConfig())]
        def accepted(frames):
            return [v=='1' for v in subprocess.check_output([str(self.mcu),'decode'],input=b''.join(frames)).decode().splitlines()]
        self.assertTrue(all(accepted(commands)))
        corrupt=[]
        for frame in commands:
            for pos in range(992):
                p=bytearray(frame);p[pos]^=1;corrupt.append(bytes(p))
            p=bytearray(frame);p[4]=2;corrupt.append(seal(p))
            if frame[6]!=2:
                p=bytearray(frame);p[987]=1;corrupt.append(seal(p))
        self.assertFalse(any(accepted(corrupt)))
        ping=[]
        for pos in range(16,988):
            p=bytearray(commands[0]);p[pos]^=1;ping.append(seal(p))
        self.assertFalse(any(accepted(ping)))
    def test_uart_contract_stays_512_pairs(self):
        from monitor.v12.receiver.unoq_receiver import LegacyDecoder
        from monitor.v12.receiver.unoq_config_receiver import LegacyDecoder as ConfigLegacyDecoder
        packet=struct.pack('<4sBH',b'DATA',1,512)+b''.join(struct.pack('<IHH',i*32,123,456) for i in range(512))
        for cls in (LegacyDecoder,ConfigLegacyDecoder):
            d=cls();self.assertEqual(d.feed(packet[:100]),[])
            self.assertEqual(len(d.feed(packet[100:])[0]),512)
    def test_tcp_fragmentation(self):
        p=self.frames[1]
        for size in (1,3,79,113,991,992):
            decoder=ConfigurationDecoder();samples=[]
            for i in range(0,len(p),size):samples+=decoder.feed(p[i:i+size])
            self.assertEqual(len(samples),113)
        a=self.frames[1];b=bytearray(a);struct.pack_into('<I',b,8,1);struct.pack_into('<I',b,52,113)
        for i in range(113):struct.pack_into('<I',b,80+8*i,(113+i)*8)
        d=ConfigurationDecoder();self.assertEqual(len(d.feed(a+seal(b))),226)
    def test_whole_node_nineteen_fragments(self):
        frames=[]
        for seq,offset in enumerate(range(0,2048,113)):
            count=min(113,2048-offset)
            p=bytearray(self.frames[1]);p[80:988]=bytes(908)
            struct.pack_into('<I',p,8,seq);struct.pack_into('<I',p,52,offset);struct.pack_into('<H',p,64,count)
            for i in range(count):struct.pack_into('<IHH',p,80+8*i,(offset+i)*8,123,456)
            frames.append(seal(p))
        self.assertEqual(len(frames),19)
        self.assertTrue(all(self.c_accept(frames)))
        samples=ConfigurationDecoder().feed(b''.join(frames))
        self.assertEqual(len(samples),2048)
        self.assertEqual(samples[-1][3],2047)
    def test_corruption_every_position(self):
        originals=self.frames
        bad=[]
        for original in originals:
            for position in range(992):
                p=bytearray(original);p[position]^=1;bad.append(bytes(p))
                if original[6]!=2:
                    with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(p)
        self.assertFalse(any(self.c_accept(bad)))
    def test_resealed_semantic_corruption(self):
        corrupt=[]
        for position,value in ((4,2),(64,114),(984,1),(987,1),(67,3)):
            p=bytearray(self.frames[1]);p[position]=value;corrupt.append(seal(p))
        p=bytearray(self.frames[2]);p[192]=1;corrupt.append(seal(p))
        for frame in corrupt:
            with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(frame)
        self.assertFalse(any(self.c_accept(corrupt)))
        # Every PING payload byte must still be checked after recomputing CRC.
        ping=[]
        for position in range(16,988):
            p=bytearray(self.frames[0]);p[position]^=1;ping.append(seal(p))
        self.assertFalse(any(self.c_accept(ping)))
if __name__=='__main__':unittest.main()
