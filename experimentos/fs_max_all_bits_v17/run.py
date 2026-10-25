"""One private rate per campaign; exact rollback; no public profile edits."""
import argparse,hashlib,json,os,re,subprocess,sys,time,traceback,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from monitor.v17.receiver import unoq_native
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.bode_calibration import instrument_identity
import usb_stream
EXP=Path(__file__).resolve().parent
FILES=('wav_protocol.h','wav_dma.h','wav.h','crc32_fast.h','generator.h','wav_storage.h','native_profiles.h','high_rate_profile.h','sample_packing.h','sketch.ino')
def attempted_bits(reports):
 attempted=set()
 for report in reports:
  for row in report['cases']:
   match=re.fullmatch(r'adc(8|10|12|14|16)_(?:screen60|acceptance_[123])',row['stage'])
   if match:
    bits=int(match[1])
    if bits!=row['adc']['bits']:raise ValueError('Candidate stage/configuration mismatch')
    attempted.add(bits)
 return attempted

def continuation_reports(path,hashes,profile_hash):
 reports=[];seen=set()
 while path is not None:
  path=Path(path).resolve()
  if path in seen:raise ValueError('Continuation cycle')
  seen.add(path);report=json.loads(path.read_text())
  if not (report.get('restored') and report.get('recovery',{}).get('ok') and
          report.get('source_hashes')==hashes and report.get('candidate_profiles_sha256')==profile_hash):
   raise ValueError('Continuation is not restored or has different candidate sources/profiles')
  if reports and report.get('candidate_identity')!=reports[0].get('candidate_identity'):
   raise ValueError('Continuation chain firmware mismatch')
  reports.append(report)
  path=ROOT/report['continuation_of'] if report.get('continuation_of') else None
 return reports

