"""Deploy scoped V16 transport; validate transitions and restore prior settings."""
import json,sys,time,hashlib,traceback,subprocess,zipfile
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
import usb_stream
from experimentos.megaboom_ch1_3584_v16.run import start_relay
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_wav import State
from monitor.v16.bode_calibration import instrument_identity
from monitor.v16.numeric_batch import NumericBatch,SampleClock
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor

FOLDER=Path(__file__).resolve().parent/('physical_'+time.strftime('%Y%m%d_%H%M%S'));FOLDER.mkdir()
report={'ok':False,'restored':False,'cases':[],'scope':'V16 scoped ADC8/CH1 1403508 integration; existing transport on every other profile','source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sorted((ROOT/'arduino/v16').rglob('*.h')),*sorted((ROOT/'arduino/v16').rglob('*.ino')),*sorted((ROOT/'arduino/v16/relay').glob('*.c')),ROOT/'tools/usb_stream.py',ROOT/'monitor/v16/receiver/native_profiles.json']}}
board=Board(json.loads(config_path('v16').read_text()));old_relay=None;changed=False;remote_backup=None

def save():(FOLDER/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def scheduler():
 info=json.loads(board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
 if not info['State']['Running'] or info['State']['Pid']<=0:raise RuntimeError('Relay exited before scheduler query')
 return json.loads(board.shell('python3','-c','import os,json,sys; p=int(sys.argv[1]); print(json.dumps({"policy":os.sched_getscheduler(p),"priority":os.sched_getparam(p).sched_priority}))',str(info['State']['Pid']),capture=True).stdout)
def scheduler_live(receiver):
 # Metadata may take hundreds of milliseconds: never pause the only ADC reader.
 with ThreadPoolExecutor(max_workers=1) as pool:
  pending=pool.submit(scheduler)
  while not pending.done():receiver.pump()
  return pending.result()
def settings(receiver):return {'adc':asdict(receiver.config),'generator':asdict(receiver.generator().active)}
def recovery():
 with Connection(board.serial) as conn:
  r=OutputReceiver(conn,lambda rows:None);r.decoder.numeric=True;r.select(Mode.SPI)
  r.generator(GeneratorConfig(enabled=0));r.configure(Configuration(**report['prior']['adc']));r.generator(GeneratorConfig(**report['prior']['generator']))
  report['final_settings']=settings(r);report['restored']=report['final_settings']==report['prior']
  before=r.decoder.pairs;start=time.monotonic()
  while time.monotonic()-start<10:r.pump()
  report['recovery']={'samples':r.decoder.pairs-before,'status':r.decoder.status,'ok':True}
  report['final_scheduler']=scheduler_live(r)
  assert report['final_scheduler']=={'policy':0,'priority':0}
 save()
def trial(config,seconds,stage,restart=False):
 if restart:
  usb_stream.stop(board);board.start();start_relay(board,report['relay'])
 row={'adc':asdict(config),'seconds_requested':seconds,'stage':stage,'ok':False};start=None
 try:
  with Connection(board.serial) as conn:
   clock=SampleClock(config.timestamp_hz);last=None
   def reset(active):
    nonlocal clock,last
    clock=SampleClock(active.timestamp_hz);last=None
   def collect(rows):
    nonlocal last
    b=NumericBatch(rows.array if hasattr(rows,"array") else rows,r.config.maximum,clock,r.config.channels)
    t=b.columns['Tiempo (us)'];assert np.all(np.abs(np.diff(t)-r.config.dt_us)<1e-5)
    if last is not None:assert abs(t[0]-last-r.config.dt_us)<1e-5
    if r.config.channels==1:assert np.isnan(b.columns['CH2']).all()
    last=float(t[-1])
   r=OutputReceiver(conn,lambda rows:None);r.decoder.numeric=True;r.on_configuration=reset;r.select(Mode.SPI);r.generator(GeneratorConfig(enabled=0));r.configure(config)
   reset(r.config);r.on_samples=collect;row['scheduler']=({'policy':1,'priority':10} if config.rate==1403508 else scheduler_live(r))
   row['scheduler_verification']='Relay verifies kernel getters on profile entry; logs persisted' if config.rate==1403508 else 'Live query while continuously pumping'
   assert row['scheduler']==({'policy':1,'priority':10} if config.rate==1403508 else {'policy':0,'priority':0})
   until=time.monotonic()+1
   while time.monotonic()<until:r.pump()
   row['initial_status']=dict(r.decoder.status);before=r.decoder.pairs;start=time.monotonic();wall=time.time();next_log=start+30;send=[];maxima={};peak_events=[];previous_peak=None
   while time.monotonic()-start<seconds:
    r.pump()
    for st in r.decoder.statuses:
     assert not st['dropped'] and not st['fatal']
     if 'send_ticks' in st:
      send.append(st['send_ticks'])
      for key in ('queue_peak','copy_ticks','poll_ticks'):maxima[key]=max(maxima.get(key,0),st[key])
      maxima['slack_ticks']=min(maxima.get('slack_ticks',0xffffffff),st['slack_ticks'])
      if st['queue_peak']!=previous_peak:peak_events.append({'seconds':time.monotonic()-start,'status':dict(st)});previous_peak=st['queue_peak']
    if time.monotonic()>=next_log:print('PROGRESS',stage,config.bits,config.rate,round(time.monotonic()-start),flush=True);next_log+=30
   elapsed=time.monotonic()-start;count=r.decoder.pairs-before
   row.update(ok=True,seconds=elapsed,samples=count,observed_rate=count/elapsed,status=r.decoder.status,peak_events=peak_events,wall_monotonic_drift=time.time()-wall-elapsed)
   assert abs(row['observed_rate']/config.actual_rate-1)<.02 and abs(row['wall_monotonic_drift'])<2
   if send:
    mean=float(np.mean(send));budget=config.node_pairs*config.period
    row['metrics']={'mean_send_headroom':1-mean/budget,'send_mean_us':mean/160,'maxima':maxima}
    row['headroom_ok']=mean<budget*.9 and maxima['queue_peak']<4 and maxima['slack_ticks']>0
  print('END',stage,config.bits,config.rate,'OK',row['ok'],'MARGIN',row.get('headroom_ok'),flush=True)
 except BaseException as exc:
  row.update(ok=False,error=repr(exc));report['cases'].append(row);save();raise
 report['cases'].append(row);save();return row

def diagnose_mcu():
    # Read-only recipe: no reset, erase or flash commands. The failing candidate
    # is briefly halted for registers, then resumed before the normal rollback.
    elf=FOLDER/'failed_debug.elf'
    board.run('pull',board.remote+'/.cache/sketch/sketch.ino_debug.elf',str(elf))
    board.run('pull',board.remote+'/.cache/sketch/sketch.ino.map',str(FOLDER/'failed.map'))
    nm=Path.home()/'Library/Arduino15/packages/arduino/tools/arm-none-eabi-gcc/7-2017q4/bin/arm-none-eabi-nm'
    symbols=subprocess.check_output([str(nm),'-n','-C',str(elf)],text=True)
    (FOLDER/'failed_symbols.txt').write_text(symbols)
    commands=['reset_config none','init','halt','reg pc','reg xpsr','reg msp','reg psp','mdw 0xe000ed28 6']
    for line in symbols.splitlines():
        parts=line.split(None,2)
        if len(parts)==3 and parts[1].lower() in ('b','d') and parts[2] in ('ready','last_result','fault_dma','fault_sr','acquisition::threads_started','acquisition::fatal_errors','acquisition::dropped_nodes'):
            commands+=['echo "'+parts[2]+'"','mdw 0x'+parts[0]+' 1']
    commands+=['resume','shutdown']
    cfg=FOLDER/'inspect.cfg';cfg.write_text('\n'.join(commands)+'\n')
    tool=Path.home()/'Library/Arduino15/packages/arduino/tools/remoteocd/0.1.1/remoteocd'
    result=subprocess.run([str(tool),'upload','--adb-path',board.adb,'-s',board.serial,'-f',str(cfg),str(elf)],capture_output=True,text=True,timeout=40)
    (FOLDER/'mcu_state.log').write_text(result.stdout+'\n'+result.stderr)
    report['mcu_read_result']=result.returncode

def main():
 with zipfile.ZipFile(FOLDER/'sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for rel in report['source_hashes']:archive.write(ROOT/rel,rel)
 global old_relay,changed,remote_backup
 require_exclusive_monitor();report['prior_identity']=instrument_identity(board.serial)
 try:
  if 'ESTAB' in board.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Q has another owner')
  with Connection(board.serial) as conn:
   r=OutputReceiver(conn,lambda rows:None);r.decoder.numeric=True;r.select(Mode.SPI);r.wav_request();end=time.monotonic()+3
   while r.wav_pending and time.monotonic()<end:r.pump()
   assert r.wav_status.state==State.IDLE
   report['prior']=settings(r)
   if len(sys.argv)>1:
    report['snapshot_after_recovery']=report['prior']
    report['prior']=json.loads(Path(sys.argv[1]).read_text())['prior']
    report['prior_recovered_from']=sys.argv[1]
  info=json.loads(board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0];old_relay=next(m['Source'] for m in info['Mounts'] if m['Destination']=='/work/unoq_stream');report['old_relay']=old_relay
  report['backup']=str(board.backup());save();usb_stream.stop(board);board.stop()
  remote_backup='/home/arduino/.cache/serialmonitor/v16-before-send1400-'+time.strftime('%Y%m%d%H%M%S');report['remote_backup']=remote_backup
  board.run('push',report['backup'],'/tmp/v16-before-send1400.zip')
  board.shell('python3','-c','import zipfile,pathlib,sys; root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True); z=zipfile.ZipFile("/tmp/v16-before-send1400.zip"); [(root.joinpath(*pathlib.PurePosixPath(n).parts[1:]).parent.mkdir(parents=True,exist_ok=True),root.joinpath(*pathlib.PurePosixPath(n).parts[1:]).write_bytes(z.read(n))) for n in z.namelist() if not n.endswith("/")]',remote_backup)
  changed=True;report['relay']=usb_stream.binary(board,build=True,p992=True,audio=True);save()
  board.push_sources(board.check_sources(),board.remote);board.start();start_relay(board,report['relay'])
  trial(Configuration(14,40000),10,'legacy_before')
  # Every stage configures the high profile then the next ordinary profile checks deactivation.
  for stage,seconds in [('finalist',60),('acceptance_1',120),('acceptance_2',120),('acceptance_3',120),('endurance',600)]:
   trial(Configuration(8,1403508),seconds,stage,restart=True)
   trial(Configuration(10,909090),10,'normal_after_'+stage)
  trial(Configuration(14,363636),10,'dual_after')
  trial(Configuration(16,40000),10,'adc16_after')
  report['ok']=True;report['headroom_accepted']=all(c.get('headroom_ok',False) for c in report['cases'] if c['adc']['rate']==1403508)
 except BaseException as exc:
  report['error']=repr(exc);traceback.print_exc()
  try:(FOLDER/'failure_relay.log').write_text(board.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout)
  except Exception as log_error:report['log_error']=repr(log_error)
  if changed and 'Relay no confirmó' in str(exc):
   try:diagnose_mcu()
   except Exception as debug_error:report['mcu_read_error']=repr(debug_error)
  if changed:
   try:
    usb_stream.stop(board);board.stop()
    board.shell('python3','-c','import shutil,sys;shutil.copytree(sys.argv[2],sys.argv[1],dirs_exist_ok=True)',board.remote,remote_backup)
    board.start();start_relay(board,old_relay);report['rolled_back']=True
   except Exception as failure:report['rollback_error']=repr(failure)
  elif old_relay:
   try:board.start();start_relay(board,old_relay)
   except Exception as failure:report['restart_error']=repr(failure)
 finally:
  if report.get('prior'):
   try:recovery()
   except Exception as exc:report['recovery_error']=repr(exc)
  report['final_identity']=instrument_identity(board.serial)
  try:(FOLDER/'final_relay.log').write_text(board.run('shell','docker logs '+usb_stream.CONTAINER+' 2>&1',capture=True).stdout)
  except Exception as exc:report['final_log_error']=repr(exc)
  save()
 print('REPORT',FOLDER/'report.json','OK',report['ok'],'RESTORED',report['restored'],flush=True)
 return 0 if report['ok'] and report['restored'] else 1
if __name__=='__main__':raise SystemExit(main())
