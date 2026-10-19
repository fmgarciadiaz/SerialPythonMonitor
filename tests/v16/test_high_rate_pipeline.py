"""Run the actual producer handoff and completion code with a slow DMA consumer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SKETCH = Path(__file__).resolve().parents[2]/'arduino/v16/oscilloscope/sketch/sketch.ino'

class PipelineTests(unittest.TestCase):
    def test_frame_scratch_is_aligned_and_outside_dma_nodes(self):
        sketch=SKETCH.read_text()
        header=(SKETCH.parent/'frame_buffer.h').read_text()
        body=header[header.index('struct SampleFrame {'):].replace('scope_bench::BLOCK_BYTES','BLOCK_BYTES')+sketch[sketch.index('static SampleFrame ordinary_frame;'):sketch.index('static SampleFrame *sample_ready')]
        code="""#include <cstdint>
#include <new>
#include <cassert>
#include <cstring>
constexpr unsigned BLOCK_BYTES=992,FRAME_SLOTS=3,CONFIG_DCACHE_LINE_SIZE=32;
namespace scope_storage {struct SingleMemory {uint32_t timestamps[16384];};}
namespace acquisition {alignas(32) uint32_t ts[16384];uint32_t *timestampBuffer=ts;unsigned timestamp_storage_bytes(){return sizeof ts;}}
BODY
int main(){
 for(auto &word:acquisition::ts)word=0x13579bdf;
 auto *a=frame_slot(0),*b=frame_slot(1),*c=frame_slot(2);
 assert(reinterpret_cast<uintptr_t>(b)%32==0 && reinterpret_cast<uintptr_t>(c)%32==0);
 assert(b!=c && a!=b && a!=c);
 memset(a->bytes,0x11,992);memset(b->bytes,0x22,992);memset(c->bytes,0x33,992);
 for(unsigned i=0;i<15888;++i)assert(acquisition::ts[i]==0x13579bdf);
 for(unsigned i=0;i<992;++i)assert(a->bytes[i]==0x11 && b->bytes[i]==0x22 && c->bytes[i]==0x33);
}
""".replace('BODY',body)
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'scratch.cpp';src.write_text(code);exe=src.with_suffix('')
            subprocess.run(['c++','-std=c++17',str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)

    def test_ownership_order_tails_and_control_delays(self):
        sketch = SKETCH.read_text()
        producer = sketch[sketch.index('const bool pipelined=high_rate_transport();'):sketch.index('        acquisition::release();')].rsplit('        }',1)[0]
        complete = '    if(have_samples && ready) k_sem_give(&frame_sent);'
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
struct FrameRef {SampleFrame *frame;bool last,pipelined;};
struct Queue {std::mutex m;std::condition_variable cv;std::deque<FrameRef> refs;};
int k_msgq_put(Queue *q,const FrameRef *r,int){std::lock_guard<std::mutex> l(q->m);assert(q->refs.size()<FRAME_SLOTS);q->refs.push_back(*r);q->cv.notify_one();return 0;}
FrameRef pop(Queue *q){std::unique_lock<std::mutex> l(q->m);q->cv.wait(l,[&]{return !q->refs.empty();});auto r=q->refs.front();q->refs.pop_front();return r;}
Sem frame_available,frame_sent;SampleFrame *sample_ready[FRAME_SLOTS];SampleFrame sample_frames[FRAME_SLOTS];
SampleFrame *frame_slot(unsigned slot){return &sample_frames[slot];}
bool ready=true;
namespace acquisition {struct Node{unsigned index;};unsigned bits,pairs,period;bool native(){return true;}bool single(){return true;}unsigned node_pairs(){return pairs;}void fail(){assert(false);}}
bool high_rate_transport(){return acquisition::bits==8 && acquisition::pairs==3456 && acquisition::period==114;}
std::atomic<unsigned> prepared{0};
void build_samples(unsigned *bytes,acquisition::Node *node,unsigned offset,unsigned count){
 for(unsigned i=0;i<864;++i)bytes[i]=i<count?node->index*100000+offset+i:0xffffffff;
 ++prepared;
}
int main(){
 struct Case {unsigned bits,pairs,ticks;};
 for(Case c: {Case{8,3456,114},Case{8,6912,131},Case{10,8192,176},Case{14,7936,214},Case{8,3456,114}}){
  const unsigned bits=c.bits,pairs=c.pairs;acquisition::period=c.ticks;
  acquisition::bits=bits;acquisition::pairs=pairs;frame_available.count=0;frame_sent.count=0;prepared=0;unsigned read_frame=0;
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
    const bool pipelined=high_rate_transport();
    k_sem_take(&frame_available,K_FOREVER);
    FrameRef sample{};
    sample.frame=pipelined?sample_ready[read_frame]:frame_slot(0);
    if(pipelined)read_frame=(read_frame+1U)%FRAME_SLOTS;
    sample.last=offset+(bits==8?864U:bits==10?696U:496U)>=pairs;
    const bool have_samples=true;
    const unsigned count=min(bits==8?864U:bits==10?696U:496U,pairs-offset);
    auto *buffer=sample.frame->bytes;unsigned snapshot[864];std::memcpy(snapshot,buffer,sizeof snapshot);
    // First DMA waits for producer to demonstrate real overlap and exhausted credits.
    if(!received && high_rate_transport()){while(prepared.load()<FRAME_SLOTS)std::this_thread::yield();assert(prepared.load()==FRAME_SLOTS);}
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
  producer.join();assert(released==20);assert(frame_available.count==0);assert(frame_sent.count==0);
 }
 // A failed transfer must retain its credit and withhold the final-node ACK.
 ready=false;frame_sent.count=0;
 const bool have_samples=true,pipelined=true;FrameRef sample{&sample_frames[0],true,true};
 COMPLETE
 assert(frame_sent.count==0);
}
'''.replace('PRODUCER',producer).replace('COMPLETE',complete)
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'pipeline.cpp';src.write_text(source)
            exe=src.with_suffix('')
            subprocess.run(['c++','-O2','-std=c++17','-pthread',str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True,timeout=20)

if __name__=='__main__':unittest.main()
