#!/usr/bin/env python3
"""Verify all offered rates via SPI, ADC bits and UART at both rate extremes."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transport.unoq_usb import Connection
from transport.unoq_config_receiver import OutputReceiver
from transport.unoq_acquisition import Configuration,RATES,BITS
from transport.unoq_switch import Mode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--r4-port',required=True)
    parser.add_argument('--oversampling',action='store_true',help='Ensayar los perfiles de 16 bits en SPI y UART')
    parser.add_argument('--min-rate',type=int,default=1000)
    args=parser.parse_args()
    rows=[];capture=[]
    try:
        with Connection(args.serial) as connection:
            connection.socket.settimeout(0.01)
            receiver=OutputReceiver(connection,capture.extend)
            try:
                profiles=[(14,rate,Mode.SPI) for rate in RATES]
                profiles += [(bits,31250,mode) for bits in BITS if bits != 16 for mode in (Mode.SPI,Mode.UART)]
                profiles += [(8,1000,Mode.UART)]
                if args.oversampling:
                    profiles=[(16,rate,mode) for rate in RATES if args.min_rate<=rate<=50000 for mode in (Mode.SPI,Mode.UART) if mode==Mode.SPI or rate<=31250]
                    profiles.append((14,31250,Mode.SPI))
                for bits,rate,mode in profiles:
                    config=Configuration(bits,rate)
                    receiver.configure(config)
                    receiver.select(mode,args.r4_port)
                    capture.clear();started=time.monotonic()
                    # Collect at least two nodes. At 1 kHz a node takes 2.048 s.
                    deadline=started+max(5,8192/rate+1)
                    while len(capture)<4096 and time.monotonic()<deadline: receiver.pump()
                    if len(capture)<4096: raise TimeoutError('No llegaron dos nodos de muestras')
                    row=dict(bits=bits,rate=rate,mode=mode.name,pairs=len(capture),epoch=receiver.decoder.epoch,
                             non_multiple_of_four=sum(a%4!=0 or b%4!=0 for _,a,b,_ in capture),
                             min_adc=min(min(a,b) for _,a,b,_ in capture),max_adc=max(max(a,b) for _,a,b,_ in capture),
                             period_us=config.period,elapsed_seconds=time.monotonic()-started,
                             timestamps_ok=all((b[0]-a[0])&0xffffffff==config.period for a,b in zip(capture,capture[1:])),
                             indices_ok=all((b[3]-a[3])&0xffffffff==1 for a,b in zip(capture,capture[1:])),
                             range_ok=all(a<=config.maximum and b<=config.maximum for _,a,b,_ in capture))
                    row['passed']=row['timestamps_ok'] and row['indices_ok'] and row['range_ok']
                    rows.append(row);print(json.dumps(row),flush=True)
                    if not row['passed']: raise RuntimeError('Perfil físico inválido')
                receiver.configure(Configuration());receiver.select(Mode.SPI)
            finally:
                receiver.on_samples=lambda samples:None
                try: receiver.configure(Configuration());receiver.select(Mode.SPI)
                finally: receiver.close()
        report=dict(profiles=rows,passed=all(r['passed'] for r in rows) and len(rows)==len(profiles),error=None)
    except Exception as exc:
        report=dict(profiles=rows,passed=False,error=str(exc))
    output=ROOT/'diagnosticos/resultados_usb';output.mkdir(exist_ok=True)
    path=output/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_acquisition.json')
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(path)
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
