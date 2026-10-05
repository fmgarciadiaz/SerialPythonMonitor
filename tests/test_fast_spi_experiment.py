import subprocess,tempfile,unittest
from pathlib import Path
from experimentos.tasas_spi.receiver.unoq_acquisition import Configuration,acquisition_request,acquisition_reply
from experimentos.tasas_spi.receiver.unoq_config_decoder import ConfigurationDecoder
from transport.unoq_acquisition import Configuration as StableConfiguration
from test_acquisition_config import frame

ROOT=Path(__file__).resolve().parents[1]

class FastSPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        folder=Path(cls.tmp.name);cls.exe=folder/'firmware';cls.relay=folder/'relay'
        source=folder/'firmware.cpp'
        source.write_text('#include <cstdio>\n#include "acquisition_protocol.h"\n'
            'int main(){uint8_t p[512];scope_acq::Request r{};scope_acq::Settings s;'
            'if(fread(p,1,512,stdin)!=512||!scope_acq::decode(p,512,r))return 2;'
            'auto a=s.submit(r,true);scope_acq::encode(p,0,a);fwrite(p,1,512,stdout);'
            'if(s.pending()){scope_acq::encode(p,1,s.complete(true));fwrite(p,1,512,stdout);}return 0;}')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v9_fast/oscilloscope/sketch'),str(source),'-o',str(cls.exe)],check=True)
        source=folder/'relay.c'
        source.write_text('#define main verifier_main\n#include "diagnosticos/verificar_spi.c"\n#undef main\n'
            '#include "experimentos/tasas_spi/relay/config_relay_protocol.h"\n'
            'int main(int argc,char **argv){(void)argv;init_crc();DualChecker c={.period=32,.bits=14};uint8_t p[512];'
            'while(fread(p,1,512,stdin)==512)if(!(argc>1?dual_command(p):dual_feed(&c,p)))return 2;return 0;}')
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(source),'-lm','-o',str(cls.relay)],check=True)

    def test_high_rates_cross_firmware_relay_and_receiver(self):
        for bits in (8,10,12,14):
            for rate in (100000,125000,200000,250000):
                config=Configuration(bits,rate)
                out=subprocess.run([str(self.exe)],input=acquisition_request(0x80000100,config),capture_output=True,check=True).stdout
                packets=[out[:512],out[512:],frame(config,epoch=1,seq=2)]
                self.assertEqual(acquisition_reply(packets[1]).active,config)
                decoder=ConfigurationDecoder();samples=[]
                for packet in packets:samples+=decoder.feed(packet)
                self.assertEqual(len(samples),2)
                self.assertEqual(subprocess.run([str(self.relay)],input=b''.join(packets)).returncode,0)

    def test_stable_contract_and_oversampling_limits_unchanged(self):
        for rate in (100000,125000,200000,250000):
            with self.assertRaises(ValueError):StableConfiguration(14,rate)
            with self.assertRaises(ValueError):Configuration(16,rate)
        with self.assertRaises(ValueError):Configuration(16,62500)
        Configuration(16,50000)

    def test_fast_crc_keeps_iso_hdlc_wire_contract(self):
        import zlib
        folder=Path(self.tmp.name);source=folder/'crc.cpp';exe=folder/'crc'
        source.write_text('#include <cstdio>\n#include "benchmark_protocol.h"\n'
            'int main(){uint8_t p[4096];size_t n=fread(p,1,sizeof p,stdin);'
            'printf("%u",scope_bench::crc32(p,n));return 0;}')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT/'arduino/v9_fast/oscilloscope/sketch'),str(source),'-o',str(exe)],check=True)
        for data in (b'',b'123456789',bytes(range(256))*2):
            output=subprocess.run([str(exe)],input=data,capture_output=True,check=True).stdout
            self.assertEqual(int(output),zlib.crc32(data))

    def test_adc_has_timing_margin(self):
        for rate in (62500,100000,125000,200000,250000):
            c=Configuration(14,rate)
            self.assertLess(2*(c.sampling_cycles+17)/40,c.period)
