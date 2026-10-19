#include <cassert>
#include <cstdio>
#include <vector>
#define GENERATOR_TEST
#define CONFIG_SYS_CLOCK_TICKS_PER_SEC 10000
#define K_TICKS(x) (x)
struct k_timer {};
inline unsigned irq_lock(){return 0;}
inline void irq_unlock(unsigned){}
inline long long k_uptime_ticks(){return 0;}
template<class... Args> void k_timer_init(Args...){}
template<class... Args> void k_timer_start(Args...){}
#include "../oscilloscope/sketch/generator_timing.h"
namespace generator_hw {
static bool healthy_flag=true;
static uint16_t level=0;
static unsigned starts=0;
static std::vector<uint32_t> waveform;
static generator::Timing clock;
inline bool init(){return true;}
inline bool healthy(){return healthy_flag;}
inline bool pulse_finished(){return false;}
inline bool stop(uint16_t n){level=n;return true;}
inline bool pulse(uint16_t,uint16_t,uint32_t){return true;}
inline void set_timing(generator::Timing){}
inline bool start(uint32_t *data,unsigned count,generator::Timing t){
 waveform.assign(data,data+count);clock=t;++starts;return true;
}
}
#include "radio_test_backend.h"
#include "../oscilloscope/sketch/generator.h"
int main(){
 scope_gen::Config c{1,1,3,20525000,40750000,800,3300,750};
 assert(scope_gen::valid(c));assert(generator::apply(c));
 assert(generator::running && !generator::faulted);
 assert(generator_hw::waveform.size()==5120);
 assert(generator_hw::clock.prescaler==0 && generator_hw::clock.reload==1249);
 const auto before=generator_hw::waveform;
 assert(generator::apply(c));assert(generator_hw::starts==1);
 for(unsigned tick=0;tick<2000;++tick)generator::tick(nullptr);
 assert(generator_hw::waveform==before && generator_hw::starts==1);
 for(unsigned i=0;i<radio_test::RATE;++i){
  const auto value=generator_hw::waveform[i%radio_test::POINTS];
  assert(value>=c.low && value<=c.high);std::printf("%u\n",value);
 }
 // Exactly one period: every accepted oscillator returns to its initial phase.
 assert(radio_test::sample(c,0,generator::sine)==radio_test::sample(c,5120,generator::sine));
 c.frequency=750000;c.duration=0;assert(generator::apply(c));
 assert(generator_hw::starts==2);
 generator_hw::healthy_flag=false;generator::tick(nullptr);
 assert(!generator::running && generator::faulted && generator_hw::level==0);
 generator_hw::healthy_flag=true;c.enabled=0;assert(generator::apply(c));
 assert(!generator::running && !generator::faulted);
 generator_hw::level=2048;assert(generator::apply(c));assert(generator_hw::level==0);
 generator::external_tick=[](){};
 scope_gen::Request request{0x80000001U,c,false};
 assert(generator::submit(request).reason==scope_control::BUSY);
}
