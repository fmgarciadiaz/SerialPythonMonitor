#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "../oscilloscope/sketch/benchmark_protocol.h"
#include "../oscilloscope/sketch/acquisition_protocol.h"
#include "../oscilloscope/sketch/generator_protocol.h"
int main(int argc,char **) {
 if(argc>1) {
  uint8_t command[992];
  while(fread(command,1,992,stdin)==992) {
   scope_control::Request t{};scope_acq::Request a{};scope_gen::Request g{};
   bool ok=scope_bench::valid_ping(command) || scope_control::decode(command,992,t) || scope_acq::decode(command,992,a) || scope_gen::decode(command,992,g);
   printf("%d\n",ok);
  }
  return 0;
 }

 uint8_t p[992];
 scope_bench::frame(p,2,0x80000001);scope_bench::seal(p);fwrite(p,1,992,stdout);
 for(unsigned count: {113u,14u}) {
  memset(p,0,992);scope_bench::data_frame(p,0,0x80000001,0,0,0,992);
  scope_bench::put16(p+6,3);scope_bench::put32(p+48,125000);
  scope_bench::put16(p+64,count);p[66]=14;p[67]=2;scope_bench::put32(p+68,8);
  for(unsigned i=0;i<count;i++){scope_bench::put32(p+80+8*i,i*8);scope_bench::put16(p+84+8*i,123);scope_bench::put16(p+86+8*i,456);}
  scope_bench::seal(p);fwrite(p,1,992,stdout);
 }
 scope_control::Reply transport{0x80000001,0,0,2,0,0};scope_control::encode(p,0,transport);fwrite(p,1,992,stdout);
 scope_acq::Reply acquisition{0x80000001,14,14,2,0,8,8,1};scope_acq::encode(p,0,acquisition);fwrite(p,1,992,stdout);
 auto cfg=scope_gen::defaults();scope_gen::Reply generator{0x80000001,2,0,0,cfg,cfg};scope_gen::encode(p,0,generator);fwrite(p,1,992,stdout);
}
