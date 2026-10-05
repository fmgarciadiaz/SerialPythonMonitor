#!/usr/bin/env python3
"""Isolated high-rate receiver: binary captures, continuity, tone fit, restore."""
import argparse,csv,json,sys,time
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experimentos.tasas_spi.receiver.unoq_usb import Connection
from experimentos.tasas_spi.receiver.unoq_config_receiver import OutputReceiver
from experimentos.tasas_spi.receiver.unoq_acquisition import Configuration
from experimentos.tasas_spi.receiver.unoq_generator import GeneratorConfig
from experimentos.tasas_spi.receiver.unoq_switch import Mode

DTYPE=np.dtype([('timestamp_us','<u4'),('adc_in','<u2'),('adc_out','<u2'),('index','<u4')])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rates',type=int,nargs='+',default=[62500,100000,125000,200000,250000])
    p.add_argument('--bits',type=int,nargs='+',default=[14])
    p.add_argument('--seconds',type=float,default=10)
    p.add_argument('--frequency',type=float,default=2000)
    p.add_argument('--serial',default='1060031107')
    a=p.parse_args()
    if a.seconds<=0: p.error('seconds debe ser positivo')
    profiles=[Configuration(bits,rate) for bits in a.bits for rate in a.rates]
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'experimentos/tasas_spi/resultados'/stamp;folder.mkdir(parents=True)
    report={'profiles':[],'passed':False,'errors':[],'capture':str(folder.relative_to(ROOT))}
    before=None;previous_generator=None;analyses=[]
    try:
        with Connection(a.serial) as c:
            c.socket.settimeout(.02)
            r=OutputReceiver(c,lambda samples:None)
            try:
                previous_generator=r.generator().active
                if r.decoder.config is None: raise RuntimeError('Requiere muestras SPI iniciales')
                before=r.config
                report['before']={'acquisition':asdict(before),'generator':asdict(previous_generator)}
                r.select(Mode.SPI)
                tone=GeneratorConfig(1,1,0,round(a.frequency*1000),round(a.frequency*1000),500,3500,1000)
                r.generator(tone)
                for config in profiles:
                    r.on_samples=lambda samples:None
                    row={'bits':config.bits,'rate':config.rate,'period_us':config.period,'sampling_cycles':config.sampling_cycles,'passed':False}
                    report['profiles'].append(row)
                    try:
                        r.configure(config)
                        last=None;count=0;gaps=0;bad_range=0;recent=[]
                        path=folder/f'{config.bits}bits_{config.rate}Hz.bin'
                        with path.open('wb') as stream:
                            def consume(samples):
                                nonlocal last,count,gaps,bad_range,recent
                                if not samples:return
                                v=np.asarray(samples,dtype=np.uint32)
                                if last is not None:
                                    gaps += int(((int(v[0,0])-last[0])&0xffffffff)!=config.period or ((int(v[0,3])-last[1])&0xffffffff)!=1)
                                gaps += int(np.count_nonzero(np.diff(v[:,0])!=config.period)+np.count_nonzero(np.diff(v[:,3])!=1))
                                bad_range += int(np.count_nonzero(v[:,1:3]>config.maximum))
                                last=(int(v[-1,0]),int(v[-1,3]));count+=len(v)
                                out=np.empty(len(v),dtype=DTYPE)
                                for col,name in enumerate(DTYPE.names):out[name]=v[:,col]
                                stream.write(out.tobytes())
                                recent.extend(samples)
                                if len(recent)>16384:recent=recent[-16384:]
                            r.on_samples=consume;started=time.monotonic()
                            while time.monotonic()-started<a.seconds:r.pump()
                        elapsed=time.monotonic()-started
                        status=r.decoder.status or {}
                        row.update(pairs=count,seconds=elapsed,received_pairs_per_second=count/elapsed,gaps=gaps,bad_range=bad_range,
                                   hardware_status=status,binary=str(path.relative_to(ROOT)))
                        analyses.append((row,config,recent))
                        row['passed']=gaps==0 and bad_range==0 and count>=config.rate*(a.seconds-.5) and status.get('fatal',0)==0 and status.get('dropped',0)==0
                        with (folder/f'{config.bits}bits_{config.rate}Hz_preview.csv').open('w',newline='') as f:
                            writer=csv.writer(f);writer.writerow(['timestamp_us','ADC_IN','ADC_OUT','index']);writer.writerows(recent[:4096])
                        print(json.dumps(row),flush=True)
                        if not row['passed']:raise RuntimeError('Continuidad, caudal o estado inválidos')
                    except Exception as exc:
                        row['error']=str(exc);row['hardware_status']=r.decoder.status
                        report['errors'].append(f'{config.bits}/{config.rate}: {exc}')
                        print(json.dumps(row),flush=True)
                        break
            finally:
                r.on_samples=lambda samples:None
                try:
                    if before is not None:r.configure(before)
                    if previous_generator is not None:r.generator(previous_generator)
                    report['after']={'acquisition':asdict(r.config),'generator':asdict(r.generator().active)}
                    if report.get('before')!=report['after']:report['errors'].append('Restauración distinta del estado inicial')
                except Exception as exc:report['errors'].append(f'Restauración: {exc}')
                r.close()
    except Exception as exc:report['errors'].append(str(exc))
    # Fit tones after closing the stream: offline analysis must not backpressure the relay.
    for row,config,recent in analyses:
        v=np.asarray(recent,dtype=float)
        t=((v[:,0].astype(np.int64)-int(v[0,0])) & 0xffffffff)*1e-6
        yinput=v[:,1]/config.maximum*3.3
        def basis_for(f):return np.column_stack([np.cos(2*np.pi*f*t),np.sin(2*np.pi*f*t),np.ones(len(t))])
        def loss(f):
            basis=basis_for(f);fit=np.linalg.lstsq(basis,yinput,rcond=None)[0]
            return float(np.mean((yinput-basis@fit)**2))
        freq=np.fft.rfftfreq(len(t),1/config.rate)
        energy=abs(np.fft.rfft((yinput-yinput.mean())*np.hanning(len(t))))
        chosen=np.flatnonzero((freq>a.frequency*.9)&(freq<a.frequency*1.1))
        peak=freq[chosen[np.argmax(energy[chosen])]]
        left=max(1,peak-config.rate/len(t));right=peak+config.rate/len(t)
        golden=(5**.5-1)/2
        for _ in range(28):
            f1=right-golden*(right-left);f2=left+golden*(right-left)
            if loss(f1)<loss(f2):right=f2
            else:left=f1
        fitted_frequency=(left+right)/2
        basis=basis_for(fitted_frequency)
        channels=[]
        for col in (1,2):
            y=v[:,col]/config.maximum*3.3;fit=np.linalg.lstsq(basis,y,rcond=None)[0]
            channels.append({'amplitude_peak_v':float(np.hypot(*fit[:2])),'offset_v':float(fit[2]),'residual_rms_v':float(np.std(y-basis@fit))})
        row.update(channels=channels,fitted_frequency_hz=fitted_frequency)
        row['analog_passed']=all(.8 < channel['amplitude_peak_v'] < 1.5 and channel['residual_rms_v'] < .1 for channel in channels) and .95 < channels[1]['amplitude_peak_v']/max(channels[0]['amplitude_peak_v'],1e-12) < 1.05
        print(json.dumps({'bits':row['bits'],'rate':row['rate'],'analog_passed':row['analog_passed'],'channels':channels,'fitted_frequency_hz':fitted_frequency}),flush=True)
    report['passed']=not report['errors'] and len(report['profiles'])==len(profiles) and all(row['passed'] for row in report['profiles'])
    (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(folder/'informe.json',flush=True)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
