"""Isolated fast WAV functions; always restore exact MCU headers and Q state."""
import sys,json,time,traceback,hashlib,subprocess,os
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from diagnosticos.validar_generador_radio_v17 import main as audio_trial
import usb_stream
EXP=Path(__file__).resolve().parent
HEADERS=('wav_protocol.h','wav_dma.h','wav.h','crc32_fast.h','generator.h','wav_storage.h')
def main():
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 matrix='--radio-bits' in sys.argv
 seconds=int(sys.argv[sys.argv.index('--seconds')+1]) if '--seconds' in sys.argv else 60
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()))
 x.folder=EXP/('probe_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir();x.normal=None
 hashes={n:hashlib.sha256((EXP/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in HEADERS}
 expected_identity=None
 if matrix:
  from experimentos.radio_dac_headroom_v17.evidence import validated_identity
  evidence=Path(sys.argv[sys.argv.index('--evidence')+1])
  expected_identity=validated_identity(evidence,hashes)
 x.report={'ok':False,'restored':False,'cases':[],'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};changed=False
 shutil_source=Path(__file__).read_text();(x.folder/'runner.py').write_text(shutil_source)
 x.save()
 with board_owner(x.board.serial,'Radio DAC O2 aislado'):
  try:
   x.snapshot()
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'])
   x.normal=x.policy();x.report['normal_policy']=x.normal
   prior=x.folder/'prior_headers';prior.mkdir()
   x.report['prior_header_presence']={}
   for name in HEADERS:
    try:x.board.shell('test','-f',x.board.remote+'/sketch/'+name)
    except subprocess.CalledProcessError:x.report['prior_header_presence'][name]=False
    else:
     x.report['prior_header_presence'][name]=True
     x.board.run('pull',x.board.remote+'/sketch/'+name,str(prior/name))
   x.report['candidate_hashes']=hashes;x.save()
   usb_stream.stop(x.board);x.board.stop();changed=True
   x.sources=sorted(p for p in (EXP/'relay').iterdir() if p.is_file())
   x.report['relay_source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in x.sources}
   x.build()
   for name in HEADERS:x.board.run('push',str(EXP/'oscilloscope/sketch'/name),x.board.remote+'/sketch/'+name)
   x.board.start();x.start_relay(x.relay)
   for suffix in ('elf','bin'):
    try:x.board.run('pull',x.board.remote+'/.cache/sketch/sketch.ino.'+suffix,str(x.folder/('candidate.'+suffix)))
    except subprocess.CalledProcessError:pass
   from monitor.v17.bode_calibration import instrument_identity
   x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
   if expected_identity is not None and x.report['candidate_identity']!=expected_identity:
    raise RuntimeError('Loaded candidate differs from validated 120-s binary')
   from PyQt6 import QtWidgets
   qt_app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
   cases=[(10,1167883,20),(12,981595,20),(14,851063,20),(16,76226,20)] if matrix else [(8,1600000,seconds)]
   for bits,rate,duration in cases:
    sys.argv=['validar_generador_radio_v17.py','--bits',str(bits),'--rate',str(rate),'--seconds',str(duration)]
    report,folder=audio_trial(owner_context=nullcontext())
    x.report['cases'].append({'bits':bits,'rate':rate,'seconds':duration,'report':str(folder/'report.json'),'ok':report['ok'],'queue_peak':report.get('adc_queue_peak'),'adc_status':report.get('adc_status')});x.save()
    if not report['ok']:raise RuntimeError('Isolated audio trial failed')
   from experimentos.radio_dac_headroom_v17.storage_smoke import run as smoke
   x.report['storage_smoke']=smoke(x.board.serial);x.save()
   x.report['ok']=True
  except BaseException as exc:
   x.report['error']=repr(exc);x.report['traceback']=traceback.format_exc();x.save();raise
  finally:
   if changed:
    usb_stream.stop(x.board);x.board.stop()
    for name in HEADERS:
     if x.report['prior_header_presence'][name]:
      x.board.run('push',str(x.folder/'prior_headers'/name),x.board.remote+'/sketch/'+name)
     else:
      x.board.shell('python3','-c','from pathlib import Path;import sys;Path(sys.argv[1]).unlink(missing_ok=True)',x.board.remote+'/sketch/'+name)
    x.board.start();x.start_relay(x.report['old_relay'],prior=True)
   if x.report.get('prior'):x.restore_settings()
   x.save();print('REPORT',x.folder/'report.json',flush=True)
if __name__=='__main__':main()
