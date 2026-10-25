"""Private GUI/RADIO/FILTER/A0 matrix; exact candidate binary and production rollback."""
import argparse,hashlib,json,os,subprocess,sys,time,traceback,zipfile
from pathlib import Path
from contextlib import ExitStack,nullcontext
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.fs_max_all_bits_v17.run import FILES

def child(args):
 if int(os.environ.get('SPM_FS_JOINT_OWNER_PID','0'))!=os.getppid():
  raise RuntimeError('Child requires its live campaign owner parent')
 from monitor.v17.receiver import unoq_native
 profiles=json.loads((EXP/'candidate_profiles.json').read_text())
 for p in profiles:p['optimized_transport']=p['bits']!=16
 unoq_native.PROFILES=unoq_native.PROFILES+tuple(profiles)
 target=next(p for p in profiles if p['bits']==args.bits and not p.get('purpose'))
 rate=160000000//target['ticks']
 import monitor.v17.app as gui
 import monitor.v17.radio_output as output
 import monitor.v17.radio_output_panel as panel
 from diagnosticos.validar_generador_radio_v17 import main as audio_trial
 supported=gui._configuration_supported;guard=panel.acquisition_error
 def private_supported(bits,r):return (bits,r)==(args.bits,rate) or supported(bits,r)
 def private_guard(config):return None if (config.bits,config.rate)==(args.bits,rate) else guard(config)
 sys.argv=['private_joint','--bits',str(args.bits),'--rate',str(rate),'--seconds',str(args.seconds),'--audio-rate','40000','--analysis-audit','--refill-ring','--defer-diagnostics']
 if args.input=='FILTER':sys.argv+=['--filter-input']
 try:
  with ExitStack() as stack:
   stack.enter_context(patch.object(gui,'_configuration_supported',side_effect=private_supported))
   stack.enter_context(patch.object(panel,'acquisition_error',side_effect=private_guard))
   # Extend the existing qualified ADC14 source policy to its private next-rate candidate.
   if args.bits==14:stack.enter_context(patch.object(panel,'RadioDacSource',output.HighRateRadioDacSource))
   report,folder=audio_trial(owner_context=nullcontext())
  args.result.write_text(json.dumps(dict(report=str(folder/'report.json'),ok=report['ok'],restored=report['restored']),indent=2)+'\n')
 except BaseException as exc:
  args.result.write_text(json.dumps(dict(ok=False,restored=False,error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n')
  raise

def campaign(args):
 from tools.unoq import Board,config_path
 from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
 from monitor.v17.board_owner import board_owner
 from monitor.v17.bode_calibration import instrument_identity
 import usb_stream
 summary=json.loads((EXP/'qualification_summary.json').read_text())
 accepted=[b for b in (8,10,14,16) if summary['bits'][str(b)]['integrity_ok']]
 if accepted!=[8,10,14,16]:raise ValueError('Missing sustained integrity qualification')
 reference=json.loads((ROOT/summary['reports'][0]).read_text())
 sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
 hashes={'sketch/'+n:hashlib.sha256((EXP/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in FILES}
 hashes.update({'relay/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
 if hashes!=reference['source_hashes']:raise ValueError('Candidate sources changed after ADC qualification')
 if hashlib.sha256((EXP/'candidate_profiles.json').read_bytes()).hexdigest()!=reference['candidate_profiles_sha256']:raise ValueError('Private host profiles changed')
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None;x.sources=sources
 x.folder=EXP/('joint_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report=dict(ok=False,restored=False,cases=[],scope=__doc__,source_hashes=hashes,adc_evidence=summary['reports'],seconds=args.seconds,
  host_hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('diagnosticos/validar_generador_radio_v17.py','monitor/v17/app.py','monitor/v17/radio_output.py','monitor/v17/radio_output_panel.py')})
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes());x.save();changed=False
 with zipfile.ZipFile(x.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for key in hashes:z.write(EXP/('oscilloscope/'+key if key.startswith('sketch/') else key),key)
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 with board_owner(x.board.serial,'FS privada: GUI RADIO FILTER A0'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'])
   x.normal=x.policy();x.report['normal_policy']=x.normal
   prior=x.folder/'prior_headers';prior.mkdir();presence={};x.report['prior_header_presence']=presence
   for n in FILES:
    try:x.board.shell('test','-f',x.board.remote+'/sketch/'+n)
    except subprocess.CalledProcessError:presence[n]=False
    else:presence[n]=True;x.board.run('pull',x.board.remote+'/sketch/'+n,str(prior/n))
   x.save();usb_stream.stop(x.board);x.board.stop();changed=True;x.build()
   for n in FILES:x.board.run('push',str(EXP/'oscilloscope/sketch'/n),x.board.remote+'/sketch/'+n)
   x.board.start();x.start_relay(x.relay)
   x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
   if x.report['candidate_identity']!=summary['candidate_identity']:raise ValueError('Candidate firmware changed after ADC qualification')
   for bits in accepted:
    for input_name in ('RADIO','FILTER'):
     stage=f'adc{bits}_{input_name.lower()}';result=x.folder/(stage+'.json')
     print('BEGIN',stage,args.seconds,flush=True)
     env=dict(os.environ,QT_QPA_PLATFORM='cocoa',SPM_FS_JOINT_OWNER_PID=str(os.getpid()))
     command=[sys.executable,str(Path(__file__).resolve()),'--child','--bits',str(bits),'--input',input_name,'--seconds',str(args.seconds),'--result',str(result.resolve())]
     with (x.folder/(stage+'.log')).open('w') as log:
      process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env)
      while process.poll() is None:time.sleep(.5)
     leaf=json.loads(result.read_text()) if result.exists() else dict(ok=False,restored=False,error='Child exited without result')
     row=dict(stage=stage,bits=bits,input=input_name,child_exit=process.returncode,child=leaf,ok=False)
     if leaf.get('report'):
      report=json.loads(Path(leaf['report']).read_text());stats=report.get('joint_send_statistics',{});paint=report.get('paint_audit',{})
      row.update(audio_ok=report['ok'],restored=report['restored'],errors=report['errors'],queue_peak=report.get('adc_queue_peak'),send_statistics=stats,paint=paint,
       source_buffer_minimum=report.get('source_buffer_minimum'),delivery_failure=report.get('delivery_failure'),audio_source_type=report.get('audio_source_type'))
      row['ok']=report['ok'] and report['restored'] and process.returncode==0 and paint.get('exposed_fraction',0)>=.9 and paint.get('scope_fps',0)>=5 and paint.get('fft_fps',0)>=5
      row['headroom_ok']=row['ok'] and stats.get('mean_margin',0)>=.1 and row.get('queue_peak',99)<4 and stats.get('minimum_slack_ticks',0)>0
     x.report['cases'].append(row);x.save();print('END',stage,'ok',row['ok'],'headroom',row.get('headroom_ok'),flush=True)
     if not leaf.get('restored'):raise RuntimeError('Child did not verify low-rate restoration; abort before another connection')
     # No silent retries: preserve failures; continue other independent cases only after verified low-rate restore.
     x.normal_check(stage+'_normal')
   x.report['ok']=all(r.get('ok') for r in x.report['cases'] if 'child' in r)
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   if changed:
    usb_stream.stop(x.board);x.board.stop()
    for n in FILES:
     if presence[n]:x.board.run('push',str(prior/n),x.board.remote+'/sketch/'+n)
     else:x.board.shell('python3','-c','from pathlib import Path;import sys;Path(sys.argv[1]).unlink(missing_ok=True)',x.board.remote+'/sketch/'+n)
    x.board.start();x.start_relay(x.report['old_relay'],prior=True)
   if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--child',action='store_true');p.add_argument('--bits',type=int,choices=(8,10,14,16));p.add_argument('--input',choices=('RADIO','FILTER'));p.add_argument('--result',type=Path);p.add_argument('--seconds',type=int,default=60)
 args=p.parse_args()
 if not 20<=args.seconds<=120:p.error('Use20–120seconds')
 if args.child:
  if args.bits is None or args.input is None or args.result is None:p.error('Incomplete child arguments')
  child(args)
 else:campaign(args)
if __name__=='__main__':main()
