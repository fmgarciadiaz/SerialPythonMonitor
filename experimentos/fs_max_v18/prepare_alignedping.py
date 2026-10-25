"""Use alias-safe aligned word loads for the real aligned SPI receive buffer."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent;OUT=EXP/'alignedping'
def prepare():
 for name in ('oscilloscope','relay'):shutil.copytree(EXP/'wordping'/name,OUT/name,dirs_exist_ok=True)
 shutil.copyfile(EXP/'wordping/candidate_profiles.json',OUT/'candidate_profiles.json')
 p=OUT/'oscilloscope/sketch/benchmark_protocol.h';s=p.read_text()
 marker='    for(size_t i=0;i<PAYLOAD_BYTES/4;++i) {'
 assert s.count(marker)==1
 s=s.replace(marker,'''#if defined(__GNUC__) && __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    typedef uint32_t AliasWord __attribute__((may_alias));
    const uint8_t *payload=p+HEADER_BYTES;
    if((reinterpret_cast<uintptr_t>(payload)&3U)==0) {
        const AliasWord *words=reinterpret_cast<const AliasWord *>(payload);
        for(size_t i=0;i<PAYLOAD_BYTES/4;++i)
            if(words[i]!=(seed^masks[i]))return false;
        return true;
    }
#endif
'''+marker,1);p.write_text(s)
if __name__=='__main__':prepare()
