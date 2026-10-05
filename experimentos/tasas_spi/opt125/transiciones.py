"""Exercise normal candidate control during acquisition, retaining validated samples."""
import argparse,importlib,json,sys,time
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[2]))
def main():
 p=argparse.ArgumentParser();p.add_argument('--variant',choices=('p512','p992'),required=True);args=p.parse_args()
 def m(name):return importlib.import_module('experimentos.tasas_spi.opt125.'+args.variant+'.receiver.'+name)
 C=m('unoq_acquisition').Configuration;G=m('unoq_generator').GeneratorConfig
 folder=HERE/'resultados'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');folder.mkdir()
 report={'variant':args.variant,'kind':'transitions','passed':False,'profiles':[],'errors':[]};count=0
 try:
  with m('unoq_usb').Connection('1060031107') as c,(folder/'stream.scp').open('wb') as raw:
   c.socket.settimeout(.05);read=c.read
   def recorded():
    data=read();raw.write(data);return data
   c.read=recorded
   r=m('unoq_config_receiver').OutputReceiver(c,lambda samples:None)
   try:
    for cycle in range(3):
     for rate,on in ((100000,0),(125000,0),(125000,1)):
      r.generator(G(0,on,0,2500,2500,0,4095,1000));r.configure(C(14,rate));count=0
      def consume(samples):
       nonlocal count
       count+=len(samples)
      r.on_samples=consume;start=time.monotonic()
      while time.monotonic()-start<2:r.pump()
      state=dict(r.decoder.status);report['profiles'].append({'cycle':cycle,'rate':rate,'generator':on,'pairs':count,'status':state})
      if count<rate*1.8 or state['dropped'] or state['fatal']:raise RuntimeError('Perfil sin continuidad')
    report['passed']=True
   finally:r.close()
 except Exception as exc:report['errors'].append(str(exc))
 (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));print(folder)
 return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
