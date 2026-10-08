"""Cross-language frames and guarded streaming with the actual MCU state machine."""
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np
from monitor.historico.v13.receiver import unoq_wav as wav

ROOT=Path(__file__).resolve().parents[2]
SKETCH=ROOT/'arduino/v12_audio/oscilloscope/sketch'
STUB=r'''
#include <cassert>
#include <cstdio>
#include "wav_queue.h"
static unsigned irq_lock(){return 0;}static void irq_unlock(unsigned){}
namespace generator_hw { static unsigned level=0;static bool stop(unsigned n){level=n;return true;}static bool healthy(){return true;} }
namespace generator {
static scope_gen::Config active=scope_gen::defaults();static bool running=true;
static void (*external_tick)()=nullptr;
static bool apply(scope_gen::Config c){active=c;running=c.enabled;return true;}
}
namespace wav_hw {
static int position=-1;static bool bad=false,stream=false;
static bool guards[17];static uint16_t codes[16][480];
static bool prepare(){for(bool &g:guards)g=true;stream=false;position=-1;return true;}
static void descriptor(unsigned slot,bool guard){guards[slot]=guard;}
static void publish(unsigned slot,const uint8_t *p,unsigned n,bool){
    if(stream && position>=0) { assert(int(slot)!=position);assert(int(slot)!=(position+1)%16); }
    for(unsigned i=0;i<n;++i)codes[slot][i]=scope_wav::get16(p+2*i);guards[slot]=false;
}
static bool start(unsigned head){position=head;stream=true;return true;}
static int current(){return position;}
static void clear_underrun(){}
static bool errors(){return bad;}
}
#define WAV_TEST
#include "wav.h"
static scope_wav::Reply command(uint32_t id,uint32_t session,uint8_t op,uint32_t total=0) {
    (void)&wav::service;
    scope_wav::Request r{id,session,0,total,id,0,op,false,nullptr,0};return wav::submit(r);
}
static scope_wav::Reply chunk(uint32_t id,uint32_t offset,unsigned count=480,uint32_t session=77) {
    static uint8_t samples[960]{};
    scope_wav::Request r{id,session,offset,0,id,uint16_t(count),0,true,samples,0};return wav::submit(r);
}
'''

class WavFirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder=Path(cls.tmp.name)
        cls.relay=cls.folder/'checker'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(ROOT/'arduino/v12_audio/tests/checker.c'),'-lm','-o',str(cls.relay)],check=True)
    def run_cpp(self,code):
        source=self.folder/'wav.cpp';exe=self.folder/'wav'
        source.write_text('#include "generator_protocol.h"\n'+STUB+code)
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(SKETCH),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    def test_monotonic_ownership_ring_wrap_and_final_tail(self):
        self.run_cpp(r'''
int main(){
assert(command(1,77,1,480*20+37).state==scope_wav::BUFFERING);
for(unsigned i=0;i<16;++i)assert(chunk(2+i,i*480).reason==0);
assert(!wav::queue.free());assert(command(18,77,2).state==scope_wav::PLAYING);
for(unsigned i=0;i<5;++i){wav_hw::position=(i+1)%16;wav::poll();assert(wav_hw::guards[i]);
 assert(chunk(19+i,(16+i)*480,i==4?37:480).reason==0);}
assert(wav::queue.accepted==wav::queue.total);
// Prefetched/current and following slots were never reused by the producer.
wav_hw::position=-2;wav::poll();assert(wav::queue.state==scope_wav::DONE);
assert(wav::queue.played==480*20+37);assert(generator_hw::level==2048);
wav::service();assert(!wav::owned);assert(generator::external_tick==nullptr);
assert(!generator::running);assert(!generator::active.enabled);
}
''')
    def test_underrun_neutral_and_explicit_stop_silence(self):
        self.run_cpp(r'''
int main(){command(1,77,1,480*10);for(unsigned i=0;i<4;++i)chunk(2+i,i*480);
command(6,77,2);wav_hw::position=3;wav::poll();
assert(wav::queue.state==scope_wav::UNDERRUN);assert(generator_hw::level==2048);
assert(wav::owned);assert(chunk(7,4*480).reason!=0);
command(8,77,3);wav::service();assert(!wav::owned);assert(!generator::running);assert(!generator::active.enabled);
}
''')
    def test_guard_terminal_handles_delayed_supervisor(self):
        self.run_cpp(r'''
int main(){command(1,77,1,480*100);for(unsigned i=0;i<4;++i)chunk(2+i,i*480);
command(6,77,2);assert(wav_hw::guards[4]);
// Unqueued descriptor has neutral fixed source and a terminal link, so no stale
// circular replay is possible even if software misses every block transition.
wav_hw::position=-2;wav::poll();assert(wav::queue.state==scope_wav::UNDERRUN);
assert(generator_hw::level==2048);
}
''')
    def test_duplicates_offsets_and_busy_generator(self):
        self.run_cpp(r'''
int main(){command(1,77,1,1000);assert(chunk(2,0).reason==0);
assert(chunk(2,0).accepted==480);assert(chunk(3,0).reason!=0);
assert(chunk(4,480,100).reason!=0);assert(chunk(5,480,480,78).reason!=0);
assert(chunk(6,480).reason==0);assert(chunk(7,960,40).reason==0);
assert(command(8,77,2).state==scope_wav::PLAYING);
assert(chunk(9,1000,1).reason!=0);assert(command(10,78,3).reason!=0);
}
''')
    def test_python_frames_firmware_and_relay_cross_language(self):
        source=self.folder/'decode.cpp';exe=self.folder/'decode'
        source.write_text(r'''
#include <cstdio>
#include "wav_protocol.h"
int main(){uint8_t p[992];scope_wav::Request r{};while(fread(p,1,992,stdin)==992){
if(!scope_wav::decode(p,992,r))return 2;
scope_wav::Reply reply{r.id,r.session,scope_wav::BUFFERING,0,16,0,0,r.total};
scope_wav::encode(p,0,reply);fwrite(p,1,992,stdout);} }
''')
        subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(SKETCH),str(source),'-o',str(exe)],check=True)
        frames=[wav.command(0x80000001,77,1,1000,40000),wav.command(0x80000003,77,1,1000,50000),wav.chunk(0x80000002,77,0,np.arange(480,dtype=np.uint16))]
        for frame in frames:
            packet=subprocess.run([str(exe)],input=frame,capture_output=True,check=True).stdout
            self.assertEqual(wav.status(packet).state,wav.State.BUFFERING)
            for checked in [frame,packet]:
                self.assertEqual(subprocess.run([str(self.relay)],input=checked,capture_output=True,check=True).stdout,b'1\n')
        corrupt=bytearray(frames[0]);corrupt[20]^=1
        self.assertNotEqual(subprocess.run([str(exe)],input=corrupt,capture_output=True).returncode,0)

    def test_negotiated_rate_acceptance_and_rejection(self):
        self.run_cpp(r'''
int main(){
 (void)&chunk;
 scope_wav::Request r{1,77,0,1000,1,0,scope_wav::BEGIN,false,nullptr,40000};
 assert(wav::submit(r).reason==0);assert(scope_wav::active_rate==40000);
 command(2,77,3);wav::service();
 r.id=3;r.fingerprint=3;r.rate=50000;
 assert(wav::submit(r).reason==0);assert(scope_wav::active_rate==50000);
 command(4,77,3);wav::service();
 r.id=5;r.fingerprint=5;r.rate=44100;
 assert(wav::submit(r).reason!=0);assert(scope_wav::active_rate==50000);
}
''')
