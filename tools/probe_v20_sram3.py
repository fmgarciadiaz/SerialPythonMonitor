#!/usr/bin/env python3
"""Private V20 SRAM3 ADC screen, wrapped in verified V19 backup/restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import time
import zlib

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_relay_candidate_v19 import execute_build
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.prepare import atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.q_support.board import source_files
from monitor.v20.io.live_connection import LiveConnection
from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
from monitor.v20.receiver.unoq_acquisition import Configuration
from tools.relay_wire_metrics_v19 import WireMetrics

APP='/home/arduino/ArduinoApps/scope-v20-20261031-225916'
CONTAINER='serialmonitor-usb-stream-v20'
MANIFEST=r'''
import pathlib,hashlib,json,sys
root=pathlib.Path(sys.argv[1]);names=json.loads(sys.argv[2])
print(json.dumps({name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}))
'''


def screen(receiver,config,seconds):
    receiver.configure(config) # Unique request ID and actual APPLIED required.
    if receiver.config_applied is None or receiver.config!=config:
        raise RuntimeError('V20 configuration not confirmed')
    metrics=WireMetrics(config.bits,config.rate,config.period,config.node_pairs,config.channels)
    original=receiver.connection.read
    def read():
        data=original();metrics.feed(data);return data
    receiver.connection.read=read
    start=time.monotonic()
    before=receiver.decoder.pairs
    try:
        while time.monotonic()-start<seconds:receiver.pump()
    finally:receiver.connection.read=original
    report=metrics.report();samples=receiver.decoder.pairs-before
    report.update(elapsed_seconds=time.monotonic()-start,validated_samples=samples,
                  integrity_pass=samples>0,scope='ADC transport only; not GUI/audio or analog qualification',
                  queue_capacity=(config._native or {}).get('queue_slots',4),publicly_accepted=False,
                  applied_request_id=receiver.config_applied.request_id,applied_epoch=receiver.config_applied.epoch)
    if not samples:raise RuntimeError('No validated V20 samples')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--rates',type=int,nargs='+',choices=(1860465,2000000,2051282),default=(1860465,2000000,2051282))
    parser.add_argument('--install-memory-fix',action='store_true',help='Install the reviewed SRAM tail repair with original V20 source/cache archive')
    parser.add_argument('--install-storage-fix',action='store_true')
    parser.add_argument('--baseline-proof',type=Path)
    parser.add_argument('--storage-cycle',action='store_true')
    parser.add_argument('--ready-no-yield',action='store_true',help='Private exact READY loop comparison; no source edits')
    parser.add_argument('--tcp-queue-recovery',action='store_true',help='Private isolated FIFO recovery header; never updates product sources')
    args=parser.parse_args();output=args.output.resolve()
    if args.tcp_queue_recovery and args.ready_no_yield:parser.error('Do not combine independent relay experiments')
    if args.install_memory_fix and args.install_storage_fix:parser.error('Select one source patch only')
    if args.install_storage_fix:
        if args.baseline_proof is None:parser.error('Restored baseline proof required')
        from tools.v20_storage_fix import validate
        validate(args.baseline_proof)
    elif args.baseline_proof is not None:parser.error('Baseline proof requires storage patch')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('New private V20 output required')
    if not 1<=args.seconds<=120:parser.error('seconds must be 1..120')
    output.mkdir(parents=True);report=dict(private=True,promoted=False,version=20,cases=[],ready_no_yield=args.ready_no_yield,tcp_queue_recovery=args.tcp_queue_recovery)
    save=lambda:atomic_report(output/'report.json',report);save()
    acceptance=load_acceptance(RECEIPT);backend=ProductionBackend(acceptance);backend._board().serial=args.serial
    def trial(b,_sources,_output):
        board=b._board();stage='/tmp/v20-sram3-'+b.token;compiler='v20-compiler-'+b.token
        port=None;connection=None;app_started=False;relay_started=False;memory_backup=None;successful=False
        try:
            from monitor.v20.memory_contract import verify_board
            report['memory_contract']=verify_board(board);save()
            if args.install_memory_fix:
                from tools.v20_memory_fix import install
                memory_backup=install(b,APP,stage,output);report['memory_fix_backup']=memory_backup;save()
            if args.install_storage_fix:
                from tools.v20_storage_fix import install
                memory_backup=install(b,APP,stage,output,args.baseline_proof);report['memory_fix_backup']=memory_backup;save()
            expected={p.relative_to(ROOT/'arduino/v20/oscilloscope').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source_files(ROOT/'arduino/v20/oscilloscope')}
            actual=json.loads(board.shell('python3','-c',MANIFEST,APP,json.dumps(list(expected)),capture=True).stdout)
            if actual!=expected:raise RuntimeError('Imported V20 source bytes differ from local V20')
            report['v20_sources']=expected
            report['compiler_image']=json.loads(b._output('docker','image','inspect','q-gcc'))[0]['Id']
            firmware_before=b._hash(APP+'/.cache/sketch/sketch.ino.bin');report['firmware_before']=firmware_before;save()
            board.shell('mkdir','-p',stage)
            relay_hashes={}
            for p in sorted((ROOT/'arduino/v20/relay').iterdir()):
                if p.is_file():
                    source=p
                    if p.name=='base_verifier.c' and args.ready_no_yield:
                        text=p.read_text();anchor='if(now()<spin_until) { sched_yield(); continue; }'
                        if text.count(anchor)!=1:raise RuntimeError('Unique V20 READY yield anchor required')
                        source=output/'private_base_verifier.c'
                        source.write_text(text.replace(anchor,'if(now()<spin_until) { __asm__ volatile("" ::: "memory"); continue; }'))
                    if p.name=='frame_send_queue.h' and args.tcp_queue_recovery:
                        source=ROOT/'experiments/v20/tcp_queue_recovery/frame_send_queue.h'
                        (output/'private_frame_send_queue.h').write_bytes(source.read_bytes())
                    relay_hashes[p.name]=hashlib.sha256(source.read_bytes()).hexdigest()
                    board.run('push',str(source),stage+'/'+p.name)
            report['relay_sources']=relay_hashes
            save()
            b._candidate_compile_cleared=False
            with (output/'relay_compile.log').open('w') as log:
                command=['docker','run','--rm','--name',compiler,'--user','0:0',
                         '--security-opt','no-new-privileges','-v',stage+':/build','q-gcc',
                         'cc','-O2','-std=c11','-Wall','-Wextra','-Werror',
                         '/build/unoq_config_stream.c','-lm','-o','/build/relay.bin']
                subprocess.run([board.adb,'-s',board.serial,'shell',shlex.join(command)],
                               stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            b._candidate_compile_cleared=True
            board.run('pull',stage+'/relay.bin',str(output/'relay.bin'))
            report['relay_sha256']=b._hash(stage+'/relay.bin')
            cfg=json.loads((ROOT/'arduino/v20/unoq.json').read_text());cfg['remote_app']=APP
            v20=board.__class__(cfg);v20.serial=args.serial
            app_started=True;v20.start()
            loaded=b._hash(APP+'/.cache/sketch/sketch.ino.bin')
            if memory_backup is None and loaded!=firmware_before:
                raise RuntimeError('V20 launcher changed the precompiled firmware; preserve and audit before retry')
            report['previous_firmware']=firmware_before
            firmware_before=loaded;report['firmware_before']=loaded;save()
            for filename in ('sketch.ino.bin','sketch.ino.elf','sketch.ino_debug.elf'):
                board.run('pull',APP+'/.cache/sketch/'+filename,str(output/filename))
            names=b._output('docker','ps','-a','--format','{{.Names}}').splitlines()
            if CONTAINER in names:raise RuntimeError('Existing V20 relay must be inspected; not overwritten')
            board.shell('docker','run','-d','--name',CONTAINER,'--net','host','--read-only',
                '--label','arduscopio.v20-trial='+b.token,'--user','0:0','--cap-drop','ALL','--cap-add','SYS_NICE','--security-opt','no-new-privileges',
                '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
                '-v',stage+'/relay.bin:/work/unoq_stream:ro',
                '--mount','type=bind,src=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor,dst=/scope_cpu_governor',
                '--entrypoint','/work/unoq_stream','ghcr.io/arduino/app-bricks/python-apps-base:0.12.0')
            relay_started=True
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                if 'SPI ready: first verified frame' in b._output('sh','-c','docker logs '+CONTAINER+' 2>&1'):break
                time.sleep(.2)
            else:raise RuntimeError('V20 SPI did not produce its first verified frame')
            port=board.run('forward','tcp:0','tcp:8766',capture=True).stdout.strip()
            connection=LiveConnection(socket.create_connection(('127.0.0.1',int(port)),timeout=3),args.serial)
            receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
            for rate in args.rates:
                row=dict(rate=rate,state='running');report['cases'].append(row);save()
                try:row.update(state='complete',metrics=screen(receiver,Configuration(8,rate),args.seconds))
                except Exception as exc:row.update(state='failed',error=repr(exc));save();raise
                save()
            if args.storage_cycle:
                report['storage_cycle']=[]
                for bits,rate in ((8,1860465),(14,1000000),(14,363636),(8,1860465)):
                    config=Configuration(bits,rate);row=dict(bits=bits,rate=rate,channels=config.channels,state='running')
                    report['storage_cycle'].append(row);save()
                    try:row.update(state='complete',metrics=screen(receiver,config,min(args.seconds,5)))
                    except Exception as exc:row.update(state='failed',error=repr(exc));save();raise
                    save()
            successful=True
            return dict(firmware_sha256=firmware_before,relay_sha256=report['relay_sha256'],adc_only=True)
        except BaseException as exc:
            report['trial_error']=repr(exc);save();raise
        finally:
            from tools.v20_trial_cleanup import finish_steps,app_is_stopped,owned_relay,stop_relay_id,confirm_quiescence
            quiet=dict(app=not app_started,relay=False,compiler=False);owned={}
            def discover_relay():
                identity=owned_relay(b,CONTAINER,b.token)
                if identity is None:quiet['relay']=True
                else:owned['relay']=identity
            def relay_log():
                if 'relay' in owned:
                    (output/'v20_relay.log').write_text(b._output('sh','-c','docker logs '+owned['relay']+' 2>&1'))
            def stop_relay():
                if 'relay' not in owned:return
                stop_relay_id(b,board,owned['relay'],report)
                quiet['relay']=True
            def rename_relay():
                if 'relay' in owned and quiet['relay']:
                    board.shell('docker','rename',owned['relay'],CONTAINER+'-evidence-'+b.token[:8])
            def stop_app():
                if app_started:
                    container=APP.rsplit('/',1)[-1]+'-main-1'
                    if not app_is_stopped(b,container):
                        try:board.cli('app','stop',APP)
                        except Exception as exc:
                            report.setdefault('cleanup_fallbacks',[]).append(dict(step='stop_app',error=repr(exc)))
                            if not app_is_stopped(b,container):board.cli('app','stop',APP)
                    if not app_is_stopped(b,container):raise RuntimeError('V20 app still running')
                    quiet['app']=True
            def stop_compiler():
                names=b._output('docker','ps','-a','--format','{{.Names}}').splitlines()
                if compiler in names:board.shell('docker','rm','-f',compiler)
                if compiler in b._output('docker','ps','-a','--format','{{.Names}}').splitlines():
                    raise RuntimeError('Compiler termination not verified')
                quiet['compiler']=True
            def restore_v20(errors):
                nonlocal memory_backup
                # Prevent the outer transaction from restarting acquisition if
                # any private writer has not been confirmed stopped.
                report['trial_quiescence']=quiet.copy()
                confirm_quiescence(b,quiet)
                if memory_backup is None and (args.install_memory_fix or args.install_storage_fix) and (output/'memory_fix_backup.json').exists():
                    memory_backup=json.loads((output/'memory_fix_backup.json').read_text())
                if memory_backup is not None and (not successful or errors):
                    report['v20_state_uncertain']=True
                    if not all(quiet.values()):raise RuntimeError('V20 rollback blocked until all private writers stop')
                    from tools.v20_memory_fix import undo
                    report['v20_previous_verification']=undo(b,APP,memory_backup)
                    report['v20_previous_restored']=True;report['v20_state_uncertain']=False
            steps=[('close_receiver',lambda:connection.close() if connection is not None else None),
                   ('remove_forward',lambda:board.run('forward','--remove','tcp:'+port) if port else None),
                   ('identify_relay',discover_relay),('capture_relay_log',relay_log),
                   ('stop_relay',stop_relay),('rename_relay',rename_relay),
                   ('stop_app',stop_app),('stop_compiler',stop_compiler)]
            finish_steps(steps,restore_v20,report,save)
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def cancel(*_):
        if not report.get('restoring') and not report.get('trial_cleanup_active'):raise KeyboardInterrupt('V20 cancelled; restoring V19')
    for sig in previous:signal.signal(sig,cancel)
    try:
        ok=execute_build(backend,acceptance,ROOT/'arduino/v20/oscilloscope/sketch',output,report,save,
                         builder=trial,operation_name='v20_sram3_ADC_screen')
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,error=report.get('error'),restored=report.get('restoration',{}).get('ok'))))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
