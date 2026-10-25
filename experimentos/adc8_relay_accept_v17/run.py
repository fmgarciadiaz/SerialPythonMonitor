"""ADC8/1.632653 MS/s accept N1/N8 pair; same relay binary and cc46 MCU.

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
        accept_every=1
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
        x.folder=EXP/('adc8_accept_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
        x.report=dict(ok=False,restored=False,cases=[],scope=__doc__,source_hashes=hashes,
            candidate_profiles_sha256=reference['candidate_profiles_sha256'],host_profiles=list(profiles),
            actual_rate=config.actual_rate,requested_seconds=60,
            source_evidence=summary['reports'],queue_slots=8,node_pairs=3456,
            transport='SPI40 / MCU WORD / SCHED_FIFO10 / CPU2 / performance',
            entry='Both use integrity_only: low14/40000 -> private8/1428571 -> live0.5s -> target',
            metrics_limitation='Inherited Integration.trial samples decoder.statuses per pump; repeated produced statuses may weight mean send margin. Queue maximum is valid; do not use this A/B mean as final headroom acceptance.',
            runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        x.report.update(selected_rate=args.rate,accept_policies=[1,8])
        x.report['instrumentation']='Edge timing retained; accept every8 eligible frames only with active exact ADC8 client; effective pollframes/calls/skips counters'
        x.report['reference_relay_sha256']=reference['candidate_relay_sha256']
        (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes())
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
                x.report['candidate_relay_sha256']=digest;x.save()
                for name in FILES:x.board.run('push',str(CERTIFIED/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
                x.board.start();x.start_relay(x.relay)
                x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
                if x.report['candidate_identity']!=summary['candidate_identity']:raise ValueError('Certified firmware binary changed')
                x.normal_check('candidate_boot_low')
                for every in (1,8):
                    x.accept_every=every
                    if every==8:
                        usb_stream.stop(x.board);x.board.stop();x.board.start();x.start_relay(x.relay)
                        actual_digest=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
                        x.report['policy_n8_actual_relay_sha256']=actual_digest;x.save()
                        if actual_digest!=digest:raise ValueError('Relay binary changed between accept policies')
                        identity=instrument_identity(x.board.serial)
                        if identity!=summary['candidate_identity']:raise ValueError('Firmware changed between accept policies')
                        x.normal_check('candidate_n8_boot_low')
                    name='adc8_accept_n'+str(every)
                    row=x.trial(config,60,name,restart=False)
                    row['accept_every']=every;row['relay_sha256']=digest;x.save()
                    x.normal_check(name+'_normal')
                    logs=x.logs(name+'_relay.log')
                    rows=[json.loads(line.split('SPM_RELAY_TIMING ',1)[1]) for line in logs.splitlines() if 'SPM_RELAY_TIMING ' in line]
                    target_rows=[profile for summary_row in rows if summary_row.get('accept_every')==every for profile in summary_row['profiles'] if profile['ticks']==98 and profile['accept_poll_frames']]
                    if not target_rows:raise RuntimeError('Missing accept-policy timing evidence')
                    frames=sum(profile['accept_poll_frames'] for profile in target_rows)
                    calls=sum(profile['accept_calls'] for profile in target_rows)
                    row['accept_poll_frames']=frames;row['accept_calls']=calls
                    row['accept_calls_per_pollframe']=calls/frames
                    row['accept_wall_ns_per_pollframe']=sum(profile['stages']['socket_accept']['sum_ns'] for profile in target_rows)/frames
                    x.report.setdefault('relay_timing_summaries',[]).append(dict(accept_every=every,records=rows));x.save()
                    if not row.get('ok'):raise RuntimeError('A/B case failed; no further case or retry')
                x.report['ok']=all(row['ok'] for row in x.report['cases'])
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
