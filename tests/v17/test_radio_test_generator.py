import unittest
import subprocess,tempfile
from pathlib import Path
import numpy as np
from monitor.v17.receiver.unoq_generator import GeneratorConfig,unpack_config
from monitor.v17.radio_am import AMDemodulator,RadioConfig

ROOT=Path(__file__).resolve().parents[2]

class GeneratorTests(unittest.TestCase):
    def test_real_firmware_table_has_two_am_carriers(self):
        header=ROOT/'arduino/v17/oscilloscope/sketch/radio_test.h'
        import re
        lut=re.search(r'sine\[256\]=\{([^}]+)\}',(header.parent/'generator.h').read_text()).group(1)
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'test.cpp';exe=Path(folder)/'test'
            src.write_text(f'''#include <cstdio>
#include "{header}"
#include "{header.parent/'generator_timing.h'}"
int main(){{scope_gen::Config c{{1,1,3,20000000,40000000,800,3300,1000}};
const uint16_t lut[256]={{{lut}}};
if(!scope_gen::valid(c)||!radio_test::valid(c))return 1;
auto timing=generator::timing(25000,5120);
if(timing.prescaler||timing.reload!=1249)return 2;
for(unsigned i=0;i<5120;++i)std::printf("%u\\n",radio_test::sample(c,i,lut));}}
''')
            subprocess.run(['c++','-std=c++17',str(src),'-o',str(exe)],check=True)
            codes=np.array([int(x) for x in subprocess.check_output([str(exe)],text=True).split()])
        self.assertTrue(np.all((codes>=800)&(codes<=3300)))
        spectrum=abs(np.fft.rfft(codes-codes.mean()))
        for carrier in (20,40):
            self.assertGreater(spectrum[carrier*40],spectrum[(carrier+1)*40])
            self.assertAlmostEqual(spectrum[(carrier+1)*40]/spectrum[carrier*40],.25,delta=.005)
            self.assertAlmostEqual(spectrum[(carrier-1)*40]/spectrum[carrier*40],.25,delta=.005)
        # Reconstruct the actual periodic DAC table at RF acquisition timestamps.
        rate=160000000/114;t=np.arange(int(rate*.08))/rate
        signal=np.interp((t*128000)%5120,np.arange(5121),np.r_[codes,codes[0]])*3.3/4095
        for carrier in (20000,40000):
            d=AMDemodulator(RadioConfig(rate,carrier))
            audio=d.process(signal)[int(.03*d.output_rate):]
            freq=np.fft.rfftfreq(len(audio),1/d.output_rate)
            self.assertLess(abs(freq[np.argmax(abs(np.fft.rfft(audio)))]-1000),30)

    def test_hz_immutable_table_frequency_and_hardware_fault(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'stream'
            subprocess.run(['c++','-std=c++17','-O2',str(ROOT/'arduino/v17/tests/radio_test_table.cpp'),'-o',str(exe)],check=True)
            codes=np.fromstring(subprocess.check_output([str(exe)],text=True),sep='\n')
        self.assertEqual(len(codes),128000)
        spectrum=abs(np.fft.rfft(codes-codes.mean()))
        for carrier in (20525,40750):
            self.assertEqual(np.argmax(spectrum[carrier-100:carrier+101])+carrier-100,carrier)
            self.assertAlmostEqual(spectrum[carrier+750]/spectrum[carrier],.25,delta=.005)
            self.assertAlmostEqual(spectrum[carrier-750]/spectrum[carrier],.25,delta=.005)
        rate=160000000/114;t=np.arange(int(rate*.12))/rate
        signal=np.interp(t*128000,np.arange(len(codes)),codes)*3.3/4095
        for carrier in (20525,40750):
            d=AMDemodulator(RadioConfig(rate,carrier))
            audio=d.process(signal)[int(.04*d.output_rate):]
            freq=np.fft.rfftfreq(len(audio),1/d.output_rate)
            self.assertLess(abs(freq[np.argmax(abs(np.fft.rfft(audio)))]-750),20)

    def test_hz_status_is_accepted_by_host_and_relay(self):
        from monitor.v17.receiver.unoq_generator import generator_reply
        header=ROOT/'arduino/v17/oscilloscope/sketch/generator_protocol.h'
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'reply.cpp';exe=Path(folder)/'reply';checker=Path(folder)/'checker'
            source.write_text(f"""#include <cstdio>
#include "{header}"
int main(){{uint8_t p[992];scope_gen::Config c{{1,1,3,750000,20525000,800,3300,750}};
if(!scope_gen::valid(c))return 1;
scope_gen::Reply reply{{0x80000001,2,0,1,c,c}};
scope_gen::encode(p,0,reply);fwrite(p,1,992,stdout);}}
""")
            subprocess.run(['c++','-std=c++17',str(source),'-o',str(exe)],check=True)
            packet=subprocess.check_output([str(exe)])
            reply=generator_reply(packet)
            self.assertTrue(reply.radio_test_hz_capable)
            self.assertEqual((reply.active.frequency,reply.active.duration),(750000,750))
            subprocess.run(['cc','-std=c11','-O2',str(ROOT/'arduino/v17/tests/checker.c'),'-lm','-o',str(checker)],check=True,capture_output=True)
            self.assertEqual(subprocess.check_output([str(checker)],input=packet),b'1\n')

    def test_independent_carriers_table_and_protocol(self):
        header=ROOT/'arduino/v17/oscilloscope/sketch/radio_test.h'
        import re
        lut=re.search(r'sine\[256\]=\{([^}]+)\}',(header.parent/'generator.h').read_text()).group(1)
        from monitor.v17.receiver.unoq_generator import generator_reply
        from monitor.v17.receiver.unoq_usb import ProtocolError
        import struct,zlib
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'test.cpp';exe=Path(folder)/'test';checker=Path(folder)/'checker'
            src.write_text(f'''#include <cstdio>
#include "{header}"
int main(int argc,char**argv){{const uint16_t lut[256]={{{lut}}};
for(unsigned mask=0;mask<4;++mask){{scope_gen::Config c{{1,1,3,(mask&1)?20000000u:0u,(mask&2)?40000000u:0u,800,3300,1000}};
if(!scope_gen::valid(c))return 1;
if(argc>1){{uint8_t p[992];scope_gen::Reply r{{0x80000001,2,0,1,c,c}};scope_gen::encode(p,0,r);fwrite(p,1,992,stdout);}}
else for(unsigned i=0;i<5120;++i){{
const auto actual=radio_test::sample(c,i,lut);
if(mask==3){{const int32_t a=int32_t(lut[(i*800/20+64)&255])-32768;
const int32_t b=int32_t(lut[(i*1600/20+64)&255])-32768;
const int32_t tone=int32_t(lut[(i*40/20)&255])-32768;
int32_t unit=32768+(a+b)*(16384+tone/4)/49152;
if(unit<0)unit=0;if(unit>65535)unit=65535;
const uint16_t old=800+uint16_t((uint32_t(2500)*uint32_t(unit)+32767)/65535);
if(actual!=old)return 2;}}
printf("%u\\n",actual);}}}}}}
''')
            subprocess.run(['c++','-std=c++17',str(src),'-o',str(exe)],check=True)
            tables=np.fromstring(subprocess.check_output([str(exe)],text=True),sep='\n').reshape(4,5120)
            self.assertEqual(np.ptp(tables[0]),0)
            for mask in (1,2,3):
                spectrum=abs(np.fft.rfft(tables[mask]-tables[mask].mean()))
                for bit,carrier in ((1,20000),(2,40000)):
                    if mask&bit:self.assertGreater(spectrum[carrier//25],1e5)
                    else:self.assertLess(spectrum[carrier//25],1000)
            subprocess.run(['cc','-std=c11',str(ROOT/'arduino/v17/tests/checker.c'),'-lm','-o',str(checker)],check=True,capture_output=True)
            packets=subprocess.check_output([str(exe),'reply'])
            for offset in range(0,len(packets),992):
                packet=packets[offset:offset+992]
                self.assertTrue(generator_reply(packet).radio_test_independent_capable)
                self.assertEqual(subprocess.check_output([str(checker)],input=packet),b'1\n')
            legacy=bytearray(packets[:992]);legacy[23]=15
            struct.pack_into('<I',legacy,988,zlib.crc32(legacy[:988]))
            with self.assertRaises(ProtocolError):generator_reply(legacy)
            self.assertEqual(subprocess.check_output([str(checker)],input=legacy),b'0\n')

    def test_contract_and_unmodulated_tone_zero(self):
        c=GeneratorConfig(wave=1,mode=3,frequency=20000000,final_frequency=40000000,duration=0)
        self.assertEqual(unpack_config(c.pack(),0),c)
        fine=GeneratorConfig(wave=1,mode=3,frequency=20525000,final_frequency=40750000,duration=750)
        self.assertEqual(unpack_config(fine.pack(),0),fine)
        for args in ({'frequency':20501000},{'duration':5001},{'final_frequency':20000000},{'frequency':1}):
            with self.assertRaises(ValueError):GeneratorConfig(**{**c.__dict__,**args})
