"""Private TCP write coalescing; unchanged validated SCP1 byte stream."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
HEADER=r'''#pragma once
/* Only an empty FIFO can take the pair fast path. Partial bytes are retained. */
static int scope_send_pair(struct ScopeSendQueue *q,int fd,const uint8_t *frames,ScopeSendCall call) {
    if(q->count || q->offset) {errno=EINVAL;return -1;}
    ssize_t n=call(fd,frames,1984U,MSG_DONTWAIT|MSG_NOSIGNAL);
    if(n==1984)return 0;
    if(n==0 || n>1984) {errno=EIO;return -1;}
    if(n<0) {
        if(errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR)return -1;
        n=0;
    }
    if(n>=992) {
        memcpy(q->frames[q->head],frames+992,992);
        q->count=1;q->offset=(unsigned)n-992U;
    } else {
        memcpy(q->frames[q->head],frames,992);
        memcpy(q->frames[(q->head+1U)%SCOPE_SEND_SLOTS],frames+992,992);
        q->count=2;q->offset=(unsigned)n;
    }
    return 0;
}
'''


def instrument(text):
    before='#include "frame_send_queue.h"'
    if text.count(before)!=1:raise ValueError('Unique send queue include required')
    text=text.replace(before,before+'\n#include "pair_send.h"',1)
    before='''            // Validation of both halves already committed before either is sent.
            for (unsigned half=0;half<2;++half) {'''
    after='''            // Both halves have already passed the unchanged atomic validator.
            if(cpu && !send_queue.count) {
                if(scope_send_pair(&send_queue,client,rx,send)<0) {
                    fprintf(stderr,"PC disconnected or too slow during pair send\\n");
                    close(client);client=-1;
                }
            } else for (unsigned half=0;half<2;++half) {'''
    if text.count(before)!=1:raise ValueError('Unique validated send loop required')
    return text.replace(before,after,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();source=args.source.resolve();out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'diagnosticos/resultados_v19') or not source.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private output and private source required')
    shutil.copytree(source,out)
    f=out/'unoq_config_stream.c';f.write_text(instrument(f.read_text()))
    (out/'pair_send.h').write_text(HEADER)
    (out.parent/'source_manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
