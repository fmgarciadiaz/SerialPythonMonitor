"""Private installed-profile screen; exact restore, no programming or deployment."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from experimentos.fs_max_v18.run_probe import private_profiles,FrameMetrics
from monitor.v18.io.live_connection import installed_connection,installed_identity
from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
from monitor.v18.receiver.unoq_acquisition import Configuration


def run(seconds=15,bits_filter=None,channels_filter=None,repeats=1,qualify=False):
 folder=Path(__file__).parent/time.strftime('%Y%m%d_%H%M%S');folder.mkdir()
 report={'ok':False,'seconds_per_case':seconds,'repeats':repeats,'deployment':False,'qualification':qualify,'cases':[]}
 def save(): (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 save();print(folder,flush=True)
 with private_profiles():
  with installed_connection('1060031107') as connection:
   receiver=OutputReceiver(connection,lambda records:None);receiver.decoder.numeric=True
   lifecycle=ReceiverLifecycle(receiver,connection.identity,folder);captured=False
   try:
    snapshot=lifecycle.capture();captured=True
    if snapshot.generator.enabled:raise RuntimeError('Generador activo: campaña no iniciada')
    cases=[(10,122,5568),(12,146,7488),(14,176,5952),(16,1100,3488),(16,None,None)]
    cases=[case for case in cases if bits_filter is None or case[0] in bits_filter]
    cases=[case for case in cases if channels_filter is None or (1 if case[1] else 2) in channels_filter]
    sequence=([(rep,duration,*case) for case in cases for rep,duration in enumerate((60,120,120,120),1)] if qualify else [(rep,seconds,*case) for rep in range(1,repeats+1) for case in cases])
    for repetition,duration,bits,ticks,pairs in sequence:
     receiver.configure(Configuration(14,40000))
     config=Configuration.from_wire(bits,(pairs<<16)|ticks) if ticks else Configuration(16,76226)
     row={'seconds':duration,'repetition':repetition,'bits':bits,'channels':config.channels,'rate':config.actual_rate,'ticks':config.period,'node_pairs':config.node_pairs,'ok':False}
     report['cases'].append(row);save();print('BEGIN',row,flush=True)
     receiver.configure(config)
     deadline=time.monotonic()+1
     while time.monotonic()<deadline:receiver.pump()
     before=receiver.decoder.pairs;start=time.monotonic();metrics=FrameMetrics()
     while time.monotonic()-start<duration:
      receiver.pump();metrics.observe(receiver.decoder.statuses)
     elapsed=time.monotonic()-start;samples=receiver.decoder.pairs-before
     budget=config.node_pairs*config.period
     # Legacy dual profiles have a 1 MHz timestamp; metric budgets use 160 MHz ticks.
     if not config._native:budget*=160
     margin=metrics.margin(budget)
     row.update(elapsed=elapsed,samples=samples,observed_rate=samples/elapsed,status=receiver.decoder.status,queue_peak=metrics.queue_peak,min_slack_ticks=metrics.min_slack,mean_send_margin=margin)
     if abs(samples/elapsed/config.actual_rate-1)>.02:raise RuntimeError('Tasa observada incorrecta')
     if not metrics.frames:raise RuntimeError('Sin métricas de integridad')
     row['ok']=True
     row['headroom_ok']=margin is not None and margin>=.1 and metrics.queue_peak<4 and metrics.min_slack>0
     save();print('END',row,flush=True)
    report['measurement_ok']=True
   except BaseException as exc:
    report['error']=repr(exc);print('ERROR',repr(exc),flush=True)
   finally:
    if captured:report['restoration']=lifecycle.restore(10)
    receiver.close();save()
   after=installed_identity('1060031107')
   report['identity_unchanged']=after==connection.identity
  report['ok']=bool(report.get('measurement_ok') and report.get('restoration',{}).get('hardware_restored') and report.get('identity_unchanged'))
  save();print('FINAL',report['ok'],folder,flush=True)
 return 0 if report['ok'] else 1
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--qualify',action='store_true');parser.add_argument('--seconds',type=float,default=15)
 parser.add_argument('--bits',nargs='+',type=int);parser.add_argument('--channels',nargs='+',type=int)
 parser.add_argument('--repeats',type=int,choices=(1,2,3),default=1)
 args=parser.parse_args()
 if not 0<args.seconds<=120:parser.error('seconds must be in (0,120]')
 raise SystemExit(run(args.seconds,args.bits,args.channels,args.repeats,args.qualify))
