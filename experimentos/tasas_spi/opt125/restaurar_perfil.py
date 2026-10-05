import sys,time,json
from pathlib import Path
from dataclasses import asdict
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from experimentos.tasas_spi.receiver.unoq_usb import Connection
from experimentos.tasas_spi.receiver.unoq_config_receiver import OutputReceiver
from experimentos.tasas_spi.receiver.unoq_acquisition import Configuration
from experimentos.tasas_spi.receiver.unoq_generator import GeneratorConfig
HERE=Path(__file__).resolve().parent
previous=json.loads((HERE/'resultados/perfil_anterior.json').read_text())
with Connection('1060031107') as c:
 c.socket.settimeout(.1)
 count=[0]
 r=OutputReceiver(c,lambda samples:None)
 r.configure(Configuration(**previous['acquisition']))
 r.generator(GeneratorConfig(**previous['generator']))
 r.on_samples=lambda samples:count.__setitem__(0,count[0]+len(samples))
 until=time.monotonic()+3
 while time.monotonic()<until:
  try:r.pump()
  except TimeoutError:pass
 g=r.generator().active
 report={'configuration':asdict(r.config),'generator':asdict(g),'pairs':count[0],'status':r.decoder.status}
 report['passed']=count[0]>previous['acquisition']['rate']*2.5 and report['configuration']==previous['acquisition'] and report['generator']==previous['generator'] and not report['status']['dropped'] and not report['status']['fatal']
 (HERE/'resultados/restauracion_final.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report));r.close()
