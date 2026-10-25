"""Full8 with portable slicing-by-eight CRC; identical wire checks and MCU."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent
OUT=EXP/'crc8'
def prepare():
    for name in ('oscilloscope','relay'):
        shutil.copytree(EXP/'full8'/name,OUT/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'full8/candidate_profiles.json',OUT/'candidate_profiles.json')
    p=OUT/'relay/base_verifier.c';s=p.read_text()
    s=s.replace('static uint32_t crc_table[256];','static uint32_t crc_table[256];\nstatic uint32_t crc_slices[8][256];')
    a=s.index('static void init_crc(void)');b=s.index('static uint8_t pattern',a)
    s=s[:a]+'''static void init_crc(void) {
    for(unsigned i=0;i<256;++i) {
        uint32_t c=i;
        for(unsigned j=0;j<8;++j)c=(c>>1)^((c&1)?UINT32_C(0xedb88320):0);
        crc_table[i]=crc_slices[0][i]=c;
    }
    for(unsigned slice=1;slice<8;++slice)
        for(unsigned i=0;i<256;++i) {
            uint32_t c=crc_slices[slice-1][i];
            crc_slices[slice][i]=(c>>8)^crc_table[c&255];
        }
}
static uint32_t crc32(const uint8_t *p,size_t n) {
    uint32_t c=UINT32_MAX;
    while(n>=8) {
        const uint32_t first=get32(p)^c,second=get32(p+4);
        c=crc_slices[7][first&255]^crc_slices[6][(first>>8)&255]^
          crc_slices[5][(first>>16)&255]^crc_slices[4][first>>24]^
          crc_slices[3][second&255]^crc_slices[2][(second>>8)&255]^
          crc_slices[1][(second>>16)&255]^crc_slices[0][second>>24];
        p+=8;n-=8;
    }
    while(n--)c=(c>>8)^crc_table[(c^*p++)&255];
    return c^UINT32_MAX;
}
'''+s[b:];p.write_text(s)
if __name__=='__main__':prepare()
