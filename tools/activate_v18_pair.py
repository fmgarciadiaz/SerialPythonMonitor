"""Activate an independent Scope V18 + relay, preserving the frozen V17 app.
Explicit --run required; never overwrites an existing V18 deployment.
"""
import argparse,json,shlex,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board
from monitor.v18.board_owner import board_owner
from monitor.relay_identity import relay_digest


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');a=parser.parse_args()
 config=json.loads((ROOT/'arduino/v18/unoq.json').read_text())
 if not a.run:print(json.dumps(config,indent=2));return 0
 folder=ROOT/'diagnosticos/resultados_v18'/time.strftime('activation_%Y%m%d_%H%M%S');folder.mkdir(parents=True)
 report={'ok':False,'v17_sources_modified':False};b=Board(config);created=False;original_stopped=False
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 with board_owner(b.serial,'Activar pareja V18 independiente'):
  try:
   apps=json.loads(b.cli('app','list','--format','json',capture=True).stdout)['apps']
   if any(x.get('name')=='Scope V18' for x in apps):raise RuntimeError('Scope V18 already exists; refuse overwrite')
   frozen=sorted((ROOT/'respaldos/parejas').glob('v17_*/manifest.json'))
   if not frozen:raise RuntimeError('Missing frozen V17 pair')
   report['v17_frozen_manifest']=str(frozen[-1].relative_to(ROOT));save()
   report['original_relay']=json.loads(b.shell('docker','inspect','serialmonitor-usb-stream',capture=True).stdout)[0]
   report['original_app']=json.loads(b.shell('docker','inspect','scope-v17-main-1',capture=True).stdout)[0];save()
   if report['original_relay']['State']['Running']:raise RuntimeError('V17 relay running; close acquisition before activation')
   # Keep V17 source/app installed; only stop its running instance.
   b.cli('app','stop','/home/arduino/ArduinoApps/scope-v17');original_stopped=True
   b.create();created=True;report['created']=True;save()
   # App CLI compiles/uploads this independent application's sketch.
   b.start()
   digest=relay_digest(ROOT/'arduino/v18/relay')
   binary='/home/arduino/.cache/serialmonitor/usb-stream-'+digest+'/unoq_stream'
   b.shell('test','-x',binary)
   from spi_benchmark import IMAGE
   b.shell('docker','run','-d','--name',config['container'],'--network','host','--read-only',
    '--cap-drop','ALL','--cap-add','SYS_NICE','--security-opt','no-new-privileges','--user','0:0',
    '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
    '--mount',f'type=bind,src={binary},dst=/work/unoq_stream,readonly',
    '--mount','type=bind,src=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor,dst=/scope_cpu_governor',
    '--entrypoint','/work/unoq_stream',IMAGE)
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    logs=b.run('shell','docker logs '+shlex.quote(config['container'])+' 2>&1',capture=True).stdout
    if 'SPI ready: first verified frame' in logs:break
    time.sleep(.2)
   else:raise TimeoutError('V18 relay has no verified first frame')
   report.update(ok=True,relay_binary=binary);save()
  except BaseException as exc:
   report['error']=repr(exc);report['rollback_errors']=[]
   if created:
    for label,fn in [('stop_v18_relay',lambda:b.shell('docker','stop','--time','3',config['container'])),('stop_v18_app',b.stop)]:
     try:fn()
     except Exception as failure:report['rollback_errors'].append(label+': '+repr(failure))
   if original_stopped:
    old=Board(json.loads((ROOT/'arduino/v17/unoq.json').read_text()))
    try:old.start()
    except Exception as failure:report['rollback_errors'].append('restart_v17: '+repr(failure))
   save();raise
 print(folder/'report.json');return 0
if __name__=='__main__':raise SystemExit(main())
