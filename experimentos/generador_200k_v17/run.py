"""Isolated generator timing/analog capture; always restore installed headers/Q."""
import sys,json,time,hashlib,traceback,subprocess,shutil
from pathlib import Path
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.bode_calibration import instrument_identity
import monitor.v17.receiver.unoq_generator as host_generator
import usb_stream
EXP=Path(__file__).resolve().parent
HEADERS=('generator_protocol.h','generator_timing.h')
def main():
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.normal=None
 x.folder=EXP/('probe_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir()
 x.report={'ok':False,'restored':False,'cases':[],'qualification_requested_seconds':120 if '--qualify' in sys.argv else 0,'wiring':'User confirmed A0→CH2/A3, common ground','analog_scope':'ADC8 dual; fundamental amplitude/frequency, not calibrated THD or edge speed'};changed=False
 relay=EXP/'relay';shutil.copytree(ROOT/'arduino/v17/relay',relay,dirs_exist_ok=True)
 p=relay/'config_relay_protocol.h';p.write_text(p.read_text().replace('>50000000','>200000000'))
 x.sources=sorted(p for p in relay.iterdir() if p.is_file());x.save()
 with board_owner(x.board.serial,'Generador seno150k/cuadrada200k aislado'):
  try:
   x.snapshot();info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus']);x.save()
   prior=x.folder/'prior_headers';prior.mkdir()
   for name in HEADERS:x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name))
   usb_stream.stop(x.board);x.board.stop();changed=True
   x.build()
   for name in HEADERS:x.board.run('push',str(EXP/'include'/name),x.board.remote+'/sketch/'+name)
   x.board.start();x.start_relay(x.relay)
   x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
   host_generator.MAX_FREQUENCY_MHZ=200000000
   blocks=[]
   def collect(batch):
    if sum(map(len,blocks))<65536:blocks.append(np.asarray(batch.array if hasattr(batch,'array') else batch,dtype=float))
   with Connection(x.board.serial) as connection:
    r=OutputReceiver(connection,collect);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(8,632411))
    for wave in ((1,0,1,0,1,0) if "--qualify" in sys.argv else (1,0)):
     for hz in (((150000,) if wave==1 else (200000,)) if "--qualify" in sys.argv else (25000,50000,62500,73333,87500,100000,112500,123456,137500,150000) if wave==1 else (50000,87500,100000,123456,150000,175000,200000)):
      case_started=time.monotonic()
      cfg=GeneratorConfig(wave=wave,frequency=hz*1000,final_frequency=hz*1000,low=1427,high=2668)
      reply=r.generator(cfg);deadline=time.monotonic()+.15
      while time.monotonic()<deadline:r.pump()
      blocks.clear();deadline=time.monotonic()+.25
      while time.monotonic()<deadline:r.pump()
      if '--qualify' in sys.argv:
       until=time.monotonic()+120;last=0
       while time.monotonic()<until:
        r.pump();remaining=int(until-time.monotonic())
        if remaining//30!=last:last=remaining//30;print('LIVE',wave,hz,'remaining',remaining,flush=True)
      raw=np.concatenate(blocks);name=f'wave{wave}_{hz}.npy';np.save(x.folder/name,raw)
      t=np.arange(len(raw))/r.config.actual_rate;y=raw[:,2]*3.3/255
      t=t-t[0];n=len(y);window=np.hanning(n);spectrum=abs(np.fft.rfft((y-y.mean())*window));freqs=np.fft.rfftfreq(n,r.config.dt_us*1e-6)
      region=(freqs>hz*.8)&(freqs<hz*1.2);indices=np.flatnonzero(region);k=indices[np.argmax(spectrum[region])];a,b,c=np.log(np.maximum(spectrum[k-1:k+2],1e-12));delta=.5*(a-c)/(a-2*b+c);frequency=(k+delta)*r.config.actual_rate/n
      fit=np.column_stack((np.sin(2*np.pi*frequency*t),np.cos(2*np.pi*frequency*t),np.ones(n)));coef=np.linalg.lstsq(fit,y,rcond=None)[0]
      case={'wall_seconds':time.monotonic()-case_started,'wave':wave,'requested_hz':hz,'measured_hz':frequency,'fundamental_vpp':2*float(np.hypot(*coef[:2])),'sample_vpp':float(np.ptp(y)),'mean_v':float(y.mean()),'samples':n,'raw':name,'adc_status':r.decoder.status,'reply_matches':reply.active==cfg,'running':bool(reply.running)}
      x.report['cases'].append(case);x.save();print('CASE',json.dumps(case),flush=True)
    r.generator(GeneratorConfig(enabled=0))
   x.report['ok']=all(c['reply_matches'] and c['running'] and abs(c['measured_hz']/c['requested_hz']-1)<.03 for c in x.report['cases'])
  except BaseException as exc:
   x.report.update(error=repr(exc),traceback=traceback.format_exc());x.save();raise
  finally:
   host_generator.MAX_FREQUENCY_MHZ=50000000
   if changed:
    usb_stream.stop(x.board);x.board.stop()
    for name in HEADERS:x.board.run('push',str(x.folder/'prior_headers'/name),x.board.remote+'/sketch/'+name)
    x.board.start();x.start_relay(x.report['old_relay'],prior=True)
   if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
