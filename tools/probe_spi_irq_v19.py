"""Private, reversible SPI IRQ affinity screen with the accepted V19 pair."""
import argparse
import json
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monitor.v19.board_owner import board_owner
from monitor.v19.receiver.unoq_usb import adb
from monitor.v19.io.live_connection import installed_connection,installed_identity
from monitor.v19.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
from monitor.v19.q_support.prepare import atomic_report


def spi_irq(text):
    matches=re.findall(r'^\s*(\d+):.*\s4a94000\.spi\s*$',text,re.M)
    if len(matches)!=1:raise ValueError('Unique dedicated 4a94000.spi IRQ required')
    return int(matches[0])


def restore_affinity(original, read, write):
    current=read()
    if current==original:
        return current  # A rejected write may not have changed anything.
    write(original['requested'])
    current=read()
    if current!=original:
        # Some controllers retain the current CPU when widening a mask.
        write(original['effective'])
        write(original['requested'])
        current=read()
    return current


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--hold',type=float,default=20)
    parser.add_argument('--writer',choices=('sudo','docker'),default='sudo',
                        help='Docker uses the existing Q image and a single writable IRQ-file bind')
    args=parser.parse_args();folder=args.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private diagnostic output required')
    if not 0<args.hold<=120:parser.error('hold must be in (0,120]')
    folder.mkdir(parents=True)
    report=dict(private=True,promoted=False,ok=False,changed=False,writer=args.writer)
    save=lambda:atomic_report(folder/'report.json',report)
    save();child=None;snapshot=None;dirty=False;irq=None
    def remote(*command):return adb('-s',args.serial,'shell',shlex.join(command))
    def affinity():
        return dict(requested=remote('cat',f'/proc/irq/{irq}/smp_affinity_list'),
                    effective=remote('cat',f'/proc/irq/{irq}/effective_affinity_list'))
    def write(value):
        if not re.fullmatch(r'[0-9,-]+',value):raise ValueError('Invalid affinity list')
        script='import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])'
        if args.writer=='sudo':
            remote('sudo','-n','python3','-c',script,f'/proc/irq/{irq}/smp_affinity_list',value)
        else:
            # Same narrow bind-mount pattern as Q's accepted governor control.
            # No privileged container, network, image pull or host-root mount.
            remote('docker','run','--rm','--pull','never','--network','none','--read-only',
                   '--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0',
                   '--mount',f'type=bind,src=/proc/irq/{irq}/smp_affinity_list,dst=/scope_irq',
                   '--entrypoint','python3','ghcr.io/arduino/app-bricks/python-apps-base:0.12.0',
                   '-c',script,'/scope_irq',value)
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def interrupted(*_):
        if report.get('restoring'):return
        raise KeyboardInterrupt('IRQ experiment cancelled; restoring')
    for sig in previous:signal.signal(sig,interrupted)
    try:
        with installed_connection(args.serial) as connection:
            report['identity']=connection.identity
            receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
            life=ReceiverLifecycle(receiver,connection.identity,folder/'baseline')
            snapshot=life.capture();report['snapshot']=snapshot.to_dict();save()
            receiver.close()
        with board_owner(args.serial,'private SPI IRQ preflight'):
            if installed_identity(args.serial)!=report['identity']:raise RuntimeError('Pair identity changed')
            irq=spi_irq(remote('cat','/proc/interrupts'))
            report['irq']=irq;report['original_affinity']=affinity();save()
            if report['original_affinity']['effective']=='2':raise RuntimeError('IRQ already on CPU2; no comparison')
            dirty=True;save();write('2');report['candidate_affinity']=affinity()
            if report['candidate_affinity']!={'requested':'2','effective':'2'}:
                raise RuntimeError('CPU2 affinity did not apply')
            report['changed']=True;save()
        command=[sys.executable,str(ROOT/'tools/gui_accepted_metrics_v19.py'),
                 '--metrics-output',str(folder/'metrics.json'),'--serial',args.serial,
                 '--output',str(folder/'gui.json'),'--bits','8','--rate','1860465',
                 '--fft-size','16384','--frequency-khz','550','--duration',str(args.hold+5),
                 '--hold-radio-seconds',str(args.hold),'--no-retune']
        report['command']=command;save()
        with (folder/'gui.log').open('w') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            child.wait(timeout=args.hold+150)
        evidence=json.loads((folder/'gui.json').read_text())
        metrics=json.loads((folder/'metrics.json').read_text())
        report['functional_pass']=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values())
        report['headroom']=metrics['radio_playing']
        report['errors']=evidence['errors']
        periodic=[s for s in evidence['stages'] if s['stage']=='periodic']
        report['exposed_fraction']=sum(bool(s.get('exposed')) for s in periodic)/max(1,len(periodic))
        report['visible_gui_pass']=bool(periodic) and evidence['display']['platform']=='cocoa' and report['exposed_fraction']>=.9 and evidence['paint_events']>=args.hold*8
    except BaseException as exc:
        report['error']=repr(exc)
    finally:
        report['restoring']=True;save()
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=90)
            except subprocess.TimeoutExpired:report['owner_still_active']=True
        if not report.get('owner_still_active'):
            if dirty:
                try:
                    with board_owner(args.serial,'restore private SPI IRQ affinity'):
                        report['final_affinity']=restore_affinity(report['original_affinity'],affinity,write)
                        report['irq_restored']=report['final_affinity']==report['original_affinity']
                except BaseException as exc:report['irq_restore_error']=repr(exc)
            if snapshot is not None:
                try:
                    with installed_connection(args.serial) as connection:
                        if connection.identity!=report['identity']:raise RuntimeError('Final pair identity differs')
                        receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
                        life=ReceiverLifecycle(receiver,connection.identity,folder/'restore')
                        life.snapshot=snapshot;report['restoration']=life.restore(10);receiver.close()
                except BaseException as exc:report['restore_error']=repr(exc)
        report['restoring']=False
        report['ok']=bool(report.get('functional_pass') and report.get('visible_gui_pass') and
                          report.get('headroom',{}).get('headroom_pass') and report.get('irq_restored') and
                          report.get('restoration',{}).get('hardware_restored') and not report.get('error'))
        save()
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps({k:report.get(k) for k in ('ok','error','headroom','irq_restored','restoration')}))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
