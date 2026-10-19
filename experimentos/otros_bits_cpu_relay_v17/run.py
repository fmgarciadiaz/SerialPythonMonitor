"""Qualify an isolated relay at accepted CH1 rates, then restore production."""
import sys,json,time,hashlib,traceback,zipfile,subprocess
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from diagnosticos.incorporar_adc1600_v17 import Integration
from tools.unoq import Board,config_path
from spi_benchmark import IMAGE,BUILD_IMAGE
import usb_stream
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_wav import State
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.bode_calibration import instrument_identity
from concurrent.futures import ThreadPoolExecutor
EXP=Path(__file__).resolve().parent

class RelayCampaign(Integration):
 def __init__(self):
  self.board=Board(json.loads(config_path('v17').read_text()));self.headroom_only=False
  self.folder=EXP/('qualification_'+time.strftime('%Y%m%d_%H%M%S'));self.folder.mkdir()
  self.sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.sources}
  self.report={'ok':False,'restored':False,'cases':[],'scope':'Isolated relay CH1 ADC10/12/14 at accepted rates; CPU policy plus bounded TCP partial sends','source_hashes':hashes,'acceptance_seconds':[60,120,120,120],'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
  self.changed=False;self.relay=None;self.normal=None
  with zipfile.ZipFile(self.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
   for p in self.sources:z.write(p,p.name)
 def snapshot(self):
  require_exclusive_monitor()
  if 'ESTAB' in self.board.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Q already has another reader')
  with Connection(self.board.serial) as c:
   r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI)
   gen=r.generator().active
   if gen.enabled:raise RuntimeError('Generator enabled; no test started')
   r.wav_request();deadline=time.monotonic()+3
   while r.wav_pending and time.monotonic()<deadline:r.pump()
   if r.wav_pending or r.wav_status is None or r.wav_status.state!=State.IDLE:raise RuntimeError('WAV occupied')
   self.report['prior']={'adc':asdict(r.config),'generator':asdict(gen)};self.save()
   r.configure(Configuration(14,40000))
  # Administrative Q work only after leaving the high-rate profile.
  self.report['prior_identity']=instrument_identity(self.board.serial)
  if self.report['prior_identity'] is None:raise RuntimeError('Unknown firmware identity')
  info=json.loads(self.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
  self.report['old_relay']=next(m['Source'] for m in info['Mounts'] if m['Destination']=='/work/unoq_stream')
  self.report['old_cap_add']=info['HostConfig']['CapAdd'] or []
  self.report['old_scope_environment']=[e for e in info['Config']['Env'] if e.startswith('SCOPE_')]
  self.report['backup']=str(self.board.backup());self.save()
 def restore_settings(self):
  # Called after the production relay/MCU have restarted at low load.
  identity=instrument_identity(self.board.serial)
  if identity!=self.report['prior_identity']:raise RuntimeError('Firmware identity changed')
  with Connection(self.board.serial) as c:
   r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
   self.report['restored_low_policy']=self.pumping(r,self.policy)
   if self.normal is not None and self.report['restored_low_policy']!=self.normal:raise RuntimeError('Original policy did not restore')
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:r.pump()
   prior=self.report['prior'];r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
   final={'adc':asdict(r.config),'generator':asdict(r.generator().active)};before=r.decoder.pairs;start=time.monotonic()
   while time.monotonic()-start<10:r.pump()
   self.report.update(final_settings=final,restored=final==prior,final_identity=identity,recovery={'ok':True,'samples':r.decoder.pairs-before,'status':r.decoder.status,'method':'No administrative Q calls after final high-rate configuration'})
  self.save()
 def pumping(self,r,fn):
  with ThreadPoolExecutor(max_workers=1) as pool:
   future=pool.submit(fn)
   while not future.done():r.pump()
   return future.result()
 def policy(self):
  pid=self.board.shell('docker','inspect','--format','{{.State.Pid}}',usb_stream.CONTAINER,capture=True).stdout.strip()
  code="import os,json,sys;from pathlib import Path;p=int(sys.argv[1]);print(json.dumps({'governor':Path('/sys/devices/system/cpu/cpufreq/policy0/scaling_governor').read_text().strip(),'cpus':sorted(os.sched_getaffinity(p)),'scheduler':os.sched_getscheduler(p),'priority':os.sched_getparam(p).sched_priority}))"
  return json.loads(self.board.shell('python3','-c',code,pid,capture=True).stdout)
 def start_relay(self,target,prior=False):
  usb_stream.stop(self.board);flags=[]
  for cap in self.report['old_cap_add'] if prior else ['SYS_NICE']:flags+=['--cap-add',cap]
  if prior:
   for m in self.report['old_mounts']:
    flags+=['--mount',f"type=bind,src={m['Source']},dst={m['Destination']}"+('' if m['RW'] else ',readonly')]
   for env in self.report['old_scope_environment']:flags+=['--env',env]
   if self.report.get('old_cpuset'):flags+=['--cpuset-cpus',self.report['old_cpuset']]
  else:
   flags+=['--mount',f'type=bind,src={target},dst=/work/unoq_stream,readonly','--mount','type=bind,src=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor,dst=/scope_cpu_governor']
  self.board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host','--read-only','--cap-drop','ALL',*flags,'--security-opt','no-new-privileges','--user','0:0','--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw','--entrypoint','/work/unoq_stream',IMAGE)
  deadline=time.monotonic()+15
  while time.monotonic()<deadline:
   if 'SPI ready: first verified frame' in self.logs('current_relay.log'):return
   time.sleep(.2)
  raise RuntimeError('Relay first frame not confirmed')
 def build(self):
  digest=hashlib.sha256(b''.join(p.read_bytes() for p in self.sources)).hexdigest()[:20]
  remote='/home/arduino/.cache/serialmonitor/cpu-relay-'+digest
  try:
   self.board.shell('test','-x',remote+'/unoq_stream')
  except subprocess.CalledProcessError:pass
  else:
   self.relay=remote+'/unoq_stream';self.report['candidate_relay']=self.relay;self.save();return
  self.board.shell('mkdir','-p',remote)
  for p in self.sources:self.board.run('push',str(p),remote+'/'+p.name)
  self.board.shell('docker','run','--rm','--user','0:0','--security-opt','no-new-privileges','--mount',f'type=bind,src={remote},dst=/build','--entrypoint','sh',BUILD_IMAGE,'-c','apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && cc -O2 -std=c11 -Wall -Wextra -Werror /build/unoq_config_stream.c -lm -o /build/unoq_stream')
  self.relay=remote+'/unoq_stream';self.report['candidate_relay']=self.relay;self.save()
 def trial(self,*args,**kwargs):
  require_exclusive_monitor()
  return super().trial(*args,**kwargs)
 def normal_check(self,stage):
  self.trial(Configuration(14,40000),10,stage)
  actual=self.policy();self.report.setdefault('normal_policy_checks',[]).append({'stage':stage,'policy':actual})
  self.save()
  if actual!=self.normal:raise RuntimeError('CPU policy did not restore: '+repr(actual))
 def run_campaign(self):
  self.save()
  try:
   self.snapshot()
   if self.report['prior']['generator']['enabled']:raise RuntimeError('Generator enabled; no test started')
   info=json.loads(self.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   self.report['old_mounts']=info['Mounts'];self.report['old_cpuset']=info['HostConfig']['CpusetCpus']
   if any(m['Type']!='bind' for m in info['Mounts']):raise RuntimeError('Unexpected relay mount')
   with Connection(self.board.serial) as c:
    r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(0);r.configure(Configuration(14,40000))
    self.normal=self.pumping(r,self.policy);self.report['normal_policy']=self.normal;self.save()
   self.changed=True;usb_stream.stop(self.board);self.board.stop()
   self.build() # ADC stopped; no physical qualification during compilation.
   profiles=((10,137),(12,163),(14,188));completed_stages={}
   if '--resume-from' in sys.argv:
    source=Path(sys.argv[sys.argv.index('--resume-from')+1]);old=json.loads(source.read_text())
    if not old['restored'] or old['source_hashes']!=self.report['source_hashes'] or old['final_identity']!=self.report['prior_identity']:raise RuntimeError('Resume evidence identity mismatch')
    inherited=[r for r in old['cases'] if r['stage'].startswith('adc10_')]
    high=[r for r in inherited if r['requested_seconds']>3]
    if len(inherited)!=8 or sorted(r['requested_seconds'] for r in high)!=[60,120,120,120] or not all(r['ok'] for r in inherited) or not all(r['headroom_ok'] for r in high):raise RuntimeError('ADC10 acceptance incomplete')
    self.report['cases']=inherited
    self.report['normal_policy_checks']=[r for r in old['normal_policy_checks'] if r['stage'].startswith('adc10_')]
    if any(r['policy']!=self.normal for r in self.report['normal_policy_checks']):raise RuntimeError('Resume policy mismatch')
    self.report['inherited_adc10_evidence']=str(source)
    self.report['protocol_revision']='Normal checks10s; measurements saved before clock/rate gate; host kept awake; no Q administration after final high-rate restore'
    from experimentos.otros_bits_cpu_relay_v17.resume_evidence import accepted_prefix
    rows,checks,names=accepted_prefix(old,12,(('screen60',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120)),self.normal)
    self.report['cases'].extend(rows);self.report['normal_policy_checks'].extend(checks)
    completed_stages[12]=names
    self.report['inherited_adc12_evidence']={'report':str(source),'stages':names}
    self.report['excluded_interrupted_cases']=[r for r in old['cases'] if r['stage'].startswith('adc12_') and r not in rows]
    profiles=((12,163),(14,188));self.save()
   for bits,ticks in profiles:
    config=Configuration(bits,160000000//ticks)
    for stage,seconds in (('screen60',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120)):
     if stage in completed_stages.get(bits,[]):continue
     row=self.trial(config,seconds,f'adc{bits}_{stage}',restart=True)
     self.logs(f'adc{bits}_{stage}_relay.log')
     self.normal_check(f'adc{bits}_{stage}_normal')
     if not row.get('headroom_ok',False):raise RuntimeError(f'Headroom failed for ADC{bits} {stage}')
   self.report['ok']=True
  except BaseException as exc:
   self.report['error']=repr(exc);self.report['traceback']=traceback.format_exc();self.save()
   try:self.logs('failure_relay.log')
   except Exception:pass
   raise
  finally:
   try:
    if self.changed:
     usb_stream.stop(self.board);self.board.start();self.start_relay(self.report['old_relay'],prior=True)
    if 'prior' in self.report and not self.report['prior']['generator']['enabled']:
     self.restore_settings()
     if self.report['final_identity']!=self.report['prior_identity']:raise RuntimeError('Firmware identity changed')
     if not self.report['restored'] or not self.report['recovery']['ok']:raise RuntimeError('Restoration not verified')
   except BaseException as exc:
    self.report['restoration_error']=repr(exc);self.report['restored']=False;raise
   finally:self.save();print('REPORT',self.folder/'report.json',flush=True)
if __name__=='__main__':
 from monitor.v17.board_owner import board_owner
 campaign=RelayCampaign()
 with board_owner(campaign.board.serial,'campaña CPU10/12/14'):
  campaign.run_campaign()
