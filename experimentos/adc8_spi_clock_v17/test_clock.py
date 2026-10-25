import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from experimentos.adc8_spi_clock_v17.run import nss_summary


class ClockTests(unittest.TestCase):
    def test_actual_pair_statistics_keep_negative_residuals(self):
        s=(Path(__file__).parent/'arduino/historico/v16/relay/unoq_config_stream.c').read_text()
        helper=s[s.index('struct NssStats'):s.index('static void prof_dump')]
        code='#include <stdint.h>\n#include <assert.h>\n'+helper+'''
int main(void) {
 record_nss(16000,120000);record_nss(16000,90000);
 assert(nss_stats.count==2 && nss_stats.negative==1);
 assert(nss_stats.outside_ns==10000);
 assert(nss_stats.outside_min==-10000 && nss_stats.outside_max==20000);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.c';p.write_text(code);binary=Path(folder)/'test'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)

    def test_selected_windows_only(self):
        rows=[dict(start_s=i,end_s=i+10,count=2,nss_ticks=32000,ioctl_ns=210000,
            outside_ns=10000,nss_min_ticks=16000,nss_max_ticks=16000,
            outside_min_ns=-10000,outside_max_ns=20000,mismatched=0,negative=1)
            for i in (0,10,20)]
        log='\n'.join('PROFILE_NSS '+json.dumps(r) for r in rows)
        d=nss_summary(log,[dict(start_s=10,end_s=20),dict(start_s=20,end_s=30)])
        self.assertEqual(d['count'],4)
        self.assertEqual(d['negative'],2)
        self.assertEqual(d['nss_mean_us'],100)
        self.assertEqual(d['estimated_outside_mean_us'],5)
        self.assertEqual(d['estimated_outside_min_us'],-10)


if __name__=='__main__':unittest.main()
