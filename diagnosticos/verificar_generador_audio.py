#!/usr/bin/env python3
"""Verifica salida real 1/10/20 kHz, barridos y continuidad ADC; conserva capturas."""
import csv
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from transport.unoq_acquisition import Configuration
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_generator import GeneratorConfig
from transport.unoq_switch import Mode, Phase
from transport.unoq_usb import Connection


def main():
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/generador_audio'/stamp
    folder.mkdir(parents=True)
    report={'passed':False,'error':None,'cases':[], 'capture_folder':str(folder.relative_to(ROOT))}
    samples=[]
    with Connection('1060031107') as connection:
        connection.socket.settimeout(.01)
        receiver=OutputReceiver(connection,samples.extend)
        def wait(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:receiver.pump()
        def capture(name,config,seconds=1.2,settle=.15):
            # A short pulse can reach the ADC while generator() is waiting for its ACK.
            samples.clear()
            applied=receiver.generator(config)
            assert applied.phase==Phase.APPLIED,applied
            if settle:
                wait(settle);samples.clear()
            wait(seconds)
            data=np.asarray(samples,dtype=np.int64)
            assert len(data)>1000,'No hubo muestras suficientes'
            assert np.all((np.diff(data[:,0])&0xffffffff)==receiver.config.period)
            assert np.all((np.diff(data[:,3])&0xffffffff)==1)
            state=receiver.generator()
            result={'name':name,'generator':asdict(config),'adc':asdict(receiver.config),
                    'pairs':len(data),'running':state.running,'continuity_ok':True}
            if config.mode==0 and config.wave<4 and config.enabled:
                v=data[:,2].astype(float);v-=v.mean()
                spectrum=abs(np.fft.rfft(v*np.hanning(len(v))))
                spectrum[0]=0
                measured=np.fft.rfftfreq(len(v),receiver.config.period/1e6)[spectrum.argmax()]
                result['a3_frequency_hz']=float(measured)
                assert abs(measured-config.frequency/1000)<max(1,config.frequency/1000*.01),result
                result['a3_vpp_nominal']=float(np.ptp(data[:,2])*3.3/receiver.config.maximum)
                assert result['a3_vpp_nominal']>.3,result
            elif config.mode or config.wave==4:
                assert not state.running,result
                if config.wave==4:
                    high=np.flatnonzero(data[:,2]>receiver.config.maximum*.5)
                    assert len(high)>0,'No se observó el pulso en A3'
                    width=(high[-1]-high[0]+1)*receiver.config.period/1000
                    result['pulse_width_ms']=float(width)
                    assert abs(width-config.duration)<.8,result
            # Preserve 4096 original pairs per case; validate the entire captured interval.
            path=folder/f'{name}.csv'
            with path.open('w',newline='') as file:
                writer=csv.writer(file);writer.writerow(['Tiempo_us','ADC_IN_A2','ADC_OUT_A3','Muestra'])
                writer.writerows(data[:4096].tolist())
            report['cases'].append(result)
            print(json.dumps(result),flush=True)
        try:
            receiver.select(Mode.SPI)
            receiver.configure(Configuration(14,62500))
            for wave in range(4):
                for frequency in (1000000,10000000,20000000):
                    capture(f'wave{wave}_{frequency//1000}Hz_14bit',GeneratorConfig(wave=wave,frequency=frequency))
            receiver.configure(Configuration(16,50000))
            for frequency in (1000000,10000000,20000000):
                capture(f'sine_{frequency//1000}Hz_16bit',GeneratorConfig(wave=1,frequency=frequency))
            for mode in (1,2):
                capture(f'sweep_mode{mode}_20k',GeneratorConfig(wave=1,mode=mode,frequency=1000000,
                        final_frequency=20000000,duration=1000),seconds=1.3,settle=0)
            capture('pulse_5ms',GeneratorConfig(wave=4,duration=5),seconds=.3,settle=0)
            receiver.generator(GeneratorConfig(wave=1,frequency=20000000))
            wait(.2);samples.clear();start=time.monotonic();progress=start+10
            while time.monotonic()-start<60:
                receiver.pump()
                # Decoder validates continuously. Keep only bounded tail during the long run.
                if len(samples)>8192:del samples[:-4096]
                if time.monotonic()>=progress:
                    print(f'16 bits / 50 kHz + DAC 20 kHz: {time.monotonic()-start:.0f} s válidos',flush=True)
                    progress+=10
            report['long_run']={'seconds':time.monotonic()-start,'bits':16,'rate':50000,'dac_hz':20000,
                                'strict_continuity_ok':True}
            report['passed']=True
        except Exception as exc:
            report['error']=repr(exc)
        finally:
            try:
                receiver.generator(GeneratorConfig());receiver.configure(Configuration());receiver.select(Mode.SPI)
                report['restored_default']=True
            except Exception as exc:report['restore_error']=repr(exc)
            receiver.close()
            output=ROOT/'diagnosticos/resultados_usb'/f'{stamp}_generador_audio.json'
            output.write_text(json.dumps(report,indent=2)+'\n');print(output,flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
