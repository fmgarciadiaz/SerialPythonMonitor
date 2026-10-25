"""N8 RADIO + FFT + A0 qualification: 60s and three independent 120s cases.

Private host copies normalize the entry sequence. No public profile/source edits.
No retries: stop the comparison on the first failed case.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
EXP=Path(__file__).resolve().parent
CERTIFIED=ROOT/'experimentos/fs_max_all_bits_v17'
from experimentos.fs_max_all_bits_v17.run import FILES
EXPECTED_RELAY='2253ee67a2cdca6e793413b790ccc932cd835de42e6051d1dd2b44dcfa34b13a'
STAGES=(('screen60',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120))

def validate_relay_digest(digest):
    if digest!=EXPECTED_RELAY:raise ValueError('N8 relay differs from the screened binary')


def private_profiles(public, candidates):
    baseline=next(dict(p) for p in public if p['bits']==8 and p['ticks']==100 and p['channels']==1)
    candidate=next(dict(p) for p in candidates if p['bits']==8 and p['ticks']==98 and p['channels']==1)
    for profile in (baseline,candidate):
        if (profile['node_pairs'],profile.get('queue_slots'))!=(3456,8):
            raise ValueError('A/B requires node3456 and queue8 for both profiles')
        # Identical low-load -> SPI40 warm-up -> live settle -> target entry.
        profile.update(optimized_transport=True,integrity_only=True,warmup_rate=1428571)
    return baseline,candidate


def certified_sources():
    from experimentos.fs_max_all_bits_v17.adc8_ab import certified_sources as original_sources
    summary,reference,_,_=original_sources()
    sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
    hashes={'sketch/'+n:hashlib.sha256((CERTIFIED/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in FILES}
    hashes.update({'relay/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    for key,digest in reference['source_hashes'].items():
        if key not in ('relay/unoq_config_stream.c','relay/base_verifier.c','relay/relay_timing.h') and hashes[key]!=digest:
            raise ValueError('Unexpected certified source difference: '+key)
    expected=summary['candidate_identity']
    if expected['firmware_sha256']!='cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223':
        raise ValueError('Unexpected certified candidate identity')
    return summary,reference,sources,hashes


def argument_parser():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rate',type=int,choices=(1632653,),default=1632653)
    return parser


def main(argv=None):
    parser=argument_parser()
    args=parser.parse_args(argv)
    from tools.unoq import Board,config_path
    from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
    from monitor.v17.board_owner import board_owner
    from monitor.v17.bode_calibration import instrument_identity
    from monitor.v17.receiver import unoq_native
    from monitor.v17.receiver.unoq_acquisition import Configuration
    import usb_stream
    from spi_benchmark import IMAGE
    class AcceptCampaign(RelayCampaign):
        accept_every=8
        def start_relay(self,target,prior=False):
            usb_stream.stop(self.board);flags=[]
            for cap in self.report['old_cap_add'] if prior else ['SYS_NICE']:flags+=['--cap-add',cap]
            if prior:
                for mount in self.report['old_mounts']:
                    flags+=['--mount',f"type=bind,src={mount['Source']},dst={mount['Destination']}"+('' if mount['RW'] else ',readonly')]
                for env in self.report['old_scope_environment']:flags+=['--env',env]
                if self.report.get('old_cpuset'):flags+=['--cpuset-cpus',self.report['old_cpuset']]
            else:
                flags+=['--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--mount','type=bind,src=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor,dst=/scope_cpu_governor',
                    '--env',f'SCOPE_ADC8_ACCEPT_EVERY={self.accept_every}']
            self.board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host','--read-only','--cap-drop','ALL',*flags,'--security-opt','no-new-privileges','--user','0:0',
                '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw','--entrypoint','/work/unoq_stream',IMAGE)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                if 'SPI ready: first verified frame' in self.logs('current_relay.log'):return
                time.sleep(.2)
            raise RuntimeError('Relay first frame not confirmed')
    summary,reference,sources,hashes=certified_sources()
    profiles=private_profiles(unoq_native.PROFILES,json.loads((CERTIFIED/'candidate_profiles.json').read_text()))
    # Replace only these two host descriptions in this process; no JSON mutation.
    remaining=tuple(p for p in unoq_native.PROFILES if not(p['bits']==8 and p['channels']==1 and p['ticks'] in (98,100)))
    with patch.object(unoq_native,'PROFILES',profiles+remaining):
        config=Configuration(8,args.rate)
        x=AcceptCampaign.__new__(AcceptCampaign)
        x.board=Board(json.loads(config_path('v17').read_text()));x.headroom_only=False;x.normal=None;x.sources=sources
        x.folder=EXP/('radio_qualification_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
        x.report=dict(ok=False,restored=False,cases=[],scope=__doc__,source_hashes=hashes,
            candidate_profiles_sha256=reference['candidate_profiles_sha256'],host_profiles=list(profiles),
            actual_rate=config.actual_rate,stages=list(STAGES),
            source_evidence=summary['reports'],queue_slots=8,node_pairs=3456,
            transport='SPI40 / MCU WORD / SCHED_FIFO10 / CPU2 / performance',
            entry='Private integrity_only profile preserves receiver preparation via low14/40000 and 8/1428571; connected state selects the existing wait',
            metrics_limitation='Helper uses observed (epoch, produced) changes for send statistics; this is not a census of every node. Paint counts do not prove distinct new frames.',
            runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        x.report.update(selected_rate=args.rate,accept_policy=8,expected_relay_sha256=EXPECTED_RELAY)
        x.report['instrumentation']='Edge timing retained; accept every8 eligible frames only with active exact ADC8 client; effective pollframes/calls/skips counters'
        x.report['reference_relay_sha256']=reference['candidate_relay_sha256']
        (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes())
        (x.folder/'radio_child.py').write_bytes((EXP/'radio_child.py').read_bytes())
        with zipfile.ZipFile(x.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for key in hashes:archive.write((CERTIFIED/('oscilloscope/'+key) if key.startswith('sketch/') else EXP/key),key)
        x.save();changed=False;presence={};prior=None
        subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
        with board_owner(x.board.serial,'ADC8 A/B same cc46 node3456 queue8'):
            try:
                x.snapshot()
                info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
                x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'])
                x.normal=x.policy();x.report['normal_policy']=x.normal
                prior=x.folder/'prior_headers';prior.mkdir();x.report['prior_header_presence']=presence
                for name in FILES:
                    try:x.board.shell('test','-f',x.board.remote+'/sketch/'+name)
                    except subprocess.CalledProcessError:presence[name]=False
                    else:presence[name]=True;x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name))
                x.save();usb_stream.stop(x.board);x.board.stop();changed=True;x.build()
                digest=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
                x.report['candidate_relay_sha256']=digest;x.save();validate_relay_digest(digest)
                for name in FILES:x.board.run('push',str(CERTIFIED/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
                x.board.start();x.start_relay(x.relay)
                x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
                if x.report['candidate_identity']!=summary['candidate_identity']:raise ValueError('Certified firmware binary changed')
                x.normal_check('candidate_boot_low')
                for stage_index,(stage,seconds) in enumerate(STAGES):
                    if stage_index:
                        usb_stream.stop(x.board);x.board.stop();x.board.start();x.start_relay(x.relay)
                        actual_digest=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
                        validate_relay_digest(actual_digest)
                        if instrument_identity(x.board.serial)!=summary['candidate_identity']:raise ValueError('Firmware changed between radio cases')
                        x.normal_check(stage+'_boot_low')
                    result=x.folder/(stage+'_child.json')
                    previous_reports=set((ROOT/'diagnosticos/resultados_v17').glob('generador_radio_*/report.json'))
                    env=dict(os.environ,SPM_ADC8_ACCEPT_OWNER_PID=str(os.getpid()))
                    command=[sys.executable,str(EXP/'radio_child.py'),'--seconds',str(seconds),'--result',str(result)]
                    with (x.folder/(stage+'_child.log')).open('w') as log:
                        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env)
                        timed_out=False
                        try:exit_code=child.wait(timeout=seconds+180)
                        except subprocess.TimeoutExpired:
                            timed_out=True;child.terminate()
                            try:exit_code=child.wait(timeout=15)
                            except subprocess.TimeoutExpired:child.kill();exit_code=child.wait()
                    leaf=json.loads(result.read_text()) if result.exists() else dict(ok=False,restored=False,error='Child exited without result')
                    if timed_out:
                        leaf.update(ok=False,audio_integrity_ok=False,restored=False,error='Child exceeded duration+180s; terminated without retry')
                        if not leaf.get('report'):
                            new=list(set((ROOT/'diagnosticos/resultados_v17').glob('generador_radio_*/report.json'))-previous_reports)
                            if new:leaf['report']=str(max(new,key=lambda path:path.stat().st_mtime))
                    row=dict(stage=stage,requested_seconds=seconds,child_exit=exit_code,child=leaf,
                        child_timed_out=timed_out,
                        audio_integrity_ok=exit_code==0 and leaf.get('audio_integrity_ok',False),
                        visual_ok=leaf.get('visual_ok',False),headroom_ok=leaf.get('headroom_ok',False),
                        restored=leaf.get('restored',False),accept_every=8,relay_sha256=digest)
                    x.report['cases'].append(row);x.save()
                    if not row['audio_integrity_ok'] or not row['restored']:
                        try:x.logs(stage+'_failure_relay.log')
                        except BaseException as exc:row['failure_log_error']=repr(exc)
                        x.save();raise RuntimeError('Real RADIO/ADC/restoration failure; no retry or later stage')
                    x.normal_check(stage+'_normal')
                    x.logs(stage+'_relay.log')
                radio_cases=[row for row in x.report['cases'] if 'child' in row]
                x.report['integrity_ok']=len(radio_cases)==4 and all(row['audio_integrity_ok'] for row in radio_cases)
                x.report['visual_ok']=len(radio_cases)==4 and all(row['visual_ok'] for row in radio_cases)
                x.report['headroom_ok']=len(radio_cases)==4 and all(row['headroom_ok'] for row in radio_cases)
                x.report['ok']=x.report['integrity_ok'] and x.report['visual_ok']
            except BaseException as exc:
                x.report.update(ok=False,error=repr(exc),traceback=traceback.format_exc());x.save()
            finally:
                try:
                    if changed:
                        usb_stream.stop(x.board);x.board.stop()
                        for name in FILES:
                            if presence[name]:x.board.run('push',str(prior/name),x.board.remote+'/sketch/'+name)
                            else:x.board.shell('python3','-c','from pathlib import Path;import sys;Path(sys.argv[1]).unlink(missing_ok=True)',x.board.remote+'/sketch/'+name)
                        x.board.start();x.start_relay(x.report['old_relay'],prior=True)
                    if x.report.get('prior'):x.restore_settings()
                except BaseException as exc:
                    x.report.update(ok=False,restored=False,restore_error=repr(exc),restore_traceback=traceback.format_exc())
                x.save();print('REPORT',x.folder/'report.json',flush=True)
        return x.report


if __name__=='__main__':
    report=main()
    raise SystemExit(0 if report['ok'] and report['restored'] else 1)
