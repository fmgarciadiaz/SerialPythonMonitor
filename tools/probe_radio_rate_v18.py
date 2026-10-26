"""Single installed RADIO/A0 rate check; exact restoration, no profile injection."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def run(args):
 from monitor.v18.io.live_connection import installed_connection,installed_identity
 from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
 from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
 profiles=json.loads((ROOT/'monitor/v18/receiver/native_profiles.json').read_text())
 selected=[p for p in profiles if not p.get('internal_only') and not p.get('integration_pending') and p['bits']==args.bits and p['ticks']==args.ticks]
 if len(selected)!=1:raise ValueError('Expected one public catalogue profile')
 profile=selected[0]
 folder=ROOT/'diagnosticos/resultados_v18'/time.strftime('radio_rate_check_%Y%m%d_%H%M%S');folder.mkdir()
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
  env=dict(os.environ)
  env.pop('SCOPE_V18_GUI_RECIPE',None);env.pop('SCOPE_V18_GUI_TARGET',None)
  command=[sys.executable,str(ROOT/'tools/gui_live_smoke_v18.py'),'--serial',args.serial,
   '--output',str(folder/'gui.json'),'--bits',str(args.bits),'--rate',str(160000000//args.ticks),
   '--frequency-khz',str(args.frequency_khz),'--duration',str(args.hold+5),'--hold-radio-seconds',str(args.hold),
   '--voices','20']
  if args.us:command+=['--us']
  fft_size=getattr(args,'fft_size',None)
  if fft_size:command+=['--fft-size',str(fft_size)]
  if getattr(args,'fft_only',False):command+=['--fft-only']
  if getattr(args,'fft_fixed_10',False):command+=['--fft-fixed-10']
  if getattr(args,'crop_radios',False):command+=['--scan','--crop-radios']
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
   minimum_hz=8 if fft_size else 20
   report['minimum_paint_hz']=minimum_hz
   report['visible_gui_ok']=bool(periodic) and report['exposed_fraction']>=.9 and evidence['paint_events']>=args.hold*minimum_hz
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
 parser.add_argument('--bits',type=int,choices=(8,10,12,14,16),required=True);parser.add_argument('--ticks',type=int,required=True)
 parser.add_argument('--hold',type=float,default=120);parser.add_argument('--frequency-khz',type=float,default=400)
 parser.add_argument('--fft-only',action='store_true')
 parser.add_argument('--fft-size',type=int,choices=(16384,32768,65536))
 parser.add_argument('--fft-fixed-10',action='store_true');parser.add_argument('--crop-radios',action='store_true')
 parser.add_argument('--us',action='store_true');parser.add_argument('--keep-display-awake',action='store_true');args=parser.parse_args()
 if not 0<args.hold<=120:parser.error('hold must be in (0,120]')
 def interrupted(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
 signal.signal(signal.SIGTERM,interrupted)
 raise SystemExit(run(args))
