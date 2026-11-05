#!/usr/bin/env python3
"""Local-only Os/O2 build comparison. Never invokes ADB, upload, or Q apps."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monitor.v19.q_support.prepare import atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.q_support.board import source_files

ANCHOR='__attribute__((optimize("Os")))\n#endif\n// A batch is always two logical SCP1 frames.'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(command,path,timeout=60):
    with path.open('w') as log:
        subprocess.run([str(x) for x in command],stdout=log,stderr=subprocess.STDOUT,
                       check=True,timeout=timeout)
    return path.read_text()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cli',type=Path,default=Path('/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli'))
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Keep private evidence under diagnosticos/resultados_v19')
    if (output/'report.json').exists() or (output/'work').exists():parser.error('New comparison required')
    output.mkdir(parents=True,exist_ok=True)
    report=dict(private=True,installed=False,promoted=False,local_only=True,hardware_used=False,ok=False,variants={})
    save=lambda:atomic_report(output/'report.json',report)
    src=ROOT/'arduino/v19/oscilloscope'
    files=source_files(src);original={p.relative_to(src).as_posix():digest(p) for p in files}
    try:
        acceptance=load_acceptance(RECEIPT)
        if original!=acceptance['sources']['app']:raise RuntimeError('Current firmware sources differ from accepted receipt')
        report['source_sha256']=original;save()
        work=output/'work'/'sketch'
        shutil.copytree(src/'sketch',work,ignore=shutil.ignore_patterns('build','.cache','__pycache__'))
        ino=work/'sketch.ino';text=ino.read_text()
        if text.count(ANCHOR)!=1:raise RuntimeError('Exactly one prepare_batch_half Os anchor required')
        report['cli_version']=capture([args.cli,'version'],output/'cli_version.txt')
        common=[args.cli,'compile','--fqbn','arduino:zephyr:unoq','--profile','default']
        props=capture(common+['--build-path',output/'property_build','--show-properties=expanded',work],output/'properties.txt')
        properties=dict(line.split('=',1) for line in props.splitlines() if '=' in line)
        compiler=Path(properties['build.compiler_path'])/'arm-zephyr-eabi-g++'
        prefix=compiler.parent/'arm-zephyr-eabi-'
        report['compiler_version']=capture([compiler,'--version'],output/'compiler_version.txt')
        report['properties_sha256']=digest(output/'properties.txt')
        flags='-fstack-usage -fdump-ipa-cgraph'
        if properties.get('compiler.cpp.extra_flags',''):
            raise RuntimeError('Do not overwrite existing C++ extra flags')
        report['metadata_flags']=flags;save()
        for name,option in (('control_os','Os'),('candidate_o2','O2')):
            folder=output/name;folder.mkdir()
            variant=text if option=='Os' else text.replace(ANCHOR,ANCHOR.replace('"Os"','"O2"'))
            ino.write_text(variant);(folder/'sketch.ino').write_text(variant)
            changes=[i for i,(a,b) in enumerate(zip(text,variant)) if a!=b]
            if option=='O2' and (len(variant)!=len(text) or len(changes)!=1):
                raise RuntimeError('Candidate must differ by precisely one optimization character')
            entry=report['variants'][name]=dict(optimization=option,source_sha256=digest(ino),build_ok=False)
            save()
            command=common+['--build-path',folder/'build','--clean','--jobs','2',
                            '--build-property','compiler.cpp.extra_flags='+flags,'--verbose',work]
            entry['command']=[str(x) for x in command];save()
            capture(command,folder/'build.log',timeout=900)
            build=folder/'build';elf=build/'sketch.ino.elf';debug=build/'sketch.ino_debug.elf'
            obj=build/'sketch'/'sketch.ino.cpp.o'
            if not elf.is_file() or not obj.is_file():raise RuntimeError('Required ELF/object missing')
            for label,target in (('module',elf),('sketch_object',obj),('debug',debug)):
                if not target.exists():continue
                capture([str(prefix)+'size','-A',target],folder/(label+'_sizes.txt'))
                capture([str(prefix)+'readelf','-SW',target],folder/(label+'_sections.txt'))
                capture([str(prefix)+'readelf','-rW',target],folder/(label+'_relocations.txt'))
                capture([str(prefix)+'nm','-S','--size-sort','-C',target],folder/(label+'_symbols.txt'))
            capture([str(prefix)+'objdump','-drC',obj],folder/'sketch_disassembly.txt')
            su=list(build.rglob('*.su'));graphs=list(build.rglob('*.cgraph'))
            if not su or not graphs:raise RuntimeError('Stack/callgraph metadata missing')
            stack='\n'.join(p.read_text() for p in su)
            (folder/'stack_usage.txt').write_text(stack)
            entry.update(build_ok=True,elf_sha256=digest(elf),elf_bytes=elf.stat().st_size,
                stack_usage_files=[str(p.relative_to(build)) for p in su],
                callgraph_files=[str(p.relative_to(build)) for p in graphs],
                focus_symbols=[line for line in (folder/'sketch_object_symbols.txt').read_text().splitlines()
                               if any(s in line for s in ('prepare_batch_half',' loop','scope_crc_fast::compute'))],
                focus_stack=[line for line in stack.splitlines() if any(s in line for s in ('prepare_batch_half','loop()','void loop'))])
            save()
        report['ok']=True
    except BaseException as exc:
        report['error']=repr(exc)
    finally:
        report['changed_original_sources']=[p.relative_to(src).as_posix() for p in files
                                            if digest(p)!=original[p.relative_to(src).as_posix()]]
        if report['changed_original_sources']:report['ok']=False
        save()
    print(json.dumps(dict(ok=report['ok'],error=report.get('error'),output=str(output),hardware_used=False)))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
