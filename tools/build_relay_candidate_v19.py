#!/usr/bin/env python3
"""Build a private V19 relay with the Q stopped, then restore the accepted pair."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import signal
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monitor.v19.q_support.prepare import Journal,_require,atomic_report,load_acceptance,rollback_once,source_changes
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.relay_identity import relay_sources

CANDIDATE=ROOT/'diagnosticos/resultados_v19/prepare_q_20261027/candidate/relay'
BUILD_IMAGE='debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a'


def build(backend,sources,output):
    """No app import/start, firmware build or production cache write here."""
    backend._require_stopped_original()
    board=backend._board();stage='/tmp/v19-relay-candidate-'+backend.token
    container='v19-relay-build-'+backend.token
    backend._candidate_compile_cleared=True
    paths=relay_sources(sources)
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError('Regular relay sources required')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output.mkdir(parents=True,exist_ok=True)
    try:
        board.shell('mkdir','-p',stage)
        for path in paths:board.run('push',str(path),stage+'/'+path.name)
        backend._require_stopped_original()
        command=['docker','run','--rm','--name',container,'--cpus','0.5','--memory','768m',
            '--pids-limit','128','--user','0:0','--security-opt','no-new-privileges',
            '--mount',f'type=bind,src={stage},dst=/build','--entrypoint','sh',BUILD_IMAGE,'-c',
            'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev '
            '&& cc -O2 -std=c11 -Wall -Wextra -Werror /build/unoq_config_stream.c -lm -o /build/relay-candidate.bin']
        with (output/'build.log').open('w') as log:
            backend._candidate_compile_cleared=False
            subprocess.run([board.adb,'-s',board.serial,'shell',shlex.join(command)],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
        binary=output/'relay-candidate.bin'
        board.run('pull',stage+'/relay-candidate.bin',str(binary))
        data=binary.read_bytes()
        if data[:6]!=b'\x7fELF\x02\x01' or int.from_bytes(data[18:20],'little')!=183:
            raise RuntimeError('Expected Linux ELF64 aarch64 relay')
        if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}:
            raise RuntimeError('Candidate sources changed during build')
        return dict(path=str(binary),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),
                    source_directory=str(sources.resolve()),
                    architecture='ELF64 aarch64',sources=hashes,compiler_image=BUILD_IMAGE,
                    compiled_with_pair_stopped=True,installed=False)
    finally:
        # Only this invocation's unique compiler container and stage are owned.
        names=backend._output('docker','ps','-a','--format','{{.Names}}').splitlines()
        if container in names:board.shell('docker','rm','-f',container)
        if container in backend._output('docker','ps','-a','--format','{{.Names}}').splitlines():
            raise RuntimeError('Compiler container still exists; do not restart acquisition')
        backend._candidate_compile_cleared=True
        board.shell('python3','-c','import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)',stage)


def execute_build(backend,acceptance,sources,output,report,save,builder=build,operation_name='build'):
    journal=Journal(report,save);baseline=backup=changes=None;dirty=False
    report.update(ok=False,candidate_installed=False,state_uncertain=False)
    with backend.owner():
        try:
            qualification=journal.step('preflight',lambda:backend.preflight(acceptance))
            _require(qualification,('production_backend_qualified','rollback_rehearsal_verified',
                                    'cached_launcher_verified'),'Qualified backend')
            baseline=journal.step('capture',backend.capture)
            _require(baseline,('generator_off','wav_idle','receiver_closed','identity_verified',
                               'source_manifest_verified'),'Accepted baseline')
            report['baseline']=baseline
            if any(baseline.get('identity',{}).get(key)!=value
                   for key,value in acceptance['candidate_identity'].items()):
                raise RuntimeError('Only the currently accepted pair may enter this build rehearsal')
            backup=journal.step('backup',lambda:backend.backup(baseline))
            _require(backup,('export_verified','source_archive_verified','full_cache_verified',
                            'firmware_elf_bin_verified','relay_verified','paired_manifest_persisted'),'Exact paired backup')
            report['backup']=backup
            changes=source_changes(baseline['app_sources'],baseline['app_sources'])
            dirty=True;report['state_uncertain']=True
            for name,args in (('quiesce',(baseline,)),('stop_old_relay',(baseline,)),
                              ('rename_old_relay',(baseline,)),('stop_app',())):
                journal.step(name,lambda name=name,args=args:getattr(backend,name)(*args))
            report['artifact']=journal.step(operation_name,lambda:builder(backend,sources,output))
        except BaseException as exc:
            report['error']=repr(exc)
        finally:
            report['restoring']=dirty
            if dirty:
                if getattr(backend,'_candidate_compile_cleared',None) is False:
                    report['restoration']=dict(ok=False,errors=['Compiler stop not confirmed; accepted pair remains stopped'],
                                               backup=backup)
                else:
                    report['restoration']=rollback_once(backend,baseline,backup,None,changes,journal)
                report['state_uncertain']=not report['restoration']['ok']
            report['restoring']=False
            report['ok']=bool(report.get('artifact') and report.get('restoration',{}).get('ok') and not report.get('error'))
            save()
    return report['ok']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sources',type=Path,default=CANDIDATE)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists():parser.error('--output must be a new directory')
    if not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Keep candidate evidence under diagnosticos/resultados_v19')
    sources=args.sources.resolve()
    if not sources.is_dir() or not sources.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Private source directory required under diagnosticos/resultados_v19')
    output.mkdir(parents=True)
    report=dict(schema=1,version=19,purpose='private relay build and exact production restoration')
    save=lambda:atomic_report(output/'report.json',report)
    save()
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    def interrupted(*_):
        if report.get('restoring'):return
        raise KeyboardInterrupt('Candidate build cancelled; restoring Q')
    for sig in previous:signal.signal(sig,interrupted)
    try:
        acceptance=load_acceptance(RECEIPT);backend=ProductionBackend(acceptance)
        backend._board().serial=args.serial
        ok=execute_build(backend,acceptance,sources,output,report,save)
    except BaseException as exc:
        report.update(ok=False,error=repr(exc));save();ok=False
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,output=str(output),error=report.get('error'),
                         restored=report.get('restoration',{}).get('ok')),indent=2))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
