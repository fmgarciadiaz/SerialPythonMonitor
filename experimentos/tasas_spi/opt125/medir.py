#!/usr/bin/env python3
"""Isolated hardware acceptance capture; production firmware/monitor stay unchanged."""
import argparse, importlib, json, sys, time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=('p512','p992'),required=True)
    parser.add_argument('--rate',type=int,default=125000)
    parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--generator',choices=('off','on'),default='off')
    parser.add_argument('--stress',action='store_true')
    args=parser.parse_args()
    if args.seconds<=0:parser.error('seconds debe ser positivo')
    package=f'experimentos.tasas_spi.opt125.{args.variant}.receiver'
    def module(name):return importlib.import_module(package+'.'+name)
    Connection=module('unoq_usb').Connection
    OutputReceiver=module('unoq_config_receiver').OutputReceiver
    Configuration=module('unoq_acquisition').Configuration
    GeneratorConfig=module('unoq_generator').GeneratorConfig
    folder=Path(__file__).resolve().parent/'resultados'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    report={'variant':args.variant,'rate':args.rate,'seconds_requested':args.seconds,'generator':args.generator,'stress':args.stress,'integrity_passed':False,'acceptance_passed':None,'passed':False,'errors':[]}
    count=0;commands=0;before=None;started=None;receiver=None
    try:
        with Connection('1060031107') as connection, (folder/'stream.scp').open('wb') as raw:
            connection.socket.settimeout(.02)
            read=connection.read
            def record_read():
                data=read();raw.write(data);return data
            connection.read=record_read
            receiver=OutputReceiver(connection,lambda samples:None)
            try:
                generator=receiver.generator().active
                before={'configuration':asdict(receiver.config),'generator':asdict(generator)}
                report['before']=before
                receiver.generator(GeneratorConfig(0,int(args.generator=='on'),0,2500,2500,0,4095,1000))
                receiver.configure(Configuration(14,args.rate))
                def consume(samples):
                    nonlocal count
                    count+=len(samples)
                receiver.on_samples=consume
                started=time.monotonic();next_command=started+1
                while time.monotonic()-started<args.seconds:
                    receiver.pump()
                    if args.stress and time.monotonic()>=next_command:
                        # Query status and repeat an identical setting without ADC reset.
                        receiver.generator(GeneratorConfig(0,int(args.generator=='on'),0,2500,2500,0,4095,1000))
                        commands+=1;next_command=time.monotonic()+1
                report.update(pairs=count,elapsed_s=time.monotonic()-started,status=receiver.decoder.status,commands=commands)
                if count<args.rate*args.seconds*.9:raise RuntimeError('Caudal recibido insuficiente')
                if report['status']['dropped'] or report['status']['fatal']:raise RuntimeError('Estado MCU no saludable')
                report['integrity_passed']=True;report['passed']=True
            finally:
                if receiver is not None:
                    report.setdefault('pairs',count)
                    if started is not None:report.setdefault('elapsed_s',time.monotonic()-started)
                    report['status']=receiver.decoder.status
                    receiver.on_samples=lambda samples:None
                    if before is not None:
                        try:
                            receiver.configure(Configuration(**before['configuration']))
                            receiver.generator(GeneratorConfig(**before['generator']))
                            report['after']={'configuration':asdict(receiver.config),'generator':asdict(receiver.generator().active)}
                            if before!=report['after']:raise RuntimeError('Restauracion de perfil diferente')
                        except Exception as exc:report['errors'].append('Restore: '+str(exc));report['passed']=False
                    receiver.close()
    except Exception as exc:
        report['errors'].append(str(exc));report['passed']=False
    (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True);print(folder,flush=True)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