def main():
 p=argparse.ArgumentParser();selection=p.add_mutually_exclusive_group(required=True)
 selection.add_argument('--bits',type=int,choices=(8,10,12,14,16));selection.add_argument('--all',action='store_true')
 p.add_argument('--qualify',action='store_true');p.add_argument('--evidence',type=Path)
 p.add_argument('--continue-from',dest='continuation',type=Path);a=p.parse_args()
 profiles=json.loads((EXP/'candidate_profiles.json').read_text())
 # Register private formats only inside this diagnostic process.
 for profile in profiles:profile['optimized_transport']=profile['bits']!=16
 unoq_native.PROFILES=unoq_native.PROFILES+tuple(profiles)
 available=sorted({v['bits'] for v in profiles if not v.get('purpose')})
 selected=available if a.all else [a.bits]
 if not set(selected)<=set(available):p.error('Resolution not in this prepared campaign')
 sources=sorted(v for v in (EXP/'relay').iterdir() if v.is_file())
 hashes={'sketch/'+n:hashlib.sha256((EXP/'oscilloscope/sketch'/n).read_bytes()).hexdigest() for n in FILES}
 hashes.update({'relay/'+v.name:hashlib.sha256(v.read_bytes()).hexdigest() for v in sources})
 continuation=None
 if a.continuation:
  if not a.qualify:p.error('--continue-from requires --qualify')
  ancestors=continuation_reports(a.continuation,hashes,hashlib.sha256((EXP/'candidate_profiles.json').read_bytes()).hexdigest())
  continuation=ancestors[0]
  attempted=attempted_bits(ancestors)
  selected=[bits for bits in selected if bits not in attempted]
  if not selected:p.error('No untested resolutions remain; failed stages will not be retried')
 expected=None
 if a.qualify:
  if a.evidence is None:p.error('--qualify requires restored 15-s screening evidence')
  old=json.loads(a.evidence.read_text())
  if not(old.get('ok') and old.get('restored') and old.get('recovery',{}).get('ok') and old.get('source_hashes')==hashes and set(selected)<=set(old.get('target_bits',[]))):
   raise ValueError('Screen evidence is incomplete, changed, or for another resolution')
  for bits in selected:
   if not any(v.get('ok') and v.get('headroom_ok') and v.get('requested_seconds')==15 and v['adc']['bits']==bits for v in old['cases']):
    raise ValueError('No successful 15-s headroom screen for ADC'+str(bits))
  expected=old['candidate_identity']
  if continuation is not None and continuation.get('candidate_identity')!=expected:
   raise ValueError('Continuation firmware differs from screening')
 subprocess.Popen(['/usr/bin/caffeinate','-dimsu','-w',str(os.getpid())])
 x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.headroom_only=False;x.normal=None
 x.folder=EXP/('qualification_'+time.strftime('%Y%m%d_%H%M%S'));x.folder.mkdir();x.sources=sources
 x.report=dict(ok=False,restored=False,cases=[],target_bits=selected,source_hashes=hashes,phase='qualification' if a.qualify else 'screen',acceptance_seconds=[60,120,120,120] if a.qualify else [15],runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 x.report['screening_evidence']=str(a.evidence) if a.evidence else None
 x.report['continuation_of']=str(a.continuation) if a.continuation else None
 x.report['candidate_profiles_sha256']=hashlib.sha256((EXP/'candidate_profiles.json').read_bytes()).hexdigest()
 x.report['host_profile_note']='ADC8 SPI40 uses 8 physical queue slots; initial screening omitted queue_slots and decoder assumed4. Corrected host metadata only; MCU/relay source hashes unchanged.'
 x.report['qualification']={}
 x.report['helper_hashes']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('diagnosticos/incorporar_adc1600_v17.py','experimentos/otros_bits_cpu_relay_v17/run.py')}
 (x.folder/'runner.py').write_bytes(Path(__file__).read_bytes());x.save();changed=False
 with zipfile.ZipFile(x.folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for key in hashes:z.write(EXP/('oscilloscope/'+key if key.startswith('sketch/') else key),key)
 with board_owner(x.board.serial,'Tasas privadas CRC '+str(selected)):
  try:
   x.snapshot()
   if continuation is not None and x.report['prior_identity']!=continuation['final_identity']:
    raise ValueError('Current production firmware differs from restored continuation')
   info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
   x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'])
   x.normal=x.policy();x.report['normal_policy']=x.normal
   prior=x.folder/'prior_headers';prior.mkdir();presence={};x.report['prior_header_presence']=presence
   for n in FILES:
    try:x.board.shell('test','-f',x.board.remote+'/sketch/'+n)
    except subprocess.CalledProcessError:presence[n]=False
    else:presence[n]=True;x.board.run('pull',x.board.remote+'/sketch/'+n,str(prior/n))
   x.save();usb_stream.stop(x.board);x.board.stop();changed=True;x.build()
   x.report['candidate_relay_sha256']=x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
   x.board.run('pull',x.relay,str(x.folder/'candidate_relay'));x.save()
   for n in FILES:x.board.run('push',str(EXP/'oscilloscope/sketch'/n),x.board.remote+'/sketch/'+n)
   x.board.start();x.start_relay(x.relay)
   x.report['candidate_identity']=instrument_identity(x.board.serial);x.save()
   if x.report['candidate_identity'] is None:raise ValueError('Candidate firmware identity unknown')
   if expected is not None and x.report['candidate_identity']!=expected:raise ValueError('Candidate binary changed since screen')
   for bits in selected:
    profile=next(v for v in profiles if v['bits']==bits and not v.get('purpose'))
    config=Configuration(bits,160000000//profile['ticks'])
    baseline={8:1600000,10:1250000,12:1066666,14:851063,16:76226}[bits]
    x.trial(Configuration(bits,baseline),10,'adc'+str(bits)+'_baseline',restart=True)
    x.normal_check('adc'+str(bits)+'_baseline_normal')
    if bits==16:
     warm=next(v for v in profiles if v.get('purpose'))
     x.trial(Configuration(16,160000000//warm['ticks']),10,'adc16_ch1_format',restart=True)
     x.normal_check('adc16_format_normal')
    stages=[('screen60',60)]+[('acceptance_'+str(i),120) for i in (1,2,3)] if a.qualify else [('screen15',15)]
    completed=[]
    for stage,seconds in stages:
     name='adc'+str(bits)+'_'+stage
     row=None
     try:
      row=x.trial(config,seconds,name,restart=True)
      completed.append(row)
     except Exception as exc:
      x.report.setdefault('screen_failures',[]).append(dict(bits=bits,error=repr(exc)))
     finally:
      x.logs(name+'_relay.log');x.normal_check(name+'_normal')
     if row is None:break # Preserve a failed stage; never selectively retry it.
    x.report['qualification'][str(bits)]=dict(
        integrity_ok=len(completed)==len(stages) and all(v['ok'] for v in completed),
        headroom_ok=len(completed)==len(stages) and all(v.get('headroom_ok',False) for v in completed),
        completed_stages=[v['stage'] for v in completed])
    x.save()
   x.report['ok']=all(v.get('ok') for v in x.report['cases'])
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
if __name__=='__main__':main()
