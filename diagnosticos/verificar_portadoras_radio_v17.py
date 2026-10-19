"""Independent RADIO carriers: snapshot, zero-amplitude checks and exact restoration."""
import argparse
from dataclasses import asdict,replace
import json
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode


def capture(receiver,seconds):
    start=time.monotonic();before=receiver.decoder.pairs
    while time.monotonic()-start<seconds:receiver.pump()
    status=dict(receiver.decoder.status)
    return dict(seconds=time.monotonic()-start,samples=receiver.decoder.pairs-before,status=status,
                integrity_ok=receiver.decoder.pairs>before and not status.get('dropped',0) and not status.get('fatal',0))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',choices=('snapshot','validate','restore'),default='validate')
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--use-prior-adc',action='store_true')
    parser.add_argument('--folder',required=True,type=Path)
    args=parser.parse_args();args.folder.mkdir(parents=True,exist_ok=True)
    prior_path=args.folder/'prior.json';report_path=args.folder/'report.json'
    require_exclusive_monitor()
    report=dict(scope='Physical zero-amplitude RADIO TEST protocol/DMA; no analog carrier or waveform acceptance',cases=[],restored=False,ok=False)
    def persist():report_path.write_text(json.dumps(report,indent=2)+'\n')
    try:
        with Connection(args.serial) as connection:
            receiver=OutputReceiver(connection,lambda _:None);receiver.decoder.numeric=True
            receiver.select(Mode.SPI);initial=receiver.generator()
            if args.action=='snapshot':
                if prior_path.exists():raise RuntimeError('Prior snapshot already exists; refusing overwrite')
                receiver.wav_request();deadline=time.monotonic()+3
                while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
                if receiver.wav_status is None or receiver.wav_status.state.value not in (0,3):raise RuntimeError('WAV output is not idle')
                prior=dict(adc=asdict(receiver.config),generator=asdict(initial.active),transport='SPI',identity=instrument_identity(args.serial))
                prior_path.write_text(json.dumps(prior,indent=2)+'\n')
                receiver.generator(replace(initial.active,enabled=0))
                print(json.dumps(prior,indent=2),flush=True);return 0
            prior=json.loads(prior_path.read_text());report['identity']=instrument_identity(args.serial)
            try:
                if args.action=='validate':
                    if not initial.radio_test_independent_capable:raise RuntimeError('Missing independent carriers capability')
                    receiver.generator(replace(initial.active,enabled=0))
                    receiver.configure(Configuration(**prior['adc']) if args.use_prior_adc else Configuration(14,40000))
                    for first,second in ((20525,40750),(20525,0),(0,40750),(0,0),(20525,40750)):
                        wanted=GeneratorConfig(wave=1,enabled=1,mode=3,frequency=first*1000,final_frequency=second*1000,duration=750,low=0,high=0)
                        reply=receiver.generator(wanted)
                        case=dict(adc=asdict(receiver.config),wanted=asdict(wanted),actual=asdict(reply.active),running=reply.running)
                        report['cases'].append(case);persist()
                        case.update(capture(receiver,3));case['ok']=reply.active==wanted and reply.running and case['integrity_ok']
                        persist();print(f'F1={first} F2={second}: ok={case["ok"]}',flush=True)
                        if not case['ok']:raise RuntimeError('Carrier configuration or continuity failed')
                    wanted=replace(wanted,enabled=0);reply=receiver.generator(wanted)
                    report['stop_ok']=reply.active==wanted and not reply.running
                    if not report['stop_ok']:raise RuntimeError('RADIO TEST stop failed')
            finally:
                receiver.configure(Configuration(**prior['adc']))
                receiver.generator(GeneratorConfig(**prior['generator']))
                report['recovery']=capture(receiver,10)
                final=receiver.generator();report['final']=dict(adc=asdict(receiver.config),generator=asdict(final.active),running=final.running)
                report['restored']=report['final']['adc']==prior['adc'] and report['final']['generator']==prior['generator']
                report['final_identity']=instrument_identity(args.serial)
                report['identity_unchanged_during_check']=report['identity']==report['final_identity']
                persist()
        report['ok']=report['restored'] and report['recovery']['integrity_ok'] and report['identity_unchanged_during_check'] and all(c['ok'] for c in report['cases'])
    except Exception as exc:report['error']=str(exc)
    persist();print(json.dumps(report,indent=2),flush=True)
    return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
