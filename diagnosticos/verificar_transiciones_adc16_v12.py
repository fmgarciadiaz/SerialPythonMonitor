import sys,time,json
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnosticos.verificar_adc16_62k5 import wait_configuration
from monitor.v12.receiver.unoq_usb import Connection
from monitor.v12.receiver.unoq_config_receiver import OutputReceiver
from monitor.v12.receiver.unoq_acquisition import Configuration
folder=(ROOT/'capturas/adc16_rate')/('transitions_'+datetime.now().strftime('%Y%m%d_%H%M%S'));folder.mkdir(parents=True);report={'passed':False,'profiles':[],'errors':[]}
with Connection('1060031107') as c,(folder/'stream.scp').open('wb') as raw:
 c.socket.settimeout(.05);read=c.read
 def recorded():
  d=read();raw.write(d);return d
 c.read=recorded;r=OutputReceiver(c,lambda samples:None);before=wait_configuration(r);gen=r.generator();report['before']={'configuration':asdict(before),'generator':asdict(gen.active),'running':gen.running}
 try:
  for cycle in range(10):
   for bits,rate in ((14,125000),(16,50000),(16,62500),(14,125000)):
    config=Configuration(bits,rate);r.configure(config);wait_configuration(r,config);t=time.monotonic()
    while time.monotonic()-t<.2:r.pump()
    r.generator();report['profiles'].append({'cycle':cycle,'config':asdict(r.decoder.config),'status':dict(r.decoder.status)})
  report['passed']=True
 except Exception as e:report['errors'].append(str(e))
 finally:
  r.configure(before);wait_configuration(r,before);g=r.generator();report['after']={'configuration':asdict(r.decoder.config),'generator':asdict(g.active),'running':g.running};report['restored']=report['before']==report['after'];report['passed']=report['passed'] and report['restored'];r.close()
(folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n');print(folder);print('passed',report['passed'],'stages',len(report['profiles']));assert report['passed']
