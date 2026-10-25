#include <cassert>
#include <initializer_list>
#include "../oscilloscope/sketch/generator_timing.h"
int main() {
 auto c=scope_gen::defaults();
 for(unsigned wave=0;wave<4;++wave) {
  c.wave=wave;
  for(unsigned mode=0;mode<3;++mode) {
   c.mode=mode;
   for(uint32_t f: {100U,20000000U,40000000U,50000000U}) {
    c.frequency=f;c.final_frequency=50000000;
    assert(scope_gen::valid(c));
    unsigned n=generator::points_for(c);
    uint32_t maximum=mode?50000000:f;
    assert(uint64_t(maximum)*n<=uint64_t(scope_gen::UPDATE_HZ)*1000);
    auto t=generator::timing(maximum,n);
    double actual=double(generator::DAC_TIMER_HZ)/(unsigned(t.prescaler)+1)/(unsigned(t.reload)+1)/n;
    assert(actual>0);
    if(maximum==50000000) assert(actual==50000);
   }
  }
 }
 c.wave=0;c.mode=0;c.duty=25;c.frequency=5000000;
 assert(scope_gen::valid(c));assert(generator::points_for(c)==100);
 c.frequency=50000000;assert(generator::points_for(c)==20);
 auto square=generator::timing(c.frequency,generator::points_for(c));
 assert(double(generator::DAC_TIMER_HZ)/(square.prescaler+1)/(square.reload+1)/20==50000);
 c.mode=1;assert(!scope_gen::valid(c));
 c.mode=0;c.duty=0;assert(!scope_gen::valid(c));
 c.duty=100;assert(!scope_gen::valid(c));c.duty=50;
 c.wave=1;c.mode=0;c.frequency=40000000;
 assert(generator::points_for(c)==16);
 c.frequency=50000000;assert(generator::points_for(c)==16);
 c.frequency=50000001;assert(!scope_gen::valid(c));
}
