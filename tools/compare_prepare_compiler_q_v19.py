#!/usr/bin/env python3
"""Compile Os/O2 with the accepted Q compiler; never install either candidate."""
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
from tools.compare_prepare_compiler_v19 import ANCHOR
from tools.build_relay_candidate_v19 import execute_build
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.prepare import atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.q_support.board import source_files

REMOTE=r'''
import json,os,pathlib,subprocess,sys
stage=pathlib.Path(sys.argv[1]);jobs=[]
def run(args,destination):
    with destination.open('w') as log:
        child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs.append(dict(pid=child.pid,start=0))
        (stage/'jobs.json').write_text(json.dumps(jobs))
        try:
            fields=pathlib.Path('/proc/%s/stat'%child.pid).read_text().rsplit(')',1)[1].split()
            jobs[-1]['start']=int(fields[19])
            (stage/'jobs.json').write_text(json.dumps(jobs))
        except FileNotFoundError:pass
        result=child.wait()
        if result:raise RuntimeError('Command failed (%s): %s'%(result,destination))
work=stage/'work'/'sketch';common=['arduino-cli','compile','--fqbn','arduino:zephyr:unoq','--profile','default']
run(common+['--build-path',str(stage/'properties_build'),'--show-properties=expanded',str(work)],stage/'properties.txt')
props=dict(s.split('=',1) for s in (stage/'properties.txt').read_text().splitlines() if '=' in s)
prefix=props['build.compiler_path']+'arm-zephyr-eabi-'
run([prefix+'g++','--version'],stage/'compiler_version.txt')
if '14.3.0' not in (stage/'compiler_version.txt').read_text():raise RuntimeError('Expected accepted GCC14.3.0')
if props.get('compiler.cpp.extra_flags',''):raise RuntimeError('Existing extra flags must not be overwritten')
ino=work/'sketch.ino';base=ino.read_text();anchor=sys.argv[2]
if base.count(anchor)!=1:raise RuntimeError('Unique Os anchor required')
for name,opt in [('control_os','Os'),('candidate_o2','O2')]:
    print('Compiling '+name,flush=True)
    folder=stage/name;folder.mkdir()
    text=base if opt=='Os' else base.replace(anchor,anchor.replace('"Os"','"O2"'))
    ino.write_text(text);(folder/'sketch.ino').write_text(text)
    run(common+['--build-path',str(folder/'build'),'--clean','--jobs','2','--build-property',
                'compiler.cpp.extra_flags=-fstack-usage -fdump-ipa-cgraph','--verbose',str(work)],folder/'build.log')
    build=folder/'build';elf=build/'sketch.ino.elf';obj=build/'sketch'/'sketch.ino.cpp.o'
    for label,target in [('module',elf),('sketch_object',obj),('debug',build/'sketch.ino_debug.elf')]:
        for suffix,tool,flags in [('sizes','size',['-A']),('sections','readelf',['-SW']),
                                  ('relocations','readelf',['-rW']),('symbols','nm',['-S','--size-sort','-C'])]:
            run([prefix+tool]+flags+[str(target)],folder/(label+'_'+suffix+'.txt'))
    run([prefix+'objdump','-drC',str(obj)],folder/'sketch_disassembly.txt')
    su=list(build.rglob('*.su'));graphs=list(build.rglob('*.cgraph'))
    if not su or not graphs:raise RuntimeError('Missing stack/callgraph metadata')
    (folder/'stack_usage.txt').write_text('\n'.join(p.read_text() for p in su))
print('Both isolated compiler variants complete',flush=True)
'''

CLEANUP=r'''
import json,os,pathlib,signal,sys,time
stage=pathlib.Path(sys.argv[1]);path=stage/'jobs.json'
jobs=json.loads(path.read_text()) if path.exists() else []
def members(pid):
    found=[]
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]!='Z' and int(fields[2])==pid and int(fields[3])==pid:
                found.append((int(entry.name),(entry/'cmdline').read_bytes(),int(fields[19])))
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return found
for job in jobs:
    pid=job['pid'];live=members(pid)
    if not live:continue
    if not any(str(stage).encode() in cmd for _,cmd,_ in live) or any(start<job['start'] for _,_,start in live):
        raise RuntimeError('Compiler group ownership uncertain; leave pair stopped')
    for sig,seconds in [(signal.SIGTERM,3),(signal.SIGKILL,3)]:
        try:os.killpg(pid,sig)
        except ProcessLookupError:pass
        deadline=time.monotonic()+seconds
        while members(pid) and time.monotonic()<deadline:time.sleep(.05)
        if not members(pid):break
    if members(pid):raise RuntimeError('Compiler group remains active')
print(json.dumps(dict(compiler_idle=True)))
'''


def compare(backend,sources,output):
    backend._require_stopped_original()
    board=backend._board();stage='/tmp/v19-prepare-ab-'+backend.token
    backend._candidate_compile_cleared=True
    files=source_files(sources);hashes={p.relative_to(sources).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    try:
        board.shell('mkdir','-p',stage+'/work/sketch')
        for p in files:
            target=stage+'/work/sketch/'+p.relative_to(sources).as_posix()
            board.shell('mkdir','-p',target.rsplit('/',1)[0]);board.run('push',str(p),target)
        backend._require_stopped_original();backend._candidate_compile_cleared=False
        with (output/'comparison.log').open('w') as log:
            subprocess.run([board.adb,'-s',board.serial,'shell',shlex.join(['python3','-u','-c',REMOTE,stage,ANCHOR])],
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        for name in ('control_os','candidate_o2','properties.txt','compiler_version.txt'):
            board.run('pull',stage+'/'+name,str(output/name))
        if hashes!={p.relative_to(sources).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:
            raise RuntimeError('Original sketch sources changed')
        return dict(compiled_with_pair_stopped=True,firmware_installed=False,
                    sources=hashes,compiler=(output/'compiler_version.txt').read_text(),
                    variants={name:dict(elf_sha256=hashlib.sha256((output/name/'build/sketch.ino.elf').read_bytes()).hexdigest(),
                                       bin_sha256=hashlib.sha256((output/name/'build/sketch.ino.bin').read_bytes()).hexdigest())
                              for name in ('control_os','candidate_o2')})
    finally:
        result=board.shell('python3','-c',CLEANUP,stage,capture=True)
        if json.loads(result.stdout).get('compiler_idle') is not True:raise RuntimeError('Compiler idle not verified')
        backend._candidate_compile_cleared=True
        board.shell('python3','-c','import shutil,sys;shutil.rmtree(sys.argv[1])',stage)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Use new private diagnostic directory')
    output.mkdir(parents=True);report=dict(private=True,promoted=False,firmware_installed=False)
    save=lambda:atomic_report(output/'report.json',report);save()
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def interrupted(*_):
        if report.get('restoring'):return
        raise KeyboardInterrupt('Compiler comparison cancelled; restoring accepted pair')
    for sig in previous:signal.signal(sig,interrupted)
    ok=False
    try:
        acceptance=load_acceptance(RECEIPT)
        app=ROOT/'arduino/v19/oscilloscope'
        hashes={p.relative_to(app).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files(app)}
        if hashes!=acceptance['sources']['app']:raise RuntimeError('Accepted local sources required')
        backend=ProductionBackend(acceptance);backend._board().serial=args.serial
        ok=execute_build(backend,acceptance,ROOT/'arduino/v19/oscilloscope/sketch',output,report,save,
                         builder=compare,operation_name='compiler_comparison')
    except BaseException as exc:
        report.update(ok=False,error=repr(exc));save()
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,restored=report.get('restoration',{}).get('ok'),error=report.get('error'))))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
