"""Publish the exact Radio candidate after live validation; preserve rollback files."""
import hashlib,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
from dataclasses import asdict
from monitor.relay_identity import relay_digest
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from monitor.v17.receiver.unoq_switch import Mode
ROOT=Path(__file__).resolve().parents[2]

def install(x,exp,headers,expected_identity):
 pairs=[(exp/'oscilloscope/sketch'/n,ROOT/'arduino/v17/oscilloscope/sketch'/n) for n in headers]
 pairs += [(exp/'relay/config_relay_protocol.h',ROOT/'arduino/v17/relay/config_relay_protocol.h'),
           (exp/'tests/radio_test_backend.h',ROOT/'arduino/v17/tests/radio_test_backend.h')]
 presence={str(target.relative_to(ROOT)):target.exists() for _,target in pairs}
 backup=x.folder/'prior_local_sources.zip'
 with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as archive:
  for _,target in pairs:
   if target.exists():archive.write(target,target.relative_to(ROOT))
 x.report.update(local_presence=presence,local_backup=str(backup));x.save()
 for source,target in pairs:shutil.copyfile(source,target)
 x.report['local_sources_published']=True;x.save()
 for name,digest in x.report['relay_source_hashes'].items():
  if hashlib.sha256((ROOT/'arduino/v17/relay'/name).read_bytes()).hexdigest()!=digest:
   raise RuntimeError('Production relay differs from physically validated source: '+name)
 result=subprocess.run([sys.executable,'-m','unittest','tests.v17.test_wav_slots','tests.v17.test_radio_test_generator','tests.v17.test_radio_output','tests.v17.test_synth_credit_window'],cwd=ROOT,capture_output=True,text=True)
 (x.folder/'local_verification.log').write_text(result.stdout+result.stderr)
 x.report['local_verification_ok']=result.returncode==0;x.save()
 if result.returncode:raise RuntimeError('Local production regression failed')
 # The trial restored its low-rate boot settings, before any administrative Q work.
 identity=instrument_identity(x.board.serial)
 if identity!=expected_identity:raise RuntimeError('Candidate identity changed before publication')
 digest=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
 target='/home/arduino/.cache/serialmonitor/usb-stream-'+relay_digest(ROOT/'arduino/v17/relay')+'/unoq_stream'
 x.board.shell('mkdir','-p',target.rsplit('/',1)[0]);x.board.shell('cp',x.relay,target)
 if x.board.shell('sha256sum',target,capture=True).stdout.split()[0]!=digest:
  raise RuntimeError('Installed relay copy differs')
 x.report.update(installed_relay=target,installed_relay_sha256=digest,installed_identity=identity);x.save()
 # A new strict relay starts from epoch zero. Restart the MCU with it; a
 # late nonzero-epoch packet is not a valid initial acquisition boundary.
 import usb_stream
 usb_stream.stop(x.board);x.board.start();x.start_relay(target)
 installed_identity=instrument_identity(x.board.serial)
 if installed_identity!=identity:raise RuntimeError('Firmware changed during final restart')
 with Connection(x.board.serial) as connection:
  r=OutputReceiver(connection,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
  policy=x.pumping(r,x.policy)
  if policy!=x.normal:raise RuntimeError('Normal CPU policy did not restore')
  prior=x.report['prior'];r.configure(Configuration(**prior['adc']));r.generator(GeneratorConfig(**prior['generator']))
  final={'adc':asdict(r.config),'generator':asdict(r.generator().active)}
  before=r.decoder.pairs;began=time.monotonic()
  while time.monotonic()-began<10:r.pump()
  status=r.decoder.status;count=r.decoder.pairs-before
  okay=not(status['dropped'] or status['fatal']) and abs(count/(time.monotonic()-began)/r.config.actual_rate-1)<.02
  x.report.update(final_settings=final,settings_restored=final==prior,final_identity=identity,
                  recovery={'ok':okay,'samples':count,'status':status})
  if not okay or final!=prior:raise RuntimeError('Final acquisition/settings verification failed')
 x.report['installed']=True;x.save()

def rollback_local(x):
 if not x.report.get('local_sources_published'):return
 with zipfile.ZipFile(x.report['local_backup']) as archive:
  for name,present in x.report['local_presence'].items():
   target=ROOT/name
   if present:target.write_bytes(archive.read(name))
   else:target.unlink(missing_ok=True)
 x.report['local_sources_rolled_back']=True;x.save()
