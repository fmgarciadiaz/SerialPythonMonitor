"""Check the existing PING payload four bytes at once; no protocol changes."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'wordping'
def prepare():
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'crc8'/name,OUT/name,dirs_exist_ok=True)
 shutil.copyfile(EXP/'crc8/candidate_profiles.json',OUT/'candidate_profiles.json')
 p=OUT/'oscilloscope/sketch/benchmark_protocol.h';s=p.read_text()
 a=s.index('    const uint8_t s0 =',s.index('inline bool valid_ping'));b=s.index('    return true;',a)
 # Constants are the four original byte masks, packed little endian. A memcpy
 # load is alias-safe and valid even for an unaligned protocol pointer.
 masks=[]
 for i in range(0,972,4):masks.append(sum((((i+j)*17+0x5a)&255)<<(8*j) for j in range(4)))
 lines=['        '+','.join(f'0x{x:08x}U' for x in masks[i:i+8])+',' for i in range(0,len(masks),8)]
 replacement='''    static_assert(PAYLOAD_BYTES % 4 == 0, "PING groups require four bytes");
    static const uint32_t masks[PAYLOAD_BYTES/4]={
'''+ '\n'.join(lines)+'''
    };
    for(size_t i=0;i<PAYLOAD_BYTES/4;++i) {
        uint32_t actual;
        __builtin_memcpy(&actual,p+HEADER_BYTES+i*4,4);
        // SCP1 and the STM32 are little endian; host contract checks this too.
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
        actual=__builtin_bswap32(actual);
#endif
        if(actual!=(seed^masks[i]))return false;
    }
'''
 p.write_text(s[:a]+replacement+s[b:])
if __name__=='__main__':prepare()
