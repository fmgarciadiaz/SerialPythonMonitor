"""Prepare a private relay source copy. Does not connect, compile or deploy to Q."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def manifest(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file() and '.cache' not in p.parts}

def prepare(output=None):
    baseline=ROOT/'arduino/v18/relay';output=Path(output) if output else HERE/'candidate_v4'
    if output.exists():raise ValueError('Use a fresh output directory; existing candidate is preserved')
    shutil.copytree(baseline,output,ignore=shutil.ignore_patterns('.cache','__pycache__','.DS_Store'))
    shutil.copyfile(HERE/'telemetry.h',output/'telemetry.h')
    p=output/'unoq_config_stream.c';s=p.read_text()
    def replace(old,new):
        nonlocal s
        if s.count(old)!=1:raise ValueError('Baseline anchor mismatch: '+old[:70])
        s=s.replace(old,new,1)
    replace('#include "frame_send_queue.h"','#include "frame_send_queue.h"\n#include "telemetry.h"')
    replace('        scope_batch2_prepare_tx(tx,command,pc_command,pending); pending=false;',
            '        scope_diag_select(checker.bits,checker.mode,checker.period,checker.epoch);\n        scope_batch2_prepare_tx(tx,command,pc_command,pending); pending=false;')
    replace('        int ok=checker.have_sequence','        double ready_started=now();\n        int ok=checker.have_sequence')
    replace('        if (ok<0)', '        scope_diag_ready(ready_started,now());\n        if (ok<0)')
    replace('        previous_io=now();','        previous_io=now();\n        scope_diag_spi_begin(previous_io);')
    replace('        if (ioctl(fd,SPI_IOC_MESSAGE(1),&transfer)!=SCOPE_BATCH2_BYTES) { perror("SPI transfer"); goto done; }',
            '        int spi_result=ioctl(fd,SPI_IOC_MESSAGE(1),&transfer);\n        int spi_errno=errno;\n        scope_diag_spi_end(now(),spi_result==SCOPE_BATCH2_BYTES);\n        errno=spi_errno;\n        if (spi_result!=SCOPE_BATCH2_BYTES) { perror("SPI transfer"); goto done; }')
    replace('            goto done;\n        }\n        const ScopeNativeProfile *profile=', '            scope_diag_report("integrity_failure");\n            goto done;\n        }\n        const ScopeNativeProfile *profile=')
    replace('                    if(scope_send_frame(&send_queue,client,frame,send)<0)sent=-1;', '''                    scope_diag_backlog(send_queue.count<SCOPE_SEND_SLOTS?send_queue.count+1:send_queue.count);
                    if(send_queue.count==SCOPE_SEND_SLOTS)++scope_diag.queue_full;
                    if(scope_send_frame(&send_queue,client,frame,scope_diag_send)<0)sent=-1;''')
    replace('} else sent=send(client,frame,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL);','} else sent=scope_diag_send(client,frame,BLOCK,MSG_DONTWAIT|MSG_NOSIGNAL);')
    # Do not print extra diagnostics on client failure: acquisition continues.
    # Keep existing progress output unchanged; diagnostics print only at failure/exit.
    replace('done:\n','done:\n    scope_diag_report("exit");\n')
    p.write_text(s)
    (output.parent/(output.name+'.manifest.json')).write_text(json.dumps(dict(private=True,deployed=False,
        baseline=manifest(baseline),candidate=manifest(output),firmware_changed=False,
        policy_changed=False,measurement_scope='monotonic maxima and TCP counters; not scheduler attribution'),indent=2)+'\n')
    return output

if __name__=='__main__':print(prepare())
