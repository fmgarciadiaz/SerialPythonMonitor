#include <cassert>
#include <cstdio>
#include <initializer_list>
#include "generator_timing.h"
int main() {
 auto c=scope_gen::defaults();
 for(unsigned wave=0;wave<5;++wave) {
  c.wave=wave;
  for(unsigned hz: {50000U,100000U,150000U,200000U}) {
   c.frequency=c.final_frequency=hz*1000;
   bool expected=hz<=50000 || (wave==0&&hz<=200000) || (wave==1&&hz<=150000);
   assert(scope_gen::valid(c)==expected);
   if(!expected)continue;
   auto n=generator::points_for(c);assert(uint64_t(c.frequency)*n<=uint64_t(scope_gen::UPDATE_HZ)*1000);
   auto t=generator::timing(c.frequency,n);
   double actual=double(generator::DAC_TIMER_HZ)/(unsigned(t.prescaler)+1)/(unsigned(t.reload)+1)/n;
   std::printf("%u,%u,%u,%.6f,%.6f\n",wave,hz,n,actual,100*(actual/hz-1));
  }
 }
}
