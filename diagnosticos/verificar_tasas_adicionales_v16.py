"""60-second additional-rate screening; preserves prior Q configuration."""
import sys,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.historico.v16.receiver.unoq_autoload import connect_scope
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_generator import GeneratorConfig
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_native import PROFILES
prior=json.loads((ROOT/'diagnosticos/resultados_v16/additional_rates_prior_20261012.json').read_text())
profiles=[p for p in PROFILES if p.get('purpose')]
path=ROOT/'diagnosticos/resultados_v16/additional_rates_60s_20261012.json'
report={'scope':'60 s per added profile, normal square generator 5 kHz, strict ADC CRC/sequence/epoch/index/timestamps/loss checks; no sustained-margin or analog acceptance','cases':[],'restored':False,'ok':False}
report['profile_sha256']=hashlib.sha256((ROOT/'monitor/historico/v16/receiver/additional_profiles.json').read_bytes()).hexdigest()
def save():path.write_text(json.dumps(report,indent=2)+'\n')
count=[0]
def samples(rows):count[0]+=len(rows)
with connect_scope('1060031107') as connection:
 r=OutputReceiver(connection,samples);r.decoder.numeric=True;r.select(Mode.SPI)
 try:
  r.generator(GeneratorConfig(frequency=5000000,final_frequency=5000000,low=1000,high=3000))
  for profile in profiles:
   c=Configuration(profile['bits'],160000000//profile['ticks']);r.configure(c)
   count[0]=0;metrics={};start=time.monotonic();heartbeat=start
   case={'bits':c.bits,'rate':c.rate,'actual_rate':c.actual_rate,'ticks':c.period,'node_pairs':c.node_pairs,'purpose':profile['purpose'],'status':'RUNNING'}
   report['cases'].append(case);save();print('START',c.bits,c.rate,flush=True)
   while time.monotonic()-start<60:
    r.pump()
    for status in r.decoder.statuses:
     if 'produced' in status:metrics[status['produced']]=dict(status)
    now=time.monotonic()
    if now-heartbeat>=10:
     heartbeat=now;case.update(elapsed_s=round(now-start,3),samples=count[0]);save();print('PROGRESS',c.bits,c.rate,round(now-start),count[0],flush=True)
   elapsed=time.monotonic()-start
   case.update(elapsed_s=elapsed,samples=count[0],host_delivery_rate=count[0]/elapsed)
   save()
   # Host monotonic and nominal MCU tick frequency are independent clocks.
   # Exact continuity comes from CRC/sequence/index/TIM5 checks, not wall time.
   assert count[0]>=c.actual_rate*elapsed*.99, 'Delivery below 99% of nominal; inspect clocks/latency'

   statuses=list(metrics.values())
   case.update(status='PASS',elapsed_s=elapsed,samples=count[0],dropped=max((s['dropped'] for s in statuses),default=0),fatal=max((s['fatal'] for s in statuses),default=0),queue_peak=max((s['queue_peak'] for s in statuses),default=0),slack_ticks_min=min((s['slack_ticks'] for s in statuses),default=0),send_ticks_mean=sum(s['send_ticks'] for s in statuses)/max(1,len(statuses)))
   save();print('PASS',c.bits,c.rate,'samples',count[0],'queue',case['queue_peak'],flush=True)
  report['ok']=True
 except Exception as exc:
  report['error']=str(exc);save();raise
 finally:
  try:
   r.configure(Configuration(prior['bits'],prior['rate']));r.generator(GeneratorConfig(**prior['generator']))
   report['restored']=r.config==Configuration(prior['bits'],prior['rate']) and r.generator().active==GeneratorConfig(**prior['generator'])
   started=time.monotonic()
   while time.monotonic()-started<3:r.pump()
  except Exception as exc:report['restore_error']=str(exc)
  save();print('RESTORED',report['restored'],flush=True)
