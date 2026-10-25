"""Bounded SPI-only V18 modes campaign; run manually with the Q exclusive.

Uses the installed application, readonly baseline capture and exact restoration.
This is a control/transport test: no analog signal quality claim is made.
"""
import argparse
from dataclasses import asdict, is_dataclass, replace
import json
from pathlib import Path
import sys
import tempfile
import time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from monitor.v18.io.receiver_process import ReceiverProcess
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_generator import GeneratorConfig
from monitor.v18.receiver.unoq_native import PROFILES
from monitor.v18.receiver.unoq_switch import Mode, Phase
from monitor.v18.receiver.unoq_wav import State


def pcm_fixture(rate, seconds=5.):
    t=np.arange(round(rate*seconds),dtype=np.float64)/rate
    return np.rint(2048+600*np.sin(2*np.pi*997*t)).astype('<u2')


def configuration_cases():
    """One safe dual legacy rate, then known dual headroom native profiles."""
    cases=[Configuration(14,40000)]
    for bits in (8,10,12,14,16):
        candidates=[p for p in PROFILES if p['bits']==bits and p['channels']==2
                    and p.get('headroom') and not p.get('internal_only')]
        if not candidates:
            cases.append(Configuration(bits,40000))
            continue
        chosen=max(candidates,key=lambda p:p['ticks'])
        cases.append(Configuration(bits,160000000//chosen['ticks']))
    return cases


class Campaign:
    def __init__(self,owner,report):
        self.owner=owner;self.report=report;self.events=[]
    def pump(self):
        for event in self.owner.poll():
            if event['type']=='batch':
                self.report['samples']+=len(event['batch'])
                self.report['batches']+=1
                self.owner.release(event['id'])
            elif event['type']=='error':raise RuntimeError(event['text'])
            elif event['type']=='signal':
                self.events.append(event)
                self.report['signals'].append(dict(name=event['name'],args=event['args']))
                if event['name']=='wav_confirmed':
                    status=event['args'][0]
                    if status.reason or status.state in (State.UNDERRUN,State.FAULT):
                        raise RuntimeError(f'WAV inválido: {status}')
        terminal=self.owner.poll_terminal()
        if terminal is not None:
            self.report['terminal']=terminal
            raise RuntimeError(f'Receptor terminó antes de finalizar modos: {terminal}')
    def wait(self,name,predicate=lambda value:True,timeout=6):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.pump()
            for index,event in enumerate(self.events):
                if event['name']==name and predicate(event['args']):
                    return self.events.pop(index)['args']
            time.sleep(.001)
        raise TimeoutError(f'Sin confirmación {name}')
    def command(self,op,**payload):
        self.pump();self.events.clear()
        self.owner.submit(op,**payload)
    def dwell(self,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:self.pump();time.sleep(.001)


def run(args):
    report=dict(samples=0,batches=0,signals=[],cases=[],terminal=None,ok=False)
    owner=ReceiverProcess(args.serial,Mode.SPI,Configuration(14,40000))
    with tempfile.TemporaryDirectory(prefix='v18-modes-') as directory:
        owner.start()
        campaign=Campaign(owner,report)
        try:
            campaign.wait('acquisition_confirmed',timeout=20)
            campaign.dwell(.2)
            for config in configuration_cases():
                campaign.command('output',mode=Mode.SPI,r4_port=None,config=config)
                campaign.wait('output_confirmed',lambda values:values[0]==int(Mode.SPI))
                campaign.dwell(.35)
                report['cases'].append(dict(kind='configuration',bits=config.bits,rate=config.rate,
                                            wire_period=config.request_period,channels=config.channels,ok=True))
            # Audio exercises run at a modest dual ADC load.
            campaign.command('output',mode=Mode.SPI,r4_port=None,config=Configuration(14,40000))
            campaign.wait('output_confirmed')
            sine=GeneratorConfig(wave=1,frequency=997000,final_frequency=997000,low=900,high=3100)
            for config in (sine,replace(sine,enabled=0)):
                campaign.command('generator',config=config)
                reply=campaign.wait('generator_confirmed',lambda values:values[0].active==config)[0]
                if reply.phase!=Phase.APPLIED or bool(reply.running)!=bool(config.enabled):
                    raise RuntimeError(f'Generador sin APPLIED: {reply}')
                campaign.dwell(.25)
                report['cases'].append(dict(kind='generator',config=asdict(config),ok=True))
            for rate in (20000,40000,50000):
                path=Path(directory)/f'known_pcm_{rate}.npy'
                np.save(path,pcm_fixture(rate),allow_pickle=False)
                campaign.command('levels',amplitude=1.0,offset=1.65)
                campaign.command('wav',opcode=1,codes=dict(kind='npy',path=str(path)),rate=rate)
                initial=campaign.wait('wav_confirmed',lambda values:values[0].rate==rate and values[0].state==State.PLAYING)[0]
                campaign.dwell(.15)
                campaign.command('levels',amplitude=.8,offset=1.6)
                campaign.dwell(.15)
                campaign.command('seek',seconds=.5)
                seeked=campaign.wait('wav_confirmed',lambda values:values[0].session!=initial.session and values[0].state==State.PLAYING)[0]
                campaign.dwell(.15)
                campaign.command('wav',opcode=3,codes=None,rate=rate)
                stopped=campaign.wait('wav_confirmed',lambda values:values[0].state==State.IDLE)[0]
                report['cases'].append(dict(kind='wav',rate=rate,begin_session=initial.session,
                    seek_session=seeked.session,seek_played_absolute=seeked.played,
                    stopped_reason=stopped.reason,ok=True))
        except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
        finally:
            owner.close(timeout=60)
            report['terminal']=report['terminal'] or owner.poll_terminal()
    report['ok']=bool(not report.get('error') and report['terminal'] and
                      report['terminal'].get('ok') and report['terminal'].get('hardware_restored'))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=run(args)
    path=args.output or Path(__file__).resolve().parent/'resultados_v18'/('modes_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    def encode(value):return asdict(value) if is_dataclass(value) else str(value)
    path.write_text(json.dumps(report,indent=2,default=encode)+'\n')
    print(json.dumps(dict(ok=report['ok'],error=report.get('error'),cases=len(report['cases']),
                         terminal=report['terminal'],report=str(path)),indent=2,default=encode))
    return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
