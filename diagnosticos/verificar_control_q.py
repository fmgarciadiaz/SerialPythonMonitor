#!/usr/bin/env python3
"""Comprueba ida y vuelta PC → USB → SPI → MCU mientras continúa el ADC."""
from datetime import datetime
import argparse
import json
import socket
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from transport.unoq_usb import Connection
from transport.unoq_control import StatusSession, status_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--requests',type=int,default=100)
    args=parser.parse_args()
    if not 1<=args.requests<=10000: parser.error('Cantidad de consultas inválida')
    responses=[];error=None;session=None;rejections=[]
    try:
        with Connection(args.serial) as connection:
            session=StatusSession(connection)
            for i in range(args.requests):
                responses.append(session.query(fragmented=i%2==1))
        # A malformed or abandoned command must not reach the MCU or stop ADC.
        for kind in ('bad_crc','partial'):
            with Connection(args.serial) as connection:
                packet=bytearray(status_request(0x8abc1234))
                packet[-1]^=1
                connection.socket.sendall(packet if kind=='bad_crc' else packet[:17])
                deadline=time.monotonic()+3
                rejected=False
                while time.monotonic()<deadline:
                    try:
                        data=connection.socket.recv(65536)
                    except socket.timeout:
                        continue
                    if not data:
                        rejected=True;break
                rejections.append(dict(kind=kind,rejected=rejected))
                if not rejected:raise RuntimeError(f'No se rechazó {kind}')
            with Connection(args.serial) as connection:
                # Decoder checks hardware error counters too, including bad PINGs.
                StatusSession(connection).query()
    except Exception as exc:
        error=str(exc)
    report=dict(requested=args.requests,acknowledged=len(responses),error=error,
                verified_blocks=session.decoder.blocks if session else 0,
                verified_pairs=session.decoder.pairs if session else 0,
                max_latency_ms=max((r['latency_ms'] for r in responses),default=None),
                responses=responses,rejections=rejections)
    report['pass']=len(responses)==args.requests and error is None and len(rejections)==2
    folder=ROOT/'diagnosticos/resultados_usb';folder.mkdir(exist_ok=True)
    path=folder/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_control.json')
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='responses'},indent=2))
    print(path)
    return 0 if report['pass'] else 1


if __name__=='__main__':
    raise SystemExit(main())
