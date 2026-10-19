"""Physical CPU-policy ABBA at accepted rates; no firmware/source deployment."""
import sys,json,time,statistics,traceback
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.unoq import Board,config_path
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_wav import State
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

class Campaign:
 def __init__(self):
  self.board=Board(json.loads(config_path('v17').read_text()))
  self.folder=Path(__file__).resolve().parent/('probe_'+time.strftime('%Y%m%d_%H%M%S'));self.folder.mkdir()
  self.report={'ok':False,'restored':False,'cases':[],'scope':'CPU policy screening only; accepted rates; ADC16 dual x16'}
  self.prior=None;self.normal=None;self.pid=None
 def save(self):
  (self.folder/'report.json').write_text(json.dumps(self.report,indent=2)+'\n')
 def remote(self,code,*args):return self.board.shell('python3','-c',code,*map(str,args),capture=True).stdout
 def policy(self,variant):
  cpus=[2] if variant=='B' else self.normal['cpus'];governor='performance' if variant=='B' else self.normal['governor']
  code="import os,json,sys;from pathlib import Path;p=int(sys.argv[1]);g=Path('/scope_cpu_governor');g.write_text(sys.argv[2]);os.sched_setaffinity(p,json.loads(sys.argv[3]));print(json.dumps({'governor':g.read_text().strip(),'cpus':sorted(os.sched_getaffinity(p))}))"
  actual=json.loads(self.board.shell('docker','exec','-u','0','serialmonitor-usb-stream','python3','-c',code,'1',governor,json.dumps(cpus),capture=True).stdout)
  assert actual=={'governor':governor,'cpus':cpus},actual
  return actual
 def pumping(self,receiver,fn):
  with ThreadPoolExecutor(max_workers=1) as pool:
   future=pool.submit(fn)
   while not future.done():receiver.pump()
   return future.result()
 def logs(self,name):
  (self.folder/name).write_text(self.board.run('shell','docker logs serialmonitor-usb-stream 2>&1',capture=True).stdout)
 def run(self):
  require_exclusive_monitor();self.save()
  if 'ESTAB' in self.board.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Q already has a reader')
  self.report['identity_before']=instrument_identity(self.board.serial)
  if self.report['identity_before'] is None:raise RuntimeError('Firmware identity unknown')
  try:
   with Connection(self.board.serial) as connection:
    r=OutputReceiver(connection,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI)
    gen=r.generator().active
    if gen.enabled:raise RuntimeError('Generator enabled; screening cancelled')
    r.wav_request()
    end=time.monotonic()+3
    while r.wav_pending and time.monotonic()<end:r.pump()
    if r.wav_pending or r.wav_status is None or r.wav_status.state!=State.IDLE:raise RuntimeError('WAV occupied')
    self.prior={'adc':asdict(r.config),'generator':asdict(gen)};self.report['prior']=self.prior;self.save()
    r.configure(Configuration(14,40000))
    self.pid=int(self.pumping(r,lambda:self.board.shell('docker','inspect','--format','{{.State.Pid}}','serialmonitor-usb-stream',capture=True).stdout).strip())
    code="import os,json,sys;from pathlib import Path;p=int(sys.argv[1]);print(json.dumps({'governor':Path('/sys/devices/system/cpu/cpufreq/policy0/scaling_governor').read_text().strip(),'cpus':sorted(os.sched_getaffinity(p))}))"
    self.normal=json.loads(self.pumping(r,lambda:self.remote(code,self.pid)));self.report['normal_policy']=self.normal
    self.report['backup']=str(self.pumping(r,self.board.backup));self.save()
    for bits,ticks in ((10,137),(12,163),(14,188),(16,2099)):
     config=Configuration(bits,160000000//ticks)
     for variant in ('A','B','B','A'):
      r.configure(Configuration(14,40000));actual=self.pumping(r,lambda:self.policy(variant))
      row={'bits':bits,'rate':config.actual_rate,'channels':config.channels,'ticks':ticks,'node_pairs':config.node_pairs,'variant':variant,'policy':actual,'ok':False};self.report['cases'].append(row);self.save()
      r.configure(config);send=[];peak=0;slack=None;start=time.monotonic();before=r.decoder.pairs
      while time.monotonic()-start<10:
       r.pump()
       for s in r.decoder.statuses:
        if s.get('rate')!=config.rate or s.get('bits')!=bits:continue
        if s.get('dropped') or s.get('fatal'):raise RuntimeError('MCU loss')
        if 'send_ticks' in s:
         send.append(s['send_ticks']);peak=max(peak,s['queue_peak']);slack=s['slack_ticks'] if slack is None else min(slack,s['slack_ticks'])
      elapsed=time.monotonic()-start;count=r.decoder.pairs-before
      row.update(ok=True,seconds=elapsed,samples=count,status=r.decoder.status,queue_peak=peak,slack_ticks_min=slack,send_observations=len(send))
      if send:row.update(send_mean_us=statistics.mean(send)/160,send_margin=1-statistics.mean(send)/(config.node_pairs*config.period))
      assert abs(count/elapsed/config.actual_rate-1)<.03,row
      self.save();print('CASE',bits,variant,'margin',row.get('send_margin'),'peak',peak,flush=True)
    self.report['ok']=True
  except Exception as exc:
   self.report['error']=str(exc);self.report['traceback']=traceback.format_exc();self.logs('failure_relay.log');raise
  finally:
   try:
    if self.prior is not None:
     with Connection(self.board.serial) as c:
      r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
      if self.normal is not None:self.pumping(r,lambda:self.policy('A'))
      r.configure(Configuration(**self.prior['adc']));r.generator(GeneratorConfig(**self.prior['generator']))
      final={'adc':asdict(r.config),'generator':asdict(r.generator().active)};before=r.decoder.pairs;start=time.monotonic()
      while time.monotonic()-start<10:r.pump()
      self.report.update(restored=final==self.prior,final=final,recovery={'ok':True,'samples':r.decoder.pairs-before,'status':r.decoder.status})
     self.report['identity_after']=instrument_identity(self.board.serial)
     assert self.report['identity_after']==self.report['identity_before']
     self.logs('final_relay.log')
   finally:self.save();print('REPORT',self.folder/'report.json',flush=True)
if __name__=='__main__':Campaign().run()
