#include <cassert>
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
std::vector<uint32_t> waveform;
inline bool init(){return true;}
inline bool healthy(){return true;}
inline bool pulse_finished(){return false;}
inline bool stop(uint16_t){return true;}
inline bool pulse(uint16_t,uint16_t,uint32_t){return true;}
inline void set_timing(generator::Timing){}
inline bool start(uint32_t* values,unsigned n,generator::Timing){waveform.assign(values,values+n);return true;}
}
#include "../oscilloscope/sketch/generator.h"
int main(){
 auto c=scope_gen::defaults();c.frequency=5000000;c.low=1000;c.high=3000;
 for(unsigned duty: {1,25,50,75,99}){
  c.duty=duty;assert(generator::apply(c));
  unsigned n=duty==50?2:100;assert(generator_hw::waveform.size()==n);
  unsigned on=duty==50?1:duty;
  for(unsigned i=0;i<n;++i)assert(generator_hw::waveform[i]==(i<on?3000:1000));
 }
 c.frequency=50000000;c.duty=1;assert(generator::apply(c));
 assert(generator_hw::waveform.size()==20);
 assert(generator_hw::waveform[0]==3000);
 for(unsigned i=1;i<20;++i)assert(generator_hw::waveform[i]==1000);
}
