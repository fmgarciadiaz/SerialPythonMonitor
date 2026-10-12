"""Autonomous bounded grid, integer-tick refinement and independent long runs.

All reports are persisted after every case; finally restores the real snapshot.
No experimental profile is added to the production monitor.
"""
import sys,json,time,subprocess,traceback,struct,hashlib
from pathlib import Path
from dataclasses import asdict,replace
import numpy as np
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.maxfreq_dual_v16.prepare import boards
from experimentos.maxfreq_dual_v16.contract import Session
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from monitor.v16.receiver.unoq_switch import Mode
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
import usb_stream
TICKS=[1600,1200,960,800,640,560,480,400,360,320,288,267,256,242,224,208,192,176,160,156]
TICKS16=[4000,3200,2800,2560,2400,2304,2240,2200,2160,2144,2134,2112,2100,2098,2088,2080,2064,2048]
NODES={8:[1728,3456,3888],10:[1392,2784,4176],12:[1152,2304,4032],14:[992,1984,3968],16:[864,1728,3456]}
class Sweep:
 def __init__(self):
  self.stable,self.candidate=boards();self.deployment=json.loads((EXP/'deployment.json').read_text())
  self.prior=json.loads((EXP/'prior.json').read_text());self.dirty=False;self.switched=False
  self.report={'channels':2,'ok':False,'restored':False,'plan':{'ticks':TICKS,'nodes':NODES,'screen_seconds':5,'settle_seconds':1,'refine_seconds':10,'long_seconds':[120,120,120,600]},'prior':self.prior,'cases':[],'winners':{},'analog':'Not measured'}
  if '--resume' in sys.argv:
   previous=json.loads((EXP/'sweep.json').read_text())
   self.report['cases']=previous['cases'];self.report['winners']=previous.get('winners',{})
  self.report['skipped_after_repeated_failure']=[]
  self.report['revision']='dual_specialized_packing_v2'
  self.report['source_hashes']={str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [EXP/'sweep.py',EXP/'contract.py',*sorted((EXP/'arduino').rglob('*.h')),*sorted((EXP/'arduino').rglob('*.ino')),*sorted((EXP/'arduino').rglob('*.c'))]}
  if '--resume' in sys.argv and previous.get('source_hashes')!=self.report['source_hashes']:raise RuntimeError('No se puede mezclar evidencia de distintas fuentes')
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
   row['ok']=False;row['error']=str(e);row['status']=d.status if d else None;self.dirty=True
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
  if any(term in row.get('error','') for term in ('Padding/cantidad','Metadatos','CRC/cabecera','APPLIED inválido')):
   raise RuntimeError('Contrato incompatible; abortar sin inferir límite ADC: '+row['error'])
  return row
 def screen(self):
  def probe(bits,ticks,n,stage,seconds=10,restart=False):
   rows=[r for r in self.report['cases'] if r['bits']==bits and r['ticks']==ticks and r['node_pairs']==n and r['stage']==stage]
   return rows[-1] if rows else self.trial(bits,ticks,n,max(seconds,130*n*ticks/160000000),stage,restart=restart)
  for bits,nodes in NODES.items():
   grid=TICKS16 if bits==16 else TICKS
   for n in nodes:
    for index,ticks in enumerate(grid):
     row=probe(bits,ticks,n,'screen',5)
     if not row['ok'] and not probe(bits,ticks,n,'repeat_failure',restart=True)['ok']:
      self.report['skipped_after_repeated_failure'].append({'bits':bits,'node_pairs':n,'failed_ticks':ticks,'faster_ticks':grid[index+1:]})
      self.save();break
  # Bracket integer-tick thresholds; probe neighboring points to check short-run jitter.
  self.report['plan']['refinement']='Binary brackets plus neighboring integer ticks; margins refined separately'
  for bits,nodes in NODES.items():
   for n in nodes:
    cases=[r for r in self.report['cases'] if r['bits']==bits and r['node_pairs']==n]
    passed=[r['ticks'] for r in cases if r['ok']]
    if not passed:continue
    slow=min(passed);failed=[r['ticks'] for r in cases if not r['ok'] and r['ticks']<slow]
    if failed:
     fast=max(failed)
     while slow-fast>1:
      ticks=(slow+fast)//2
      row=probe(bits,ticks,n,'refine')
      if row['ok']:slow=ticks
      else:fast=ticks
     for ticks in range(max(2048 if bits==16 else 156,slow-2),slow+3):
      if not any(r['bits']==bits and r['node_pairs']==n and r['ticks']==ticks for r in self.report['cases']):
       probe(bits,ticks,n,'neighbor')
    cases=[r for r in self.report['cases'] if r['bits']==bits and r['node_pairs']==n]
    margin=[r['ticks'] for r in cases if r['ok'] and r.get('headroom_ok')]
    if not margin:continue
    slow=min(margin)
    failed=[r['ticks'] for r in cases if r['ticks']<slow and (not r['ok'] or not r.get('headroom_ok'))]
    if failed:
     fast=max(failed)
     while slow-fast>1:
      ticks=(slow+fast)//2
      row=probe(bits,ticks,n,'margin_refine')
      if row['ok'] and row.get('headroom_ok'):slow=ticks
      else:fast=ticks
     for ticks in range(slow,slow+4):
      if not any(r['bits']==bits and r['node_pairs']==n and r['ticks']==ticks for r in self.report['cases']):
       probe(bits,ticks,n,'margin_neighbor')
  self.save()
 def finalists(self):
  for bits in NODES:
   passed=[r for r in self.report['cases'] if r['bits']==bits and r['ok']]
   profiles=sorted({(r['ticks'],r['node_pairs']) for r in passed},key=lambda p:(p[0],-p[1]))
   accepted={};rejected=set()
   def validate(ticks,n,margin=False):
    profile=(ticks,n)
    if profile in accepted:return accepted[profile]
    if profile in rejected:return None
    rows=[]
    for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120),('endurance',600)]:
     row=self.trial(bits,ticks,n,seconds,stage,restart=True);rows.append(row)
     if not row['ok']:rejected.add(profile);return None
     if margin and not row.get('headroom_ok'):return None
    result={'channels':2,'bits':bits,'ticks':ticks,'node_pairs':n,'actual_rate':160000000/ticks,
      'integrity_accepted':True,'headroom_accepted':all(r.get('headroom_ok',False) for r in rows)}
    accepted[profile]=result;return result
   winner=None
   for ticks,n in profiles:
    winner=validate(ticks,n)
    if winner is not None:break
   self.report['winners'][str(bits)]={'maximum_integrity':winner,'maximum_headroom':None}
   self.save()
   # Search independently for the fastest sustained profile with measured margin.
   margin_profiles=[p for p in profiles if any(r['ticks']==p[0] and r['node_pairs']==p[1] and r.get('headroom_ok',False) for r in passed)]
   if winner and winner['headroom_accepted']:margin_profiles.insert(0,(winner['ticks'],winner['node_pairs']))
   for ticks,n in margin_profiles:
    result=validate(ticks,n,margin=True)
    if result and result['headroom_accepted']:
     self.report['winners'][str(bits)]['maximum_headroom']=result;break
   self.save()
   if winner is None:self.report.setdefault('unaccepted_bits',[]).append(bits)
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
   self.screen();self.finalists();self.report['ok']=not self.report.get('unaccepted_bits')
  except BaseException as e:self.report['error']=str(e);traceback.print_exc()
  finally:
   if self.switched:
    try:self.restore()
    except Exception as e:self.report['restore_error']=str(e);traceback.print_exc()
   self.save()
  print(json.dumps({k:v for k,v in self.report.items() if k!='cases'},indent=2),flush=True)
if __name__=='__main__':Sweep().run()
