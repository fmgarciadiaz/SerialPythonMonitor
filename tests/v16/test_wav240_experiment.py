import subprocess,tempfile,unittest
from pathlib import Path
from tests.v13.test_wav_firmware import STUB
ROOT=Path(__file__).resolve().parents[2]
SKETCH=ROOT/'experimentos/synth_wav240/oscilloscope/sketch'

class Wav240ExperimentTests(unittest.TestCase):
    def test_guarded_ring_wrap_short_final_tail_and_old_block_rejected(self):
        stub=STUB.replace('480','240').replace('960','480')
        code=r'''
int main(){
static_assert(scope_wav::POINTS==240,"short blocks");
assert(command(1,77,1,240*20+37).state==scope_wav::BUFFERING);
assert(chunk(2,0,480).reason!=0);
for(unsigned i=0;i<16;++i)assert(chunk(3+i,i*240).reason==0);
assert(!wav::queue.free());assert(command(19,77,2).state==scope_wav::PLAYING);
for(unsigned i=0;i<5;++i){wav_hw::position=(i+1)%16;wav::poll();
assert(wav_hw::guards[i]);assert(chunk(20+i,(16+i)*240,i==4?37:240).reason==0);}
wav_hw::position=-2;wav::poll();assert(wav::queue.state==scope_wav::DONE);
assert(wav::queue.played==240*20+37);wav::service();
command(30,77,1,240*10);for(unsigned i=0;i<4;++i)chunk(31+i,i*240);
assert(command(35,77,2).state==scope_wav::PLAYING);
wav_hw::position=3;wav::poll();assert(wav::queue.state==scope_wav::UNDERRUN);
assert(generator_hw::level==2048);assert(chunk(36,4*240).reason!=0);
command(37,77,3);wav::service();assert(!wav::owned);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);src=path/'wav.cpp';exe=path/'wav'
            src.write_text('#include "generator_protocol.h"\n'+stub+code)
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(SKETCH),str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
