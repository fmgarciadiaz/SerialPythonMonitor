"""Run the actual producer handoff and completion code with a slow DMA consumer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SKETCH = Path(__file__).resolve().parent/'arduino/v16/oscilloscope/sketch/sketch.ino'

class PipelineTests(unittest.TestCase):
    def test_ownership_order_tails_and_control_delays(self):
        sketch = SKETCH.read_text()
        producer = sketch[sketch.index('            for (unsigned offset'):sketch.index('        acquisition::release();')].replace('        }\n        k_sem_take', '        k_sem_take')
        complete = sketch[sketch.index('    if (have_samples && ready) {'):sketch.index('    // Idle status traffic')]
        source = r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <mutex>
#include <thread>
using std::min;
constexpr int K_FOREVER=1,K_NO_WAIT=0;
constexpr unsigned FRAME_SLOTS=3;
struct Sem {std::mutex m;std::condition_variable cv;int count=0;};
void k_sem_take(Sem *s,int){std::unique_lock<std::mutex> l(s->m);s->cv.wait(l,[&]{return s->count>0;});--s->count;}
void k_sem_give(Sem *s){std::lock_guard<std::mutex> l(s->m);++s->count;s->cv.notify_one();}
struct SampleFrame {unsigned bytes[864];};
struct FrameRef {SampleFrame *frame;bool last;};
struct Queue {std::mutex m;std::condition_variable cv;std::deque<FrameRef> refs;};
int k_msgq_put(Queue *q,const FrameRef *r,int){std::lock_guard<std::mutex> l(q->m);assert(q->refs.size()<FRAME_SLOTS);q->refs.push_back(*r);q->cv.notify_one();return 0;}
FrameRef pop(Queue *q){std::unique_lock<std::mutex> l(q->m);q->cv.wait(l,[&]{return !q->refs.empty();});auto r=q->refs.front();q->refs.pop_front();return r;}
Sem frame_free,frame_sent;Queue sample_ready;SampleFrame sample_frames[FRAME_SLOTS];
bool ready=true;
namespace acquisition {struct Node{unsigned index;};unsigned bits,pairs;unsigned node_pairs(){return pairs;}void fail(){assert(false);}}
std::atomic<unsigned> prepared{0};
void build_samples(unsigned *bytes,acquisition::Node *node,unsigned offset,unsigned count){
 for(unsigned i=0;i<864;++i)bytes[i]=i<count?node->index*100000+offset+i:0xffffffff;
 ++prepared;
}
int main(){
 for(unsigned bits:{8U,10U,12U})for(unsigned pairs:{3456U,6912U,8192U}){
  acquisition::bits=bits;acquisition::pairs=pairs;frame_free.count=FRAME_SLOTS;frame_sent.count=0;prepared=0;
  std::atomic<unsigned> completed_nodes{0},released{0};
  std::thread producer([&]{unsigned next_frame=0;
   for(unsigned n=0;n<20;++n){acquisition::Node owned{n};auto *node=&owned;
PRODUCER
    assert(completed_nodes.load()==n+1);++released;
   }
  });
  unsigned received=0;
  for(unsigned n=0;n<20;++n){
   for(unsigned offset=0;offset<pairs;){
    auto sample=pop(&sample_ready);const bool have_samples=true;
    const unsigned count=min(bits==8?864U:bits==10?696U:496U,pairs-offset);
    auto *buffer=sample.frame->bytes;unsigned snapshot[864];std::memcpy(snapshot,buffer,sizeof snapshot);
    // First DMA waits for producer to demonstrate real overlap and exhausted credits.
    if(!received){while(prepared.load()<FRAME_SLOTS)std::this_thread::yield();assert(prepared.load()==FRAME_SLOTS);}
    // Emulate DMA ownership and periodic control replies before the next transfer.
    std::this_thread::sleep_for(std::chrono::microseconds(received%7?40:200));
    assert(!std::memcmp(snapshot,buffer,sizeof snapshot));
    for(unsigned i=0;i<864;++i)assert(buffer[i]==(i<count?n*100000+offset+i:0xffffffff));
    offset+=count;assert(sample.last==(offset==pairs));
    assert(released.load()<=n);
    if(sample.last)++completed_nodes;
COMPLETE
    ++received;
   }
  }
  producer.join();assert(released==20);assert(sample_ready.refs.empty());assert(frame_free.count==FRAME_SLOTS);assert(frame_sent.count==0);
 }
 // A failed transfer must retain its credit and withhold the final-node ACK.
 ready=false;frame_free.count=FRAME_SLOTS-1;frame_sent.count=0;
 const bool have_samples=true;FrameRef sample{&sample_frames[0],true};
 COMPLETE
 assert(frame_free.count==FRAME_SLOTS-1);assert(frame_sent.count==0);
}
'''.replace('PRODUCER',producer).replace('COMPLETE',complete)
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'pipeline.cpp';src.write_text(source)
            exe=src.with_suffix('')
            subprocess.run(['c++','-O2','-std=c++17','-pthread',str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True,timeout=20)

if __name__=='__main__':unittest.main()
