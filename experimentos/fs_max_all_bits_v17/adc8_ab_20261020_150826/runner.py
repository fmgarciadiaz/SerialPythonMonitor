"""ADC-only A/B: two 60-s cases on the exact existing cc46 candidate, rollback.

Private host copies normalize the entry sequence. No public profile/source edits.
No retries: stop the comparison on the first failed case.
"""
import hashlib
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
    summary=json.loads((EXP/'qualification_summary.json').read_text())
    reference=json.loads((ROOT/summary['reports'][0]).read_text())
    sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
    hashes={'sketch/'+n:hashlib.sha256((EXP/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in FILES}
    hashes.update({'relay/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    if hashes!=reference['source_hashes']:raise ValueError('Candidate sources changed after qualification')
    if hashlib.sha256((EXP/'candidate_profiles.json').read_bytes()).hexdigest()!=reference['candidate_profiles_sha256']:
        raise ValueError('Private candidate profiles changed after qualification')
    expected=summary['candidate_identity']
    if expected['firmware_sha256']!='cc46e4f798a39edfb8e5bd2db8ecd510dd40fee3f10e89c69978de4191156223':
        raise ValueError('Unexpected certified candidate identity')
    return summary,reference,sources,hashes


def main():
    from tools.unoq import Board,config_path
    from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
    from monitor.v17.board_owner import board_owner
    from monitor.v17.bode_calibration import instrument_identity
    from monitor.v17.receiver import unoq_native
    from monitor.v17.receiver.unoq_acquisition import Configuration
    import usb_stream
    summary,reference,sources,hashes=certified_sources()
    profiles=private_profiles(unoq_native.PROFILES,json.loads((EXP/'candidate_profiles.json').read_text()))
    # Replace only these two host descriptions in this process; no JSON mutation.
    remaining=tuple(p for p in unoq_native.PROFILES if not(p['bits']==8 and p['channels']==1 and p['ticks'] in (98,100)))
    with patch.object(unoq_native,'PROFILES',profiles+remaining):
        configs=[Configuration(8,160000000//p['ticks']) for p in profiles]
        x=RelayCampaign.__new__(RelayCampaign)
        x.board=Board(json.loads(config_path('v17').read_text()));x.headroom_only=False;x.normal=None;x.sources=sources
        x.folder=EXP/('adc8_ab_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
        x.report=dict(ok=False,restored=False,cases=[],scope=__doc__,source_hashes=hashes,
            candidate_profiles_sha256=reference['candidate_profiles_sha256'],host_profiles=list(profiles),
            actual_rates=[c.actual_rate for c in configs],requested_seconds=60,
            source_evidence=summary['reports'],queue_slots=8,node_pairs=3456,
            transport='SPI40 / MCU WORD / SCHED_FIFO10 / CPU2 / performance',
            entry='Both use integrity_only: low14/40000 -> private8/1428571 -> live0.5s -> target',
            metrics_limitation='Inherited Integration.trial samples decoder.statuses per pump; repeated produced statuses may weight mean send margin. Queue maximum is valid; do not use this A/B mean as final headroom acceptance.',
            runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes())
        with zipfile.ZipFile(x.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for key in hashes:archive.write(EXP/('oscilloscope/'+key if key.startswith('sketch/') else key),key)
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
                if digest!=reference['candidate_relay_sha256']:raise ValueError('Certified relay binary changed')
                for name in FILES:x.board.run('push',str(EXP/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
                x.board.start();x.start_relay(x.relay)
                x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
                if x.report['candidate_identity']!=summary['candidate_identity']:raise ValueError('Certified firmware binary changed')
                x.normal_check('candidate_boot_low')
                for config in configs:
                    name='adc8_ab_'+str(config.rate)
                    row=x.trial(config,60,name,restart=False)
                    x.normal_check(name+'_normal')
                    x.logs(name+'_relay.log')
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
