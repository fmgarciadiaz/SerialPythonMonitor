"""Relay-only TCP QUICKACK A/B; keep the exact BatchArena MCU application."""
import shutil
from pathlib import Path
EXP=Path(__file__).resolve().parent

def prepare():
    out=EXP/'batchquickack'
    for name in ('oscilloscope','relay'):
        shutil.copytree(EXP/'batcharena'/name,out/name,dirs_exist_ok=True)
    shutil.copyfile(EXP/'batcharena/candidate_profiles.json',out/'candidate_profiles.json')
    path=out/'relay/unoq_config_stream.c';source=path.read_text()
    anchor='            if (received>0) {\n'
    if source.count(anchor)!=1:raise ValueError('Unexpected relay source')
    source=source.replace(anchor,anchor+
        '                // Private A/B: acknowledge incoming PC commands promptly.\n'
        '                if(setsockopt(client,IPPROTO_TCP,TCP_QUICKACK,&one,sizeof one)<0) {\n'
        '                    perror("PC TCP_QUICKACK"); goto done;\n'
        '                }\n',1)
    path.write_text(source)

if __name__=='__main__':prepare()
