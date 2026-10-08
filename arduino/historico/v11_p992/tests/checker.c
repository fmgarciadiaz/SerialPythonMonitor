#define main baseline_main
#include "../relay/base_verifier.c"
#undef main
#include "../relay/config_relay_protocol.h"
int main(void) {
 uint8_t p[BLOCK]; init_crc();
 while(fread(p,1,BLOCK,stdin)==BLOCK) {
  DualChecker d={.period=8,.bits=14};
  bool ok=get16(p+6)==2 || get16(p+6)==4 || get16(p+6)==6 || get16(p+6)==8 || get16(p+6)==10 ? dual_command(p) : dual_feed(&d,p);
  printf("%d\n",ok);
 }
}
