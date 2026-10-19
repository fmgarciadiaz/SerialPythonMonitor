import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CODE=r'''
#include <cassert>
#include <cstdint>
#include "wav_storage.h"
int main(){
 wav_storage::Memory memory;
 static_assert(sizeof(memory)==28800,"30 PCM blocks share less RAM than 16 word blocks");
 static_assert(wav_storage::WAVEFORM_POINTS>=5120,"Radio Test table still fits");
 for(unsigned turn=0;turn<20;++turn){
  auto *pcm=wav_storage::begin_pcm(memory);
  for(unsigned i=0;i<wav_storage::PCM_POINTS;++i)pcm[i]=(i*37+turn)&4095;
  for(unsigned i=0;i<wav_storage::PCM_POINTS;++i)assert(pcm[i]==((i*37+turn)&4095));
  auto *wave=wav_storage::begin_waveform(memory);
  for(unsigned i=0;i<wav_storage::WAVEFORM_POINTS;++i)wave[i]=(i*71+turn)&4095;
  for(unsigned i=0;i<wav_storage::WAVEFORM_POINTS;++i)assert(wave[i]==((i*71+turn)&4095));
 }
}
'''
class StorageTests(unittest.TestCase):
 def test_exclusive_union_lifetimes_and_full_ranges(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);src=p/'storage.cpp';src.write_text(CODE)
   subprocess.run(['c++','-O2','-std=c++17','-fsanitize=address,undefined','-Wall','-Wextra','-Werror','-I',str(ROOT/'experimentos/radio_dac_headroom_v17/oscilloscope/sketch'),str(src),'-o',str(p/'storage')],check=True)
   subprocess.run([str(p/'storage')],check=True)
if __name__=='__main__':unittest.main()
