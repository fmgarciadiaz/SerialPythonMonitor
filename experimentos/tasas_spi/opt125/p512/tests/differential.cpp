#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
#include "../benchmark_protocol_baseline.h"
#define scope_bench optimized
#include "../oscilloscope/sketch/benchmark_protocol.h"
#undef scope_bench
using Frame=std::array<uint8_t,512>;
int main() {
 unsigned cases=0;
 const uint32_t sequences[]={0,1,255,256,65535,65536,0x7fffffff,0x80000000,0xfffffffe,0xffffffff};
 for(auto seq:sequences) {
  Frame a{},b{};
  scope_bench::frame(a.data(),scope_bench::PING,seq);scope_bench::seal(a.data());
  optimized::frame(b.data(),optimized::PING,seq);optimized::seal(b.data());
  assert(a==b);assert(optimized::valid_ping(b.data()));
  for(unsigned i=0;i<512;i++) {
   auto bad=a;bad[i]^=1;
   assert(scope_bench::valid_ping(bad.data())==optimized::valid_ping(bad.data()));
   assert(!optimized::valid_ping(bad.data()));++cases;
   if(i<508) {
    scope_bench::seal(bad.data()); // Semantic corruption with a valid CRC.
    assert(!scope_bench::valid_ping(bad.data()));assert(!optimized::valid_ping(bad.data()));++cases;
   }
  }
  for(unsigned count: {0u,1u,52u,53u}) {
   a.fill(0);b.fill(0);
   for(unsigned i=80;i<80+8*count;i++) a[i]=b[i]=uint8_t(i+seq);
   scope_bench::data_frame(a.data(),seq,seq-1,0,0,0,512,0,10,20);
   optimized::data_frame(b.data(),seq,seq-1,0,0,0,512,0,10,20);
   scope_bench::seal(a.data());optimized::seal(b.data());assert(a==b);
   assert(scope_bench::crc32(a.data(),508)==optimized::crc32(b.data(),508));
   for(unsigned i=80+8*count;i<508;i++) assert(b[i]==0);
   for(unsigned i=0;i<512;i++) {
    auto bad=a;bad[i]^=1;
    assert(scope_bench::crc32(bad.data(),508)==optimized::crc32(bad.data(),508));
    assert(optimized::get32(bad.data()+508)!=optimized::crc32(bad.data(),508));
   }
   ++cases;
  }
 }
 std::cout << cases << " differential cases passed\n";
}
