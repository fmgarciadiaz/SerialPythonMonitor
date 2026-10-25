"""Physical integration: production receiver/scaled batches, transitions and restoration."""
import hashlib
import json
import sys
import struct
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


class MeasuredConnection(Connection):
    """Observe unchanged wire frames alongside the production receiver."""
    def reset_measurement(self, config):
        self.measure_config=config
        self.send_ticks=[];self.queue_peak=0;self.slack_min=0xffffffff

    def read(self):
        data=super().read()
        if not hasattr(self,'measure_buffer'):self.measure_buffer=bytearray()
        self.measure_buffer.extend(data)
        consumed=0
        while len(self.measure_buffer)-consumed>=992:
            offset=consumed;consumed+=992
            config=getattr(self,'measure_config',None)
            if config is None or not config._native:continue
            if struct.unpack_from('<H',self.measure_buffer,offset+6)[0]!=20:continue
            rate,index,_,_,count,bits,channels,ticks,node,_=struct.unpack_from('<IIIIHBBIII',self.measure_buffer,offset+48)
            metrics=struct.unpack_from('<8I',self.measure_buffer,offset+84)
            if (bits,channels,ticks,metrics[0])!=(config.bits,config.channels,config.period,config.node_pairs) or not count:continue
            self.queue_peak=max(self.queue_peak,metrics[2]);self.slack_min=min(self.slack_min,metrics[5])
            if ((index-node*config.node_pairs)&0xffffffff)==0 and metrics[6]:
                self.send_ticks.append(metrics[6])
        del self.measure_buffer[:consumed]
        return data


def main():
    require_exclusive_monitor()
    prior=json.loads((EXP/'sweep.json').read_text())['prior']
    report={'ok':False,'restored':False,'cases':[],'scope':'Production firmware/relay/receiver/scaled timestamps; analog not measured',
            'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path(__file__),ROOT/'monitor/historico/v16/numeric_batch.py',
                                       *sorted((ROOT/'monitor/historico/v16/receiver').glob('*.py'))]}}
    path=EXP/'production_integration.json'
    if '--resume' in sys.argv:
        previous=json.loads(path.read_text())
        assert previous['restored'] and previous.get('error')=='Integrated profile did not retain its measured headroom'
        assert previous['source_hashes'][str(Path(__file__).relative_to(ROOT))]==hashlib.sha256((EXP/'margin_failure_verify_production.py').read_bytes()).hexdigest()
        for name,digest in previous['source_hashes'].items():
            if name!=str(Path(__file__).relative_to(ROOT)):
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
        report['cases']=previous['cases']
        report['resumed_from']=dict(report='margin_failure_production_integration.json',
                                   source_hashes=previous['source_hashes'],
                                   reason='Completed integrity cases retained; headroom is reconciled with production labels')
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
        else:assert np.isfinite(batch.columns['CH1']).all() and np.isfinite(batch.columns['CH2']).all()
        last_time=float(times[-1])
    with MeasuredConnection('1060031107') as c:
        r=OutputReceiver(c,collect,print);r.on_configuration=configured;r.select(Mode.SPI)
        try:
            r.generator(GeneratorConfig(enabled=0))
            profiles=[Configuration(14,250000),Configuration(8,1203007)]
            profiles += [Configuration(p['bits'],160000000//p['ticks']) for p in PROFILES]
            profiles += [Configuration(16,71428),Configuration(14,31250)]
            for config in profiles:
                existing=next((row for row in report['cases'] if row['wire_period']==config.request_period
                               and row['adc']['bits']==config.bits),None)
                if existing is not None:
                    assert existing['seconds']>=(120 if config._native else 10)
                    assert abs(existing['observed_rate']/config.actual_rate-1)<.02
                    assert abs(existing['wall_monotonic_drift'])<2
                    assert existing['status']['dropped']==existing['status']['fatal']==0
                    continue
                r.configure(config);configured(r.config)
                c.reset_measurement(config)
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
                if config._native:
                    budget=config.node_pairs*config.period
                    assert len(c.send_ticks)>=128
                    row['metrics']=dict(send_observations=len(c.send_ticks),
                        mean_send_headroom=1-float(np.mean(c.send_ticks))/budget,
                        queue_peak=c.queue_peak,overwrite_slack_min_us=c.slack_min/160)
                    row['headroom_ok']=(row['metrics']['mean_send_headroom']>=.1
                        and c.queue_peak<4 and c.slack_min>0)
                report['cases'].append(row);save()
                assert abs(row['observed_rate']/config.actual_rate-1)<.02
                assert abs(row['wall_monotonic_drift'])<2
                if config._native and config._native['headroom']:
                    if not row['headroom_ok']:
                        report.setdefault('margin_not_retained',[]).append(dict(adc=asdict(config),wire_period=config.request_period))
                        save()
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
                report['final_mode']=r.mode.name
                report['restored']=report['final_adc']==prior['adc'] and report['final_generator']==prior['generator'] and r.mode==Mode.SPI
                before=r.decoder.pairs;start=time.monotonic()
                try:
                    while time.monotonic()-start<10:r.pump()
                    report['restore_samples']=r.decoder.pairs-before
                    report['restore_integrity_ok']=True
                except Exception as exc:
                    report['restore_integrity_ok']=False
                    report['restore_integrity_error']=str(exc)
            except Exception as exc:report['restore_error']=str(exc)
            save()
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
