#!/usr/bin/env python3
"""Verifica generador en Q con el circuito conectado; conserva CSV de ambas entradas."""
import argparse,csv,json,sys,time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transport.unoq_acquisition import Configuration
from transport.unoq_generator import GeneratorConfig, WAVES
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_switch import Mode,Phase
from transport.unoq_usb import Connection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r4-port',help='Prueba UART adicional; requiere TX Q a RX R4 y masa común')
    args=parser.parse_args()
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/generador_v10'/stamp;folder.mkdir(parents=True)
    report={'stages':[],'error':None,'passed':False,'capture_folder':str(folder.relative_to(ROOT))}
    samples=[]
    with Connection('1060031107') as connection:
        connection.socket.settimeout(.01)
        receiver=OutputReceiver(connection,samples.extend)
        def wait(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:receiver.pump()
        def stage(name,c,seconds=2,settle=.3):
            reply=receiver.generator(c)
            assert reply.phase==Phase.APPLIED and reply.active==c
            wait(settle);samples.clear();wait(seconds)
            array=np.asarray(samples,dtype=np.int64)
            assert len(array)>1000
            assert np.all((np.diff(array[:,0])&0xffffffff)==receiver.config.period)
            assert np.all((np.diff(array[:,3])&0xffffffff)==1)
            path=folder/(name+'.csv')
            with path.open('w',newline='') as file:
                writer=csv.writer(file);writer.writerow(['Tiempo_us','ADC_IN_A2','ADC_OUT_A3','Muestra']);writer.writerows(samples)
            state=receiver.generator()
            entry={'name':name,'config':asdict(c),'adc':asdict(receiver.config),'pairs':len(samples),
                   'continuity_ok':True,'running_after':state.running,'a3_min':int(array[:,2].min()),'a3_max':int(array[:,2].max())}
            if c.mode==0 and c.wave<4 and c.enabled:
                values=array[:,2].astype(float);values-=values.mean()
                freqs=np.fft.rfftfreq(len(values),receiver.config.period/1e6)
                magnitudes=np.abs(np.fft.rfft(values));magnitudes[0]=0
                measured=float(freqs[np.argmax(magnitudes)])
                entry['a3_dominant_frequency_hz']=measured
                assert abs(measured-c.frequency/1000)<max(.6,c.frequency/1000*.03),(name,measured)
                assert entry['a3_max']-entry['a3_min']>receiver.config.maximum*.3
            if c.mode or c.wave==4:assert not state.running
            if not c.enabled:assert not state.running
            report['stages'].append(entry);print(json.dumps(entry),flush=True)
        try:
            receiver.configure(Configuration());receiver.select(Mode.SPI)
            for wave in range(4):stage(WAVES[wave],GeneratorConfig(wave=wave,frequency=10000))
            stage('square_100Hz',GeneratorConfig(frequency=100000))
            stage('amplitude_offset',GeneratorConfig(frequency=10000,low=993,high=3102))
            stage('sweep',GeneratorConfig(wave=1,mode=1,frequency=5000,final_frequency=50000,duration=1000),seconds=1.4,settle=0)
            stage('chirp',GeneratorConfig(wave=1,mode=2,frequency=5000,final_frequency=50000,duration=1000),seconds=1.4,settle=0)
            stage('pulse',GeneratorConfig(wave=4,duration=200),seconds=.6,settle=0)
            stage('off',GeneratorConfig(enabled=0),seconds=.5)
            for bits in (14,16):
                receiver.configure(Configuration(bits,50000))
                stage(f'sine_{bits}bit_50k',GeneratorConfig(wave=1,frequency=10000))
            if args.r4_port:
                receiver.configure(Configuration());receiver.select(Mode.UART,args.r4_port)
                stage('uart_sine',GeneratorConfig(wave=1,frequency=10000))
                stage('uart_pulse',GeneratorConfig(wave=4,duration=200),seconds=.6,settle=0)
            report['passed']=True
        except Exception as exc:
            report['error']=repr(exc)
            raise
        finally:
            try:
                receiver.generator(GeneratorConfig())
                receiver.configure(Configuration());receiver.select(Mode.SPI)
                report['restored_default']=True
            except Exception as exc:report['restore_error']=repr(exc)
            receiver.close()
            output=ROOT/'diagnosticos/resultados_usb'/(stamp+'_generador_v10.json')
            output.write_text(json.dumps(report,indent=2)+'\n');print(output)

if __name__=='__main__':main()
