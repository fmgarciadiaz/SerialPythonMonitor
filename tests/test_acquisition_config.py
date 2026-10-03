import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from test_spi_native import adc_frame
from transport.unoq_acquisition import Configuration, BITS, RATES, UART_RATES, acquisition_request, acquisition_reply
from transport.unoq_config_decoder import ConfigurationDecoder
from transport.unoq_config_receiver import LegacyDecoder
from transport.unoq_usb import ProtocolError
from transport.unoq_switch import Phase

ROOT=Path(__file__).resolve().parents[1]

def frame(config,epoch=1,index=0,count=2,seq=2):
    p=adc_frame(seq=seq,index=index,count=count,timestamp=0)
    struct.pack_into('<I',p,48,config.rate)
    p[66]=config.bits
    struct.pack_into('<I',p,68,config.period)
    struct.pack_into('<I',p,76,epoch<<1)
    for i in range(count): struct.pack_into('<IHH',p,80+i*8,(index+i)*config.period,config.maximum,1)
    struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
    return bytes(p)

class AcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        source=Path(cls.tmp.name)/'acq.cpp';cls.exe=Path(cls.tmp.name)/'acq'
        source.write_text('#include <cstdio>\n#include "acquisition_protocol.h"\n'
            'int main(){ uint8_t p[512];scope_acq::Request r{};scope_acq::Settings s;'
            'if(fread(p,1,512,stdin)!=512 || !scope_acq::decode(p,512,r))return 2;'
            'auto emit=[&](scope_acq::Reply v,unsigned seq){scope_acq::encode(p,seq,v);fwrite(p,1,512,stdout);};'
            'emit(s.submit(r,true),0);if(s.pending()){emit(s.complete(true),1);emit(s.submit(r,true),2);}'
            'return 0;}')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'transport'),str(source),'-o',str(cls.exe)],check=True)
        source=Path(cls.tmp.name)/'relay.c';cls.relay=Path(cls.tmp.name)/'relay'
        source.write_text('#define main verifier_main\n#include "diagnosticos/verificar_spi.c"\n#undef main\n'
            '#include "transport/config_relay_protocol.h"\n'
            'int main(int argc,char **argv){(void)argv;init_crc();DualChecker c={.period=32,.bits=14};uint8_t p[512];'
            'while(fread(p,1,512,stdin)==512)if(!(argc>1?dual_command(p):dual_feed(&c,p)))return 2;return 0;}')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(source),'-lm','-o',str(cls.relay)],check=True)

    def replies(self,config):
        result=subprocess.run([str(self.exe)],input=acquisition_request(0x80000100,config),capture_output=True,check=True)
        return [result.stdout[i:i+512] for i in range(0,len(result.stdout),512)]

    def test_all_profiles_cross_language_and_dynamic_metadata(self):
        for bits in BITS:
            for rate in RATES:
                with self.subTest(bits=bits,rate=rate):
                    if bits==16 and rate>50000:
                        with self.assertRaises(ValueError):Configuration(bits,rate)
                        continue
                    config=Configuration(bits,rate); replies=self.replies(config)
                    self.assertEqual(acquisition_reply(replies[0]).phase,Phase.ACCEPTED)
                    self.assertEqual(acquisition_reply(replies[1]).active,config)
                    self.assertEqual(acquisition_reply(replies[2]).epoch,1)
                    packets=replies[:2]+[frame(config)]
                    decoder=ConfigurationDecoder();samples=decoder.feed(b''.join(packets))
                    self.assertEqual(samples[1][0]-samples[0][0],config.period)
                    self.assertEqual(samples[0][1],config.maximum)
                    self.assertEqual(subprocess.run([str(self.relay)],input=b''.join(packets)).returncode,0)

    def test_periods_and_bandwidth_preserve_wire_format(self):
        for rate in RATES:
            self.assertEqual(1000000%rate,0)
            if rate in UART_RATES: self.assertLess(rate*4103*10/512,3000000)
        for bits,rate in ((16,62500),(14,30000),(14,33333),(14,100000),(7,1000)):
            with self.assertRaises(ValueError):Configuration(bits,rate)
        self.assertGreater(Configuration(8,1000).sample_timeout,4)

    def test_real_mcu_rejects_invalid_period_and_reserved_fields(self):
        p=bytearray(acquisition_request(0x80000100,Configuration()))
        struct.pack_into('<I',p,20,33);struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
        result=subprocess.run([str(self.exe)],input=p,capture_output=True,check=True)
        self.assertEqual(acquisition_reply(result.stdout).phase,Phase.REJECTED)
        p[17]=1;struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
        self.assertNotEqual(subprocess.run([str(self.exe)],input=p).returncode,0)

    def test_mcu_rejects_oversampling_above_conversion_budget(self):
        p=bytearray(acquisition_request(0x80000100,Configuration(16,12500)))
        struct.pack_into('<I',p,20,16)
        struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
        result=subprocess.run([str(self.exe)],input=p,capture_output=True,check=True)
        self.assertEqual(acquisition_reply(result.stdout).phase,Phase.REJECTED)
        # Relay forwards valid requests; MCU owns profile rejection.
        self.assertEqual(subprocess.run([str(self.relay),'command'],input=p).returncode,0)
        self.assertEqual(subprocess.run([str(self.relay)],input=result.stdout).returncode,0)

    def test_old_epoch_range_and_period_corruption_are_rejected(self):
        config=Configuration(8,10000);accepted,applied,_=self.replies(config)
        variants=[]
        for offset,value in ((76,0),(68,32),(80+4,256)):
            p=bytearray(frame(config))
            struct.pack_into('<H' if offset==84 else '<I',p,offset,value)
            struct.pack_into('<I',p,508,zlib.crc32(p[:508]));variants.append(bytes(p))
        for packet in variants:
            with self.assertRaises(ProtocolError):ConfigurationDecoder().feed(accepted+applied+packet)
            self.assertNotEqual(subprocess.run([str(self.relay)],input=accepted+applied+packet).returncode,0)

    def test_uart_decoder_uses_hardware_bits_and_period(self):
        config=Configuration(8,1000)
        raw=b'DATA'+struct.pack('<BH',1,512)+b''.join(struct.pack('<IHH',i*1000,255,0) for i in range(512))
        self.assertEqual(len(LegacyDecoder(config).feed(raw)[0]),512)
        with self.assertRaises(ProtocolError):LegacyDecoder().feed(raw)

    def test_cached_applied_ack_does_not_restart_sample_timeline(self):
        config=Configuration(10,12500)
        accepted,applied,cached=self.replies(config)
        cached=bytearray(cached);struct.pack_into('<I',cached,8,3)
        struct.pack_into('<I',cached,508,zlib.crc32(cached[:508]))
        stream=accepted+applied+frame(config,seq=2)+bytes(cached)+frame(config,index=2,seq=4)
        self.assertEqual(len(ConfigurationDecoder().feed(stream)),4)
        self.assertEqual(subprocess.run([str(self.relay)],input=stream).returncode,0)

class FastSPIProfiles(unittest.TestCase):
    def test_window_profile_and_uart_guard(self):
        from transport.unoq_config_receiver import OutputReceiver
        from transport.unoq_switch import Mode
        from unittest.mock import MagicMock
        for rate,cycles in ((2000,391),(12500,68),(15625,36),(20000,36),(25000,20),(31250,20),(40000,12),(50000,5)):
            profile=Configuration(16,rate)
            self.assertEqual(profile.sampling_cycles,cycles)
            self.assertLess(32*(cycles+17)/40,profile.period)
        self.assertEqual(Configuration(14,40000).sampling_cycles,391)
        self.assertEqual(Configuration(14,50000).sampling_us,1.7)
        receiver=OutputReceiver(MagicMock(),lambda samples:None)
        receiver.config=Configuration(14,62500)
        with self.assertRaises(ValueError):receiver.select(Mode.UART,'r4')
