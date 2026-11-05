"""Installed-only private ADC screen; retain V20 and restore its live snapshot."""
import argparse,hashlib,json,signal,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v20.io.live_connection import installed_connection,installed_identity
from monitor.v20.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v20.receiver.unoq_acquisition import Configuration
from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
from monitor.v20.q_support.prepare import atomic_report
from tools.relay_wire_metrics_v19 import WireMetrics
from tools.private_v20_pair import reserve_screen

from tools.private_rate_profiles_v20 import PRIVATE_PROFILES,diagnostic_profiles


def screen(receiver,config,seconds,progress=lambda row:None):
    receiver.configure(config)
    if receiver.config_applied is None or receiver.config!=config:
        raise RuntimeError('Configuration was not confirmed')
    metrics=WireMetrics(config.bits,config.rate,config.period,config.node_pairs,config.channels)
    original=receiver.connection.read
    def read():
        data=original();metrics.feed(data);return data
    before=receiver.decoder.pairs;receiver.connection.read=read;started=time.monotonic()
    last_progress=started
    try:
        while time.monotonic()-started<seconds:
            receiver.pump();now=time.monotonic()
            if now-last_progress>=5:
                status=receiver.decoder.status or {}
                progress(dict(rate=config.rate,elapsed=now-started,samples=receiver.decoder.pairs-before,
                    status={k:status.get(k) for k in ('dropped','fatal','queue','queue_peak','slack_ticks','send_ticks')}))
                last_progress=now
    finally:receiver.connection.read=original
    samples=receiver.decoder.pairs-before;status=receiver.decoder.status or {}
    result=metrics.report();result.update(elapsed_seconds=time.monotonic()-started,
        validated_samples=samples,integrity_pass=samples>0 and status.get('dropped')==0 and status.get('fatal')==0,
        dropped=status.get('dropped'),fatal=status.get('fatal'),queue_capacity=config._native.get('queue_slots',4),
        applied_request_id=receiver.config_applied.request_id,applied_epoch=receiver.config_applied.epoch)
    result['private_reserve']=reserve_screen(result['all'],result['queue_capacity'])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seconds',type=int,choices=(10,20,60,120),default=20)
    parser.add_argument('--bits',type=int,choices=(8,10,12,14,16),default=8)
    parser.add_argument('--rates',type=int,nargs='+',default=(1860465,2000000))
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('New V20 diagnostic directory required')
    out.mkdir(parents=True)
    report=dict(private=True,promoted=False,version=20,ok=False,cases=[],
        requested_bits=args.bits,requested_rates=args.rates,
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Installed original V20, ADC only; no GUI/audio or analog qualification; no deployment')
    save=lambda:atomic_report(out/'report.json',report)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def cancel(*_):raise KeyboardInterrupt('Cancelled; restoring V20 snapshot')
    for sig in previous:signal.signal(sig,cancel)
    save();activity=None
    try:
        from monitor.v20.process_activity import MacActivity,acquisition_activity_mode
        mode=acquisition_activity_mode('receiver')
        if mode!='off':
            activity=MacActivity(mode);report['activity']=dict(mode=mode,active=activity.active)
        with diagnostic_profiles(args.bits,args.rates),installed_connection(args.serial) as connection:
            report['identity_before']=connection.identity;save()
            receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
            lifecycle=ReceiverLifecycle(receiver,connection.identity,out/'sessions')
            try:
                lifecycle.capture()
                for rate in args.rates:
                    case=dict(bits=args.bits,rate=rate,state='running');report['cases'].append(case);save()
                    def progress(row):
                        with (out/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
                    try:
                        case.update(metrics=screen(receiver,Configuration(args.bits,rate),args.seconds,progress),state='complete')
                    except BaseException as exc:
                        case.update(state='failed',error=repr(exc));raise
                    finally:save()
            finally:
                # Restoration is independent of a requested trial cancellation.
                for sig in previous:signal.signal(sig,signal.SIG_IGN)
                report['restoration']=lifecycle.restore(recovery_seconds=10);save()
                receiver.close()
        report['identity_after']=installed_identity(args.serial)
        report['identity_unchanged']=report['identity_before']==report['identity_after']
    except BaseException as exc:report['error']=repr(exc)
    finally:
        if activity is not None:
            activity.close();report['activity']['released']=not activity.active
        for sig,handler in previous.items():signal.signal(sig,handler)
        report['ok']=bool(not report.get('error') and report.get('identity_unchanged')
            and report.get('restoration',{}).get('hardware_restored')
            and report['cases'] and all(c.get('metrics',{}).get('integrity_pass') for c in report['cases']))
        save()
    print(json.dumps(dict(ok=report['ok'],report=str(out/'report.json'),error=report.get('error'))))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
