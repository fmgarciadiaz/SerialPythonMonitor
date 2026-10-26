"""Private host profile against installed Scope V18; no programming, exact restore."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def run(args):
 from monitor.v18.io.live_connection import installed_connection,installed_identity
 from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
 from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
 from tools.gui_experimental_v18 import selected_profile
 profile=selected_profile('installed',f'{args.bits}:{args.ticks}')
 folder=ROOT/'diagnosticos/resultados_v18'/time.strftime('gui_installed_private_%Y%m%d_%H%M%S');folder.mkdir()
 report=dict(ok=False,deployment=False,profile=profile);snapshot=None;identity=None;child=None;display_guard=None
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 save();print(folder,flush=True)
 try:
  with installed_connection(args.serial) as connection:
   receiver=OutputReceiver(connection,lambda records:None);receiver.decoder.numeric=True
   life=ReceiverLifecycle(receiver,connection.identity,folder/'baseline')
   snapshot=life.capture();identity=connection.identity
   report['baseline']=snapshot.to_dict();report['identity']=identity
   receiver.close()
  env=dict(os.environ,SCOPE_V18_GUI_RECIPE='installed',SCOPE_V18_GUI_TARGET=f'{args.bits}:{args.ticks}')
  command=[sys.executable,str(ROOT/'tools/gui_experimental_v18.py'),'--serial',args.serial,
   '--output',str(folder/'gui.json'),'--bits',str(args.bits),'--rate',str(160000000//args.ticks),
   '--frequency-khz',str(args.frequency_khz),'--duration',str(args.hold+30),'--hold-radio-seconds',str(args.hold),
   '--scan','--wav','--fm','--voices','20']
  if args.us:command+=['--us']
  if args.keep_display_awake:
   if sys.platform!='darwin':raise RuntimeError('Display guard requires macOS')
   display_guard=subprocess.Popen(['caffeinate','-du','-t','600'])
   report['display_guard']=dict(pid=display_guard.pid,timeout_seconds=600)
  report['command']=command;save()
  with (folder/'gui.log').open('w') as log:
   child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
   child.wait(timeout=args.hold+150)
  report['exit_code']=child.returncode
  if (folder/'gui.json').exists():
   evidence=json.loads((folder/'gui.json').read_text())
   periodic=[stage for stage in evidence['stages'] if stage['stage']=='periodic']
   report['exposed_fraction']=sum(bool(stage.get('exposed')) for stage in periodic)/max(1,len(periodic))
   report['paint_events']=evidence['paint_events']
   report['visible_gui_ok']=bool(periodic) and report['exposed_fraction']>=.9 and evidence['paint_events']>=args.hold*20
   report['gui_ok']=child.returncode==0 and not evidence['errors'] and all(evidence['assertions'].values()) and report['visible_gui_ok']
 except BaseException as exc:report['error']=repr(exc)
 finally:
  if child is not None and child.poll() is None:
   child.send_signal(signal.SIGINT)
   try:child.wait(timeout=90)
   except subprocess.TimeoutExpired:report['close_error']='GUI sigue siendo dueña del Q; sin toma forzada'
  if display_guard is not None:
   try:
    display_guard.terminate();display_guard.wait(timeout=5)
    report['display_guard']['released']=True
   except Exception as exc:report['display_guard']['release_error']=repr(exc)
  if snapshot is not None and (child is None or child.poll() is not None):
   try:
    try:installed_identity(args.serial)
    except RuntimeError:
     from monitor.v18.q_support.service import RECEIPT,prepare
     from monitor.v18.q_support.prepare import load_acceptance
     accepted=load_acceptance(RECEIPT)
     if any(identity[key]!=accepted['candidate_identity'][key] for key in ('firmware_sha256','relay_sha256')):
      raise RuntimeError('La pareja fallida no es la pareja aceptada; sin reinicio')
     report['accepted_recovery']=prepare(args.serial,folder/'accepted_recovery.json')
     if not report['accepted_recovery'].get('ok'):raise RuntimeError('Recuperación de pareja aceptada falló')
    with installed_connection(args.serial) as connection:
     if connection.identity!=identity:raise RuntimeError('Identidad de pareja cambió')
     receiver=OutputReceiver(connection,lambda records:None);receiver.decoder.numeric=True
     life=ReceiverLifecycle(receiver,identity,folder/'restore');life.snapshot=snapshot
     report['restoration']=life.restore(10)
     receiver.close()
    report['identity_unchanged']=installed_identity(args.serial)==identity
   except BaseException as exc:report['restore_error']=repr(exc)
  report['ok']=bool(report.get('gui_ok') and report.get('restoration',{}).get('hardware_restored') and report.get('identity_unchanged'))
  save();print('FINAL',report['ok'],folder,flush=True)
 return 0 if report['ok'] else 1

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',default='1060031107')
 parser.add_argument('--bits',type=int,choices=(10,12,14),required=True);parser.add_argument('--ticks',type=int,required=True)
 parser.add_argument('--hold',type=float,default=120);parser.add_argument('--frequency-khz',type=float,default=400)
 parser.add_argument('--us',action='store_true');parser.add_argument('--keep-display-awake',action='store_true');args=parser.parse_args()
 if not 0<args.hold<=120:parser.error('hold must be in (0,120]')
 def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
 signal.signal(signal.SIGTERM,interrupted)
 raise SystemExit(run(args))
