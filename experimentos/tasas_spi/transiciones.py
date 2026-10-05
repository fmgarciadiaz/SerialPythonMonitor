#!/usr/bin/env python3
"""Exercise native/oversampling transitions and DAC commands at measured fast Fs."""
import sys,json,time
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experimentos.tasas_spi.receiver.unoq_usb import Connection
from experimentos.tasas_spi.receiver.unoq_config_receiver import OutputReceiver
from experimentos.tasas_spi.receiver.unoq_acquisition import Configuration
from experimentos.tasas_spi.receiver.unoq_generator import GeneratorConfig
from experimentos.tasas_spi.receiver.unoq_switch import Mode

def main():
    report={'segments':[],'errors':[]};before=None;gen=None
    path=ROOT/'experimentos/tasas_spi/resultados'/('transiciones_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    try:
        with Connection('1060031107') as c:
            c.socket.settimeout(.01);r=OutputReceiver(c,lambda samples:None)
            try:
                gen=r.generator().active;before=r.config;r.select(Mode.SPI)
                report['before']={'acquisition':asdict(before),'generator':asdict(gen)}
                profiles=[Configuration(14,100000),Configuration(16,50000),Configuration(14,100000),Configuration(8,100000),Configuration(10,100000),Configuration(12,100000),Configuration(14,100000)]*2
                trials=[(config,2000,1) for config in profiles]
                trials += [(Configuration(14,100000),freq,on) for freq,on in ((10000,1),(20000,1),(20000,0),(2000,1))]
                for config,freq,on in trials:
                    r.on_samples=lambda samples:None;r.configure(config)
                    r.generator(GeneratorConfig(1,on,0,freq*1000,freq*1000,500,3500,1000))
                    last=None;count=0;gaps=0;invalid=0
                    def collect(samples):
                        nonlocal last,count,gaps,invalid
                        for timestamp,a,b,index in samples:
                            if last is not None and (((timestamp-last[0])&0xffffffff)!=config.period or ((index-last[1])&0xffffffff)!=1):gaps+=1
                            invalid+=int(a>config.maximum or b>config.maximum);last=(timestamp,index);count+=1
                    r.on_samples=collect;start=time.monotonic()
                    while time.monotonic()-start<3:r.pump()
                    elapsed=time.monotonic()-start;status=r.decoder.status
                    row={'config':asdict(config),'frequency_hz':freq,'enabled':on,'seconds':elapsed,'pairs':count,'gaps':gaps,'bad_range':invalid,'hardware_status':status}
                    row['passed']=count>config.rate*2.8 and gaps==invalid==0 and status['fatal']==status['dropped']==0
                    report['segments'].append(row);print(json.dumps(row),flush=True)
                    if not row['passed']:raise RuntimeError('Invalid continuity, rate or hardware state')
            finally:
                r.on_samples=lambda samples:None
                try:
                    if before is not None:r.configure(before)
                    if gen is not None:r.generator(gen)
                    report['after']={'acquisition':asdict(r.config),'generator':asdict(r.generator().active)}
                    if report['after']!=report.get('before'):report['errors'].append('Restore mismatch')
                except Exception as exc:report['errors'].append(f'Restore: {exc}')
                r.close()
    except Exception as exc:report['errors'].append(str(exc))
    report['passed']=not report['errors'] and len(report['segments'])==18 and all(s['passed'] for s in report['segments'])
    path.write_text(json.dumps(report,indent=2)+'\n');print(path,flush=True)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
