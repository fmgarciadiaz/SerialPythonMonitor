"""Physical integration: production receiver/scaled batches, transitions and restoration."""
import hashlib
import json
import sys
import time
from pathlib import Path
from dataclasses import asdict
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from monitor.historico.v16.receiver.unoq_native import PROFILES
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.numeric_batch import NumericBatch,SampleClock
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

EXP=Path(__file__).resolve().parent


def main():
    require_exclusive_monitor()
    prior=json.loads((EXP/'prior.json').read_text())
    report={'ok':False,'restored':False,'cases':[],'scope':'Production firmware/relay/receiver/scaled timestamps; analog not measured',
            'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path(__file__),ROOT/'monitor/historico/v16/numeric_batch.py',
                                       *sorted((ROOT/'monitor/historico/v16/receiver').glob('*.py'))]}}
    path=EXP/'production_integration.json'
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    clock=SampleClock();last_time=None
    def configured(config):
        nonlocal clock,last_time
        clock=SampleClock(config.timestamp_hz);last_time=None
    def collect(rows):
        nonlocal last_time
        batch=NumericBatch(rows,r.config.maximum,clock,r.config.channels)
        times=batch.columns['Tiempo (us)']
        assert np.all(np.abs(np.diff(times)-r.config.dt_us)<1e-6)
        if last_time is not None:assert abs(times[0]-last_time-r.config.dt_us)<1e-6
        if r.config.channels==1:assert np.isnan(batch.columns['CH2']).all()
        last_time=float(times[-1])
    with Connection('1060031107') as c:
        r=OutputReceiver(c,collect,print);r.on_configuration=configured;r.select(Mode.SPI)
        try:
            r.generator(GeneratorConfig(enabled=0))
            profiles=[Configuration(14,250000),Configuration(8,1203007)]
            profiles += [Configuration(p['bits'],160000000//p['ticks']) for p in PROFILES]
            profiles += [Configuration(16,71428),Configuration(14,31250)]
            for config in profiles:
                r.configure(config);configured(r.config)
                before=r.decoder.pairs;start=time.monotonic();wall=time.time();next_log=start+30
                seconds=120 if config._native else 10
                while time.monotonic()-start<seconds:
                    r.pump()
                    if time.monotonic()>=next_log:
                        print(f'PRODUCTION ADC{config.bits}/{config.rate} {time.monotonic()-start:.0f}s',flush=True)
                        next_log+=30
                elapsed=time.monotonic()-start;count=r.decoder.pairs-before
                row=dict(adc=asdict(config),wire_period=config.request_period,channels=config.channels,
                         seconds=elapsed,samples=count,observed_rate=count/elapsed,
                         wall_monotonic_drift=time.time()-wall-elapsed,status=r.decoder.status)
                report['cases'].append(row);save()
                assert abs(row['observed_rate']/config.actual_rate-1)<.02
                assert abs(row['wall_monotonic_drift'])<2
            report['ok']=True
        except BaseException as exc:
            report['error']=str(exc);report['last_status']=r.decoder.status
            raise
        finally:
            try:
                r.on_samples=lambda rows:None
                r.configure(Configuration(**prior['adc']))
                r.generator(GeneratorConfig(**prior['generator']))
                report['final_adc']=asdict(r.config);report['final_generator']=asdict(r.generator().active)
                report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator']
            except Exception as exc:report['restore_error']=str(exc)
            save()
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
