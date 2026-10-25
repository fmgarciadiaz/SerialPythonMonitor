import json
import unittest
from pathlib import Path
import subprocess
import tempfile
from experimentos.adc8_relay_profile_v17.run import summarize,NAMES


class RelayProfileTests(unittest.TestCase):
    def test_actual_c_counters_and_json(self):
        source=(Path(__file__).parent/'arduino/historico/v16/relay/unoq_config_stream.c').read_text()
        helpers=source[source.index('struct StageStats'):source.index('static volatile sig_atomic_t')]
        code='''#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#define SCOPE_STAGE_PROFILE 1
#define BLOCK 992
static double now(void) { static double t=0; return t+=0.000001; }
'''+helpers+'''
int main(void) {
 prof_call(6,0,-1,EAGAIN);prof_call(6,0,-1,EINTR);prof_call(6,0,-1,EBADF);
 prof_call(7,0,3,0);prof_call(8,0,992,0);prof_call(8,0,12,0);prof_dump();
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'check.c';p.write_text(code)
            binary=Path(directory)/'check'
            subprocess.run(['cc','-std=c11',str(p),'-o',str(binary)],check=True,capture_output=True)
            result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
        rows=[json.loads(l[len('PROFILE_RELAY '):]) for l in result.stderr.splitlines()]
        self.assertEqual(len(rows),9)
        self.assertEqual((rows[6]['count'],rows[6]['again'],rows[6]['interrupted'],rows[6]['errors']),(3,1,1,1))
        self.assertEqual((rows[7]['success'],rows[7]['bytes']),(1,0))
        self.assertEqual((rows[8]['bytes'],rows[8]['short_count']),(1004,1))

    def test_weighting_counters_and_incomplete_window(self):
        lines=[]
        for start,count,total in ((0,10,9000000),(10,20,20000),(20,10,30000),(30,10,9000000)):
            for i in range(len(NAMES)-(1 if start==30 else 0)):
                lines.append('PROFILE_RELAY '+json.dumps(dict(stage=i,start_s=start,
                    end_s=start+10,count=count,sum_ns=total,max_ns=3000,
                    success=0,again=count,interrupted=0,errors=0,bytes=0,short_count=0)))
        result=summarize('\n'.join(lines))
        self.assertEqual(len(result),9)
        self.assertEqual(result['recv']['count'],30)
        self.assertEqual(result['recv']['again'],30)
        self.assertAlmostEqual(result['recv']['mean_us'],50000/30/1000)
        self.assertEqual(result['recv']['maximum_us'],3)

    def test_no_measurement_from_only_startup(self):
        lines=['PROFILE_RELAY '+json.dumps(dict(stage=i,start_s=0,end_s=10,
            count=1,sum_ns=1,max_ns=1,success=1,again=0,interrupted=0,
            errors=0,bytes=0,short_count=0)) for i in range(9)]
        self.assertEqual(summarize('\n'.join(lines)),{})


if __name__=='__main__':unittest.main()
