#!/usr/bin/env python3
"""Repite cambios ADC y comprueba continuidad y estabilidad del orden de canales."""
import argparse,csv,json,sys,time
from pathlib import Path
from datetime import datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transport.unoq_usb import Connection
from transport.unoq_acquisition import Configuration
from transport.unoq_generator import GeneratorConfig
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_switch import Mode


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cycles',type=int,default=6)
    args=parser.parse_args();stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/generador_v10'/('channels_'+stamp);folder.mkdir(parents=True)
    report={'cases':[],'error':None,'passed':False,'note':'Comparación relativa de señal completa y filtrada; no asigna puntos del circuito a pines.'}
    samples=[]
    with Connection('1060031107') as connection:
        connection.socket.settimeout(.01);receiver=OutputReceiver(connection,samples.extend)
        def wait(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:receiver.pump()
        try:
            receiver.select(Mode.SPI);receiver.generator(GeneratorConfig(wave=1,frequency=10000))
            baseline=None
            for i,config in enumerate([Configuration(14,31250),Configuration(14,50000),Configuration(16,31250),Configuration(16,50000)]*args.cycles):
                receiver.configure(config);wait(.2);samples.clear();wait(.7)
                a=np.asarray(samples,dtype=np.int64);q=np.percentile(a[:,1:3],[10,90],axis=0)
                spans=(q[1]-q[0])*3.3/config.maximum
                role='A2' if spans[0]>spans[1] else 'A3'
                if baseline is None:baseline=role
                case={'config':{'bits':config.bits,'rate':config.rate},'epoch':receiver.decoder.epoch,'spans_volts':spans.tolist(),
                      'larger_channel':role,'pairs':len(a),'stable':role==baseline}
                report['cases'].append(case);print(json.dumps(case),flush=True)
                if i==0 or role!=baseline:
                    with (folder/f'case_{i}.csv').open('w',newline='') as file:
                        writer=csv.writer(file);writer.writerow(['Tiempo_us','ADC_IN_A2','ADC_OUT_A3','Muestra']);writer.writerows(samples)
                assert role==baseline,'La señal cambió de canal después de reconfigurar ADC'
            report['passed']=True
        except Exception as exc:report['error']=repr(exc);raise
        finally:
            try:
                receiver.generator(GeneratorConfig());receiver.configure(Configuration());receiver.select(Mode.SPI)
                report['restored_default']=True
            except Exception as exc:report['restore_error']=repr(exc)
            receiver.close()
            output=ROOT/'diagnosticos/resultados_usb'/(stamp+'_generator_channels.json')
            output.write_text(json.dumps(report,indent=2)+'\n');print(output)

if __name__=='__main__':main()
