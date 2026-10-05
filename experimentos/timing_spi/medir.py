#!/usr/bin/env python3
"""Capture original diagnostic stream and node timing snapshots; no GUI."""
import sys,time,json,argparse
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from experimentos.timing_spi.receiver.unoq_usb import Connection
from experimentos.timing_spi.receiver.unoq_config_receiver import OutputReceiver
from experimentos.timing_spi.receiver.unoq_acquisition import Configuration
from experimentos.timing_spi.receiver.unoq_generator import GeneratorConfig
from experimentos.timing_spi.receiver.unoq_switch import Mode

def main():
 p=argparse.ArgumentParser();p.add_argument('--rates',type=int,nargs='+',default=[100000,125000]);p.add_argument('--seconds',type=float,default=30);a=p.parse_args()
 folder=ROOT/'experimentos/timing_spi/resultados'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');folder.mkdir(parents=True)
 report={'profiles':[],'errors':[]};before=None;generator=None
 try:
  with (folder/'stream.scp').open('wb') as raw,Connection('1060031107') as c:
   c.socket.settimeout(.02);read=c.read
   def recording_read():
    data=read();raw.write(data);return data
   c.read=recording_read;r=OutputReceiver(c,lambda samples:None)
   try:
    generator=r.generator().active;before=r.config;r.select(Mode.SPI)
    report['before']={'configuration':asdict(before),'generator':asdict(generator)}
    r.generator(GeneratorConfig(1,1,0,2000000,2000000,500,3500,1000))
    for rate in a.rates:
     row={'rate':rate,'bits':14,'passed':False};report['profiles'].append(row);snapshots=[];count=0;started=time.monotonic()
     try:
      r.on_samples=lambda samples:None;r.configure(Configuration(14,rate));started=time.monotonic()
      def collect(samples):
       nonlocal count
       count+=len(samples)
      r.on_samples=collect
      with (folder/f'timing_{rate}.jsonl').open('w') as log:
       while time.monotonic()-started<a.seconds:
        r.pump()
        for snap in r.decoder.telemetry:
         if snap['rate']==rate:
          snap['pc_elapsed_s']=time.monotonic()-started;snapshots.append(snap);log.write(json.dumps(snap)+'\n')
      row['passed']=count>rate*(a.seconds-.5)
     except Exception as exc:row['error']=str(exc);report['errors'].append(str(exc))
     row.update(pairs=count,elapsed_s=time.monotonic()-started,snapshots=len(snapshots),status=r.decoder.status)
     if snapshots:
      latest=snapshots[-1];row['last_snapshot']=latest
      row['averages_us']={name:m['total_us']/m['count'] for name,m in latest['metrics'].items() if m['count']}
      row['queue_history']=[{'pc_elapsed_s':s['pc_elapsed_s'],'used':s['queue_used'],'peak':s['queue_peak']} for s in snapshots]
     print(json.dumps({k:v for k,v in row.items() if k!='queue_history'}),flush=True)
     if not row['passed']:break
   finally:
    r.on_samples=lambda samples:None
    try:
     if before is not None:r.configure(before)
     if generator is not None:r.generator(generator)
    except Exception as exc:report['errors'].append('Restore: '+str(exc))
    r.close()
 except Exception as exc:report['errors'].append(str(exc))
 (folder/'informe.json').write_text(json.dumps(report,indent=2)+'\n');print(folder,flush=True)
 return 0 if not report['errors'] else 1
if __name__=='__main__':raise SystemExit(main())
