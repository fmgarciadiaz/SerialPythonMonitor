"""Execute accepted and candidate V19 state machines against the same traces."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.wav_validation_candidate_v19 import SKETCH, candidate_text

STUB = r'''
#include <cassert>
#include <cstdio>
#include "generator_protocol.h"
#include "wav_queue.h"
static unsigned depth=0;
static unsigned irq_lock(){assert(!depth);return depth++;}
static void irq_unlock(unsigned old){assert(depth==1);depth=old;}
namespace generator_hw {
static bool stop(unsigned){return true;}
static bool healthy(){return true;}
}
namespace generator {
static scope_gen::Config active=scope_gen::defaults();static bool running=true;
static void (*external_tick)()=nullptr;
static bool apply(scope_gen::Config c){active=c;running=c.enabled;return true;}
}
namespace wav_hw {
static int position=-1;
static unsigned publications=0;
static bool prepare(){position=-1;return true;}
static void descriptor(unsigned,bool){assert(depth==1);}
static void publish(unsigned slot,const uint8_t *p,unsigned n,bool){
 assert(depth==1);assert(slot<scope_wav::SLOTS);assert(n<=scope_wav::POINTS);
 if(position>=0){assert(slot!=unsigned(position));}
 for(unsigned i=0;i<n;++i)assert(scope_wav::get16(p+2*i)<=4095);
 ++publications;
}
static bool start(unsigned head){assert(depth==1);position=head;return true;}
static int current(){return position;}
static void clear_underrun(){}
static bool errors(){return false;}
}
#define WAV_TEST
#include "wav.h"
static uint8_t samples[scope_wav::POINTS*2]{};
static scope_wav::Reply send(unsigned id,unsigned session,unsigned op,unsigned total=0,
 unsigned offset=0,unsigned count=0,const uint8_t *p=nullptr,unsigned fingerprint=0){
 scope_wav::Request r{id,session,offset,total,fingerprint?fingerprint:id,
 uint16_t(count),uint8_t(op),bool(count),p,0};
 auto v=wav::submit(r);assert(depth==0);
 printf("%u %u %u %u %u %u\n",unsigned(v.state),unsigned(v.reason),
 unsigned(wav::queue.accepted),unsigned(wav::queue.played),wav::queue.used,wav_hw::publications);
 return v;
}
int main(){
 (void)&wav::service;
 assert(send(1,77,scope_wav::BEGIN,480*40+37).reason==scope_control::OK);
 // Invalid oversized count must remain BUSY without touching a null buffer.
 assert(send(2,77,0,0,0,481).reason==scope_control::BUSY);
 samples[1]=0x10;
 assert(send(3,78,0,0,0,480,samples).reason==scope_control::BUSY);
 assert(send(4,77,0,0,0,480,samples).reason==scope_control::UNSUPPORTED);
 samples[1]=0;
 // Dedup keeps the previous reason even when the payload memory changes.
 assert(send(4,77,0,0,0,480,samples).reason==scope_control::UNSUPPORTED);
 assert(send(4,77,0,0,0,480,samples,99).reason==scope_control::ID_CONFLICT);
 for(unsigned i=0;i<scope_wav::SLOTS;++i)
  assert(send(10+i,77,0,0,480*i,480,samples).reason==scope_control::OK);
 assert(send(50,77,0,0,480*30,480,samples).reason==scope_control::BUSY);
 assert(send(51,77,scope_wav::PLAY).state==scope_wav::PLAYING);
 for(unsigned i=0;i<11;++i){
  wav_hw::position=int((i+1)%scope_wav::SLOTS);
  assert(send(60+i,77,0,0,480*(30+i),i==10?37:480,samples).reason==scope_control::OK);
 }
 wav_hw::position=-2;
 assert(send(80,77,scope_wav::QUERY).state==scope_wav::DONE);
 assert(wav::queue.played==480*40+37);
 send(81,77,scope_wav::STOP);wav::service();assert(!wav::owned);
 assert(send(82,78,scope_wav::BEGIN,480*20).reason==scope_control::OK);
 for(unsigned i=0;i<4;++i)send(83+i,78,0,0,480*i,480,samples);
 send(90,78,scope_wav::PLAY);wav_hw::position=-2;
 assert(send(91,78,scope_wav::QUERY).state==scope_wav::UNDERRUN);
 send(92,78,scope_wav::STOP);wav::service();assert(!wav::owned);
}
'''

class WavValidationCandidateTests(unittest.TestCase):
    def test_identical_replies_ring_wrap_eof_and_underrun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            outputs=[]
            original=(SKETCH/'wav.h').read_text()
            for name,text in [('accepted',original),('candidate',candidate_text(original))]:
                folder=root/name
                shutil.copytree(SKETCH,folder)
                (folder/'wav.h').write_text(text)
                (folder/'test.cpp').write_text(STUB)
                exe=folder/'test'
                subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',
                                '-I',str(folder),str(folder/'test.cpp'),'-o',str(exe)],check=True)
                outputs.append(subprocess.check_output([str(exe)]))
            self.assertEqual(outputs[0],outputs[1])
            self.assertGreater(len(outputs[0].splitlines()),50)

    def test_rejects_changed_baseline(self):
        with self.assertRaises(ValueError):
            candidate_text((SKETCH/'wav.h').read_text().replace('r.count;++i','r.count; ++i'))
