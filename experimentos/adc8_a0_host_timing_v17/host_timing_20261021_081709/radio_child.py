"""Owned RADIO/FFT/A0 qualification child; exact helper evidence survives errors."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]


def trial_arguments(seconds):
    if seconds not in (60,120):raise ValueError('Qualification duration must be 60 or 120 seconds')
    return ['adc8_accept_radio','--bits','8','--rate','1632653','--seconds',str(seconds),
        '--audio-rate','40000','--bandwidth','8000','--analysis-audit','--refill-ring','--defer-diagnostics','--host-cpu-trace']


def outcome(report):
    paint=report.get('paint_audit',{})
    transport=report.get('audio_transport',{})
    ordinary=report.get('audio_source_type')=='RadioDacSource' and transport.get('chunk_burst')==8
    audio=bool(report.get('ok') and report.get('restored') and ordinary and not report.get('errors'))
    visual=paint.get('exposed_fraction',0)>=.9 and paint.get('fft_fps',0)>=5
    stats=report.get('joint_send_statistics',{})
    headroom=audio and stats.get('mean_margin',0)>=.1 and report.get('adc_queue_peak',99)<4 and stats.get('minimum_slack_ticks',0)>0
    return dict(ok=audio and visual,audio_integrity_ok=audio,visual_ok=visual,headroom_ok=headroom,
        restored=bool(report.get('restored')),ordinary_source_policy_ok=ordinary)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,choices=(60,120),required=True)
    parser.add_argument('--result',type=Path,required=True)
    args=parser.parse_args(argv)
    if int(os.environ.get('SPM_ADC8_ACCEPT_OWNER_PID','0'))!=os.getppid():
        raise RuntimeError('Child requires its live board owner parent')
    from monitor.v17.receiver import unoq_native
    from experimentos.fs_max_all_bits_v17.adc8_ab import private_profiles,EXP
    profiles=private_profiles(unoq_native.PROFILES,json.loads((EXP/'candidate_profiles.json').read_text()))
    remaining=tuple(p for p in unoq_native.PROFILES if not(p['bits']==8 and p['channels']==1 and p['ticks'] in (98,100)))
    result=dict(ok=False,audio_integrity_ok=False,visual_ok=False,headroom_ok=False,restored=False)
    reports=ROOT/'diagnosticos/resultados_v17'
    before=set(reports.glob('generador_radio_*/report.json'))
    try:
        with patch.object(unoq_native,'PROFILES',profiles+remaining):
            from experimentos.fs_max_all_bits_v17.joint import private_profile_access
            from diagnosticos.validar_generador_radio_v17 import main as audio_trial
            sys.argv=trial_arguments(args.seconds)
            with private_profile_access(8,1632653):
                report,folder=audio_trial(owner_context=nullcontext())
            result.update(outcome(report),report=str(folder/'report.json'),host_profiles=list(profiles))
    except BaseException as exc:
        new=list(set(reports.glob('generador_radio_*/report.json'))-before)
        path=max(new,key=lambda p:p.stat().st_mtime) if new else None
        if path is not None:
            report=json.loads(path.read_text());result.update(outcome(report),report=str(path))
        result.update(ok=False,audio_integrity_ok=False,error=repr(exc),traceback=traceback.format_exc())
    finally:
        args.result.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    report=main()
    raise SystemExit(0 if report['audio_integrity_ok'] and report['restored'] else 1)
