#include <cassert>
#include <cstdio>
#include <initializer_list>
#include "generator_timing.h"
int main() {
 auto c=scope_gen::defaults();
 for(unsigned wave: {0U,1U}) {
  c.wave=wave;
  for(unsigned milli_hz: {50001000U,62500000U,73333000U,87500000U,112500000U,123456000U,137500000U,149999000U,150000000U,175000000U,199999000U,200000000U}) {
   c.frequency=c.final_frequency=milli_hz;
   if(milli_hz>scope_gen::waveform_limit(c.wave)){assert(!scope_gen::valid(c));continue;}
   assert(scope_gen::valid(c));
   auto n=generator::points_for(c);
   assert(n>=2 && uint64_t(milli_hz)*n<=uint64_t(scope_gen::UPDATE_HZ)*1000);
   auto t=generator::timing(milli_hz,n);
   double actual=double(generator::DAC_TIMER_HZ)/(unsigned(t.prescaler)+1)/(unsigned(t.reload)+1)/n;
   printf("%u,%.3f,%u,%.6f,%.6f\n",wave,milli_hz/1000.,n,actual,100*(actual/(milli_hz/1000.)-1));
  }
 }
 // Sweep point count must be chosen for the highest endpoint.
 c.wave=1;c.mode=1;c.frequency=62500000;c.final_frequency=150000000;
 assert(scope_gen::valid(c));assert(generator::points_for(c)==6);
 c.frequency=150000000;c.final_frequency=62500000;
 assert(generator::points_for(c)==6);
}
