"""Bounded installation check: DMA RADIO TEST at zero amplitude, restore prior ADC/DAC."""
import json,time,sys
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode


def main():
    folder=ROOT/'diagnosticos/resultados_v17'
    prior=json.loads((folder/'radio_test_prior.json').read_text())
    report={'scope':'Installed RADIO TEST protocol/DMA with zero DAC amplitude; no analog loopback claim',
            'cases':[],'restored':False,'ok':False}
    try:
        with Connection('1060031107') as c:
            r=OutputReceiver(c,lambda x:None);r.decoder.numeric=True;r.select(Mode.SPI)
            try:
                initial=r.generator()
                report['radio_test_capable']=initial.radio_test_capable
                if not initial.radio_test_capable:raise RuntimeError('Firmware does not advertise RADIO TEST')
                r.configure(Configuration(**prior['adc']))
                for first,second,tone in ((20,40,1),(21,40,2),(21,41,0)):
                    wanted=GeneratorConfig(wave=1,enabled=1,mode=3,frequency=first*1000000,
                        final_frequency=second*1000000,duration=tone*1000,low=0,high=0)
                    reply=r.generator(wanted)
                    start=time.monotonic()
                    while time.monotonic()-start<.5:r.pump()
                    actual=r.generator()
                    case={'wanted':asdict(wanted),'actual':asdict(actual.active),'running':actual.running}
                    case['ok']=actual.active==wanted and actual.running
                    report['cases'].append(case)
                    if not case['ok']:raise RuntimeError('RADIO TEST configuration/DMA failed')
            finally:
                r.generator(GeneratorConfig(**prior['generator']))
                r.configure(Configuration(**prior['adc']))
                before=r.decoder.pairs;start=time.monotonic()
                while time.monotonic()-start<10:r.pump()
                final=r.generator()
                report['final']={'adc':asdict(r.config),'generator':asdict(final.active),'running':final.running}
                report['recovery_samples']=r.decoder.pairs-before
                report['status']=r.decoder.status
                report['restored']=report['final']['adc']==prior['adc'] and report['final']['generator']==prior['generator']
                report['integrity_ok']=report['recovery_samples']>0 and not r.decoder.status.get('dropped',0) and not r.decoder.status.get('fatal',0)
        report['ok']=report['restored'] and report['integrity_ok'] and all(x['ok'] for x in report['cases'])
    except Exception as exc:report['error']=str(exc)
    (folder/'radio_test_installed.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
