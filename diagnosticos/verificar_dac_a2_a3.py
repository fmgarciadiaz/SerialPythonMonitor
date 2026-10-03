#!/usr/bin/env python3
"""Captura A2/A3 y estima niveles y frecuencia; requiere cableado físico para validar DAC0."""
import csv,json,sys,time
from datetime import datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transport.unoq_acquisition import Configuration
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_usb import Connection
from transport.unoq_switch import Mode


def main():
    samples=[];config=Configuration()
    with Connection('1060031107') as connection:
        connection.socket.settimeout(.01)
        receiver=OutputReceiver(connection,lambda batch:None)
        try:
            receiver.configure(config);receiver.select(Mode.SPI)
            receiver.on_samples=samples.extend
            started=time.monotonic()
            while time.monotonic()-started<5:receiver.pump()
        finally:receiver.close()
    assert len(samples)>4096,'Insuficientes muestras'
    assert all((b[0]-a[0])&0xffffffff==config.period and (b[3]-a[3])&0xffffffff==1 for a,b in zip(samples,samples[1:]))
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/diagnosticos_dac_a2_a3';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(stamp+'.csv')
    with path.open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['Tiempo_us','ADC_IN_A2','ADC_OUT_A3','Muestra']);writer.writerows(samples)
    array=np.asarray(samples,dtype=np.int64);channels={}
    for column,pin in ((1,'A2'),(2,'A3')):
        values=array[:,column];low,high=np.percentile(values,[10,90])
        rising=[];armed=False
        for index,value in enumerate(values):
            if value<=low+0.3*(high-low):armed=True
            elif armed and value>=low+0.7*(high-low):rising.append(index);armed=False
        rising=np.asarray(rising,dtype=np.int64)
        intervals=np.diff(array[rising,0])&0xffffffff
        channels[pin]=dict(min_adc=int(values.min()),max_adc=int(values.max()),low_volts=float(low*3.3/config.maximum),high_volts=float(high*3.3/config.maximum),rising_edges=len(rising),median_frequency_hz=float(1e6/np.median(intervals)) if len(intervals) and np.median(intervals)>0 else None)
    report=dict(bits=config.bits,rate=config.rate,pairs=len(samples),continuity_ok=True,channels=channels,csv=str(path.relative_to(ROOT)),note='A0 excita el circuito; A2 y A3 son puntos de lectura. Estimación con histéresis, no calibración de amplitud.')
    output=ROOT/'diagnosticos/resultados_usb';output.mkdir(exist_ok=True)
    report_path=output/(stamp+'_dac_a2_a3.json');report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(report_path)

if __name__=='__main__':main()
