"""Snapshot/check of RADIO TEST immutable table at zero DAC amplitude, with exact restoration."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode


def capture(receiver,seconds):
    before=receiver.decoder.pairs
    start=time.monotonic()
    while time.monotonic()-start<seconds:receiver.pump()
    return {'samples':receiver.decoder.pairs-before,'seconds':time.monotonic()-start,
            'status':dict(receiver.decoder.status)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',action='store_true')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    folder=ROOT/'diagnosticos/resultados_v17'
    prior_path=folder/'radio_hz_prior.json'
    report={'scope':'Zero amplitude immutable 25-Hz table protocol/DMA with ADC continuity; no analog acceptance',
            'dac_rate_hz':128000,'frequency_step_hz':25,
            'ok':False,'restored':False,'cases':[]}
    try:
        with Connection('1060031107') as connection:
            receiver=OutputReceiver(connection,lambda _:None)
            receiver.decoder.numeric=True
            receiver.select(Mode.SPI)
            initial=receiver.generator()
            if args.snapshot:
                receiver.wav_request()
                deadline=time.monotonic()+3
                while receiver.wav_pending and time.monotonic()<deadline:receiver.pump()
                if receiver.wav_status is None or receiver.wav_status.state.value not in (0,3):
                    raise RuntimeError('WAV output is not idle; board already owned')
                prior={'adc':asdict(receiver.config),'generator':asdict(initial.active),
                       'transport':'SPI','wav_state':receiver.wav_status.state.value}
                prior_path.write_text(json.dumps(prior,indent=2)+'\n')
                print(json.dumps(prior,indent=2));return 0
            prior=json.loads(prior_path.read_text())
            if args.restore:
                receiver.generator(GeneratorConfig(**prior['generator']))
                receiver.configure(Configuration(**prior['adc']))
                recovery=capture(receiver,3)
                final=receiver.generator()
                report.update(recovery=recovery,restored=receiver.config==Configuration(**prior['adc']) and final.active==GeneratorConfig(**prior['generator']))
                report['ok']=report['restored'] and recovery['samples']>0
                return 0 if report['ok'] else 1
            try:
                if not initial.radio_test_hz_capable:raise RuntimeError('Missing RADIO TEST Hz capability')
                for adc,seconds,first,second,tone in (
                    (Configuration(14,40000),10,20525,40750,750),
                    (Configuration(8,1403508),60,20525,40750,750),
                    (Configuration(8,1403508),10,750,20525,0),
                    (Configuration(8,1403508),10,20525,40750,4000)):
                    receiver.configure(adc)
                    wanted=GeneratorConfig(wave=1,mode=3,frequency=first*1000,
                                           final_frequency=second*1000,duration=tone,low=0,high=0)
                    receiver.generator(wanted)
                    case={'adc':asdict(adc),'wanted':asdict(wanted)}
                    report['cases'].append(case)
                    (folder/'radio_hz_installed.json').write_text(json.dumps(report,indent=2)+'\n')
                    print(f'CASE ADC{adc.bits}/{adc.rate}: {first}/{second} Hz, tone {tone} Hz, {seconds}s',flush=True)
                    case.update(capture(receiver,seconds))
                    actual=receiver.generator()
                    case.update(actual=asdict(actual.active),running=actual.running)
                    case['ok']=actual.active==wanted and actual.running and case['samples']>0
                    (folder/'radio_hz_installed.json').write_text(json.dumps(report,indent=2)+'\n')
                    print(f'CASE finished: ok={case["ok"]}, samples={case["samples"]}',flush=True)
                    if not case['ok']:raise RuntimeError('RADIO TEST stopped or configuration differs')
                    receiver.generator(GeneratorConfig(**{**asdict(wanted),'enabled':0}))
            finally:
                receiver.generator(GeneratorConfig(**prior['generator']))
                receiver.configure(Configuration(**prior['adc']))
                report['recovery']=capture(receiver,10)
                final=receiver.generator()
                report['final']={'adc':asdict(receiver.config),'generator':asdict(final.active),'running':final.running}
                report['restored']=report['final']['adc']==prior['adc'] and report['final']['generator']==prior['generator']
                report['restore_integrity_ok']=report['recovery']['samples']>0 and not any(
                    report['recovery']['status'].get(key,0) for key in ('dropped','fatal'))
                report['ok']=report['restored'] and report['restore_integrity_ok'] and len(report['cases'])==4 and all(
                    case.get('ok',False) for case in report['cases'])
    except Exception as error:
        report['error']=str(error)
        if args.snapshot:print(json.dumps(report,indent=2),flush=True)
    finally:
        if not args.snapshot:
            (folder/('radio_hz_recovery.json' if args.restore else 'radio_hz_installed.json')).write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2),flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
