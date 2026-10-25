"""Autonomous bounded grid, integer-tick refinement and independent long runs.

All reports are persisted after every case; finally restores the real snapshot.
No experimental profile is added to the production monitor.
"""
import sys,json,time,subprocess,traceback,struct
from pathlib import Path
from dataclasses import asdict,replace
import numpy as np
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.maxfreq_v16.prepare import boards
from experimentos.maxfreq_v16.contract import Session
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_switch import Mode
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
import usb_stream
TICKS=[480,400,320,267,242,224,208,200,192,176,160,144,133,128,120,112,104,96,88,80,78]
NODES={8:[3456,3584,6912,8192],10:[2784,5568,8192],14:[1984,3968,7936]}
class Sweep:
 def __init__(self):
  self.stable,self.candidate=boards();self.deployment=json.loads((EXP/'deployment.json').read_text())
  self.prior=json.loads((EXP/'prior.json').read_text());self.dirty=False;self.switched=False
  self.report={'ok':False,'restored':False,'plan':{'ticks':TICKS,'nodes':NODES,'screen_seconds':5,'settle_seconds':1,'refine_seconds':10,'long_seconds':[120,120,120,600]},'prior':self.prior,'cases':[],'winners':{},'analog':'Not measured'}
  if '--resume' in sys.argv:
   previous=json.loads((EXP/'sweep.json').read_text())
   self.report['cases']=previous['cases'];self.report['winners']=previous.get('winners',{})
  self.report['skipped_after_repeated_failure']=[]
 def save(self):(EXP/'sweep.json').write_text(json.dumps(self.report,indent=2)+'\n')
 def logs(self,name):
  try:
   out=self.stable.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout
   (EXP/name).write_text(out)
   return out
  except Exception as e:print('Log capture:',e,flush=True)
 def fast_reset(self):
  usb_stream.stop(self.candidate)
  # Use the validated App CLI boot/flash sequence. GPIO-only reset enters the
  # loader on this board and does not establish a fresh acquisition.
  self.candidate.start()
  start_relay(self.candidate,self.deployment['candidate_relay']);self.dirty=False
 def trial(self,bits,ticks,n,seconds,stage,restart=False):
  if self.dirty or restart:self.fast_reset()
  row={'bits':bits,'ticks':ticks,'node_pairs':n,'actual_rate':160000000/ticks,'requested_seconds':seconds,'stage':stage,'ok':False}
  print(f'BEGIN {stage} ADC{bits} ticks={ticks} N={n} {seconds}s',flush=True)
  d=None;start=None;before=None
  try:
   with Connection(self.stable.serial) as c:
    session=Session(c);d=session.decoder;row['phase']='generator'
    session.generator(GeneratorConfig(enabled=0));row['phase']='configure';session.configure(bits,ticks,n)
    row['phase']='settle'
    end=time.monotonic()+1
    while time.monotonic()<end:session.pump()
    d.reset_metrics();before=d.pairs;before_nodes=d.nodes;start=time.monotonic();next_log=start+30;row['phase']='measure'
    while time.monotonic()-start<seconds:
     session.pump()
     if time.monotonic()>=next_log:
      print(f'PROGRESS ADC{bits} ticks={ticks} N={n} {time.monotonic()-start:.0f}s samples={d.pairs-before}',flush=True);next_log+=30
    elapsed=time.monotonic()-start;count=d.pairs-before
    budget=n*ticks
    send=np.asarray(d.send_ticks,dtype=float)
    metrics={'node_budget_us':budget/160,'queue_histogram_frames':dict(d.queue_hist),'queue_peak':d.maxima['queue_peak'],
      'copy_max_us':d.maxima['copy_ticks']/160,'poll_max_us':d.maxima['poll_ticks']/160,'overwrite_slack_min_us':d.maxima['slack_min_ticks']/160,
      'send_observations':len(send),'send_mean_us':float(np.mean(send))/160 if len(send) else None,
      'send_p50_p95_p99_max_us':(np.percentile(send,[50,95,99,100])/160).tolist() if len(send) else [],
      'mean_send_headroom':1-float(np.mean(send))/budget if len(send) else None,
      'producer_conservative_slack_us':d.maxima['slack_min_ticks']/160}
    row.update(seconds=elapsed,samples=count,full_nodes=d.nodes-before_nodes,observed_rate=count/elapsed,status=d.status,metrics=metrics)
    if abs(count/elapsed/(160000000/ticks)-1)>.02:raise ValueError('Tasa recibida incorrecta')
    if d.nodes-before_nodes<128:raise ValueError('Muestra insuficiente de nodos')
    row['ok']=True
    row['headroom_ok']=metrics['mean_send_headroom']>=.1 and metrics['queue_peak']<4 and metrics['producer_conservative_slack_us']>0
  except Exception as e:
   row['error']=str(e);row['status']=d.status if d else None;self.dirty=True
   if start is not None:row.update(seconds=time.monotonic()-start,samples=d.pairs-before)
   logs=self.logs(f"failure_{len(self.report['cases']):04d}.log")
   if logs and 'Rejected frame (hex): ' in logs:
    try:
     packet=bytes.fromhex(logs.split('Rejected frame (hex): ')[-1].splitlines()[0])
     row['rejected_adc_status']=dict(zip(('rate','index','dropped','fatal','count','bits','channels','ticks','node','flags'),struct.unpack_from('<IIIIHBBIII',packet,48)))
     if struct.unpack_from('<H',packet,6)[0]==20:
      row['rejected_metrics']=dict(zip(('node_pairs','queue','queue_peak','copy_ticks','poll_ticks','overwrite_slack_min_ticks','send_ticks','produced'),struct.unpack_from('<8I',packet,84)))
    except Exception as parse_error:row['log_parse_error']=str(parse_error)
  self.report['cases'].append(row);self.save()
  print(f"END {stage} ADC{bits} ticks={ticks} N={n} ok={row['ok']} headroom={row.get('headroom_ok')} error={row.get('error','')}",flush=True)
  return row
 def screen(self):
  for bits,nodes in NODES.items():
   for n in nodes:
    for index,ticks in enumerate(TICKS):
     existing=[r for r in self.report['cases'] if r['bits']==bits and r['node_pairs']==n and r['ticks']==ticks and r['stage']=='screen']
     row=existing[-1] if existing else self.trial(bits,ticks,n,5,'screen')
     if not row['ok']:
      repeated=[r for r in self.report['cases'] if r['bits']==bits and r['node_pairs']==n and r['ticks']==ticks and r['stage']=='repeat_failure']
      repeat=repeated[-1] if repeated else self.trial(bits,ticks,n,10,'repeat_failure',restart=True)
      if not repeat['ok']:
       self.report['skipped_after_repeated_failure'].append({'bits':bits,'node_pairs':n,'failed_ticks':ticks,'faster_ticks':TICKS[index+1:]});self.save();break
  # Refine every integer between fastest pass and nearest faster failure per node.
  for bits,nodes in NODES.items():
   for n in nodes:
    cases=[r for r in self.report['cases'] if r['bits']==bits and r['node_pairs']==n and r['stage']=='screen']
    passes=[r['ticks'] for r in cases if r['ok']]
    if not passes:continue
    slow=min(passes);fails=[r['ticks'] for r in cases if not r['ok'] and r['ticks']<slow]
    if not fails:continue
    fast=max(fails)
    for ticks in range(slow-1,fast,-1):
     if not any(r['bits']==bits and r['node_pairs']==n and r['ticks']==ticks and r['stage']=='refine' for r in self.report['cases']):self.trial(bits,ticks,n,10,'refine')
 def finalists(self):
  for bits in NODES:
   passed=[r for r in self.report['cases'] if r['bits']==bits and r['ok']]
   # Best observed rates across all nodes, prefer measured margin at equal rate.
   profiles=sorted({(r['ticks'],r['node_pairs']) for r in passed},key=lambda p:(p[0],-p[1]))
   winner=None
   for ticks,n in profiles:
    preliminary=self.trial(bits,ticks,n,60,'finalist',restart=True)
    if not preliminary['ok']:continue
    repetitions=[]
    for rep in range(3):
     row=self.trial(bits,ticks,n,120,f'acceptance_{rep+1}',restart=True);repetitions.append(row)
     if not row['ok']:break
    if len(repetitions)!=3 or not all(r['ok'] for r in repetitions):continue
    endurance=self.trial(bits,ticks,n,600,'endurance',restart=True)
    if not endurance['ok']:continue
    winner={'bits':bits,'ticks':ticks,'node_pairs':n,'actual_rate':160000000/ticks,
      'integrity_accepted':True,'headroom_accepted':all(r.get('headroom_ok',False) for r in [preliminary,*repetitions,endurance])}
    self.report['winners'][str(bits)]=winner;self.save();break
   if winner is None:raise RuntimeError(f'No sustained ADC{bits} finalist')
 def restore(self):
  self.logs('final_candidate_relay.log')
  usb_stream.stop(self.candidate);self.candidate.stop();self.stable.start();start_relay(self.stable,self.deployment['stable_relay'])
  with Connection(self.stable.serial) as c:
   r=OutputReceiver(c,lambda b:None,print);r.select(Mode.SPI)
   r.generator(GeneratorConfig(enabled=0));r.configure(Configuration(**self.prior['adc']))
   r.generator(GeneratorConfig(**self.prior['generator']))
   self.report['final_adc']=asdict(r.config);self.report['final_generator']=asdict(r.generator().active)
   self.report['restored']=self.report['final_adc']==self.prior['adc'] and self.report['final_generator']==self.prior['generator']
   before=r.decoder.pairs;start=time.monotonic()
   try:
    while time.monotonic()-start<10:r.pump()
    self.report['restore_samples']=r.decoder.pairs-before;self.report['restore_integrity_ok']=True
   except Exception as e:self.report['restore_integrity_ok']=False;self.report['restore_integrity_error']=str(e)
 def run(self):
  require_exclusive_monitor();self.save()
  try:
   self.switched=True;usb_stream.stop(self.stable);self.stable.stop();self.candidate.start();start_relay(self.candidate,self.deployment['candidate_relay'])
   self.screen();self.finalists();self.report['ok']=True
  except BaseException as e:self.report['error']=str(e);traceback.print_exc()
  finally:
   if self.switched:
    try:self.restore()
    except Exception as e:self.report['restore_error']=str(e);traceback.print_exc()
   self.save()
  print(json.dumps({k:v for k,v in self.report.items() if k!='cases'},indent=2),flush=True)
if __name__=='__main__':Sweep().run()
