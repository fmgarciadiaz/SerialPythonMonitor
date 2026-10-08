"""Run the calibration matrix with a separate connection for each ADC profile."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.calibrate_bode import profiles
from monitor.v15.app import RATES as UI_RATES
from monitor.v15.receiver.unoq_acquisition import BITS
from monitor.v15.receiver.unoq_usb import adb

METHODS=('tone','sweep','chirp','pulse_h1')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107')
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--loopback-confirmed',action='store_true',required=True)
    parser.add_argument('--bits',type=int,nargs='+',choices=BITS)
    parser.add_argument('--rates',type=int,nargs='+',choices=UI_RATES)
    args=parser.parse_args()
    args.report=args.report.resolve()
    folder=args.report.parent/'calibracion_logs';folder.mkdir(exist_ok=True)
    for config in profiles():
        if config.rate not in (args.rates or UI_RATES):continue
        if args.bits and config.bits not in args.bits:continue
        report=json.loads(args.report.read_text())
        done={(r['bits'],r['rate'],r['method']) for r in report['results']}
        if all((config.bits,config.rate,m) in done for m in METHODS):continue
        log=folder/f'{args.report.stem}_{config.bits}bit_{config.rate}.log'
        print('PERFIL',config.bits,config.rate,flush=True)
        command=[sys.executable,str(ROOT/'tools/calibrate_bode.py'),'--serial',args.serial,
                 '--loopback-confirmed','--resume-report',str(args.report),
                 '--bits',str(config.bits),'--rates',str(config.rate)]
        with log.open('w') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode:
            report=json.loads(args.report.read_text())
            done={(r['bits'],r['rate'],r['method']) for r in report['results']}
            try:relay_log=adb('-s',args.serial,'shell','docker logs --tail 40 serialmonitor-usb-stream 2>&1')
            except Exception as exc:relay_log=str(exc)
            for method in METHODS:
                if (config.bits,config.rate,method) not in done:
                    report['results'].append(dict(bits=config.bits,rate=config.rate,method=method,
                        accepted=False,reason='Flujo interrumpido: no se completó la calibración del perfil',
                        attempt_log=str(log.relative_to(ROOT)) if log.is_relative_to(ROOT) else str(log),
                        relay_log=relay_log))
            args.report.write_text(json.dumps(report,indent=2)+'\n')
            print('RECUPERANDO Q tras fallo de perfil',config.bits,config.rate,flush=True)
            import os
            environment=dict(os.environ,UNOQ_SERIAL=args.serial)
            firmware={'scope-pulse-us-v13-main-1':'v13_pulse',
                      'scope-wav-v12-audio-main-1':'v12_audio'}.get(report['instrument'].get('app'))
            if firmware is None:raise RuntimeError('No se identificó la variante instalada para recuperarla')
            with log.open('a') as stream:
                recovery=subprocess.run([sys.executable,str(ROOT/'tools/usb_stream.py'),'start',
                    '--firmware',firmware],env=environment,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
            if recovery.returncode:raise RuntimeError('No se recuperó el Q; revisar '+str(log))
        report=json.loads(args.report.read_text())
        print('PROGRESO',len(report['results']),sum(r['accepted'] for r in report['results']),flush=True)
    # Separate final restoration also verifies recovery after the last profile.
    subprocess.run([sys.executable,str(ROOT/'tools/calibrate_bode.py'),'--serial',args.serial,
        '--loopback-confirmed','--restore-only','--resume-report',str(args.report)],check=True)
    print('MATRIZ COMPLETA',args.report,flush=True)

if __name__=='__main__':main()
