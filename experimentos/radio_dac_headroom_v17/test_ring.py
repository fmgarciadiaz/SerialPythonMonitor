"""Actual 30-slot MCU queue and state machine, using deterministic DMA positions."""
import subprocess,tempfile,unittest
from pathlib import Path
from tests.v13.test_wav_firmware import STUB
ROOT=Path(__file__).resolve().parents[2]
STUB=STUB.replace('guards[17]','guards[scope_wav::SLOTS+1]').replace('codes[16][480]','codes[scope_wav::SLOTS][scope_wav::POINTS]').replace('%16','%scope_wav::SLOTS')
class RingTests(unittest.TestCase):
 def run_cpp(self,body):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);src=p/'ring.cpp';src.write_text('#include "generator_protocol.h"\n'+STUB+body)
   subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'experimentos/radio_dac_headroom_v17/oscilloscope/sketch'),str(src),'-o',str(p/'ring')],check=True)
   subprocess.run([str(p/'ring')],check=True)
 def test_full_ring_multiple_wraps_tail_and_restore(self):
  self.run_cpp(r'''
int main(){constexpr unsigned slots=scope_wav::SLOTS;static_assert(slots==30,"capacity");
 unsigned id=1;const unsigned total=480*slots*3+37;
 assert(command(id++,77,1,total).state==scope_wav::BUFFERING);
 for(unsigned i=0;i<slots;++i)assert(chunk(id++,i*480).reason==0);
 assert(wav::queue.free()==0);assert(command(id++,77,2).state==scope_wav::PLAYING);
 while(wav::queue.accepted<total){wav_hw::position=(wav::queue.head+1)%slots;wav::poll();
  const unsigned count=total-wav::queue.accepted<480?total-wav::queue.accepted:480;
  assert(chunk(id++,wav::queue.accepted,count).reason==0);}
 wav_hw::position=-2;wav::poll();assert(wav::queue.state==scope_wav::DONE);
 assert(wav::queue.played==total);wav::service();assert(!wav::owned);assert(!generator::active.enabled);
}
''')
 def test_underrun_retains_neutral_and_rejects_late_chunk(self):
  self.run_cpp(r'''
int main(){command(1,77,1,480*100);for(unsigned i=0;i<4;++i)chunk(2+i,i*480);
 assert(command(6,77,2).state==scope_wav::PLAYING);
 wav_hw::position=3;wav::poll();assert(wav::queue.state==scope_wav::UNDERRUN);
 assert(generator_hw::level==2048);assert(chunk(7,4*480).reason!=0);
 command(8,77,3);wav::service();assert(!wav::owned);assert(!generator::running);
}
''')
if __name__=='__main__':unittest.main()
