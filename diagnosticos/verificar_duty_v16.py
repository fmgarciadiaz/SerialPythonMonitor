"""Short physical duty control/integrity check; restores captured Q profile."""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v16.receiver.unoq_autoload import connect_scope
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_generator import GeneratorConfig
from monitor.v16.receiver.unoq_switch import Mode
prior=json.loads((ROOT/'diagnosticos/resultados_v16/duty_prior_20261012.json').read_text())
report={'cases':[],'scope':'Physical generator ACK and ADC protocol integrity; LUT duty effective, analog duty not certified.'}
path=ROOT/'diagnosticos/resultados_v16/duty_live_20261012.json'
def save():path.write_text(json.dumps(report,indent=2)+'\n')
count=[0]
def samples(rows):count[0]+=len(rows)
try:
 with connect_scope('1060031107') as connection:
  r=OutputReceiver(connection,samples);r.decoder.numeric=True;r.select(Mode.SPI)
  assert r.generator().duty_capable
  try:
   r.configure(Configuration(14,100000))
   for frequency,duty in [(5000,25),(5000,50),(5000,75),(5000,1),(5000,99),(50000,1),(50000,99)]:
    c=GeneratorConfig(frequency=frequency*1000,final_frequency=frequency*1000,low=1000,high=3000,duty=duty)
    ack=r.generator(c);assert ack.active==c and ack.duty_capable
    before=count[0];began=time.monotonic()
    while time.monotonic()-began<2:r.pump()
    result={'frequency_hz':frequency,'duty_requested':duty,'duty_effective':c.effective_duty,'samples':count[0]-before,'seconds':time.monotonic()-began,'result':'PASS'}
    report['cases'].append(result);save();print(result,flush=True)
   r.configure(Configuration(8,1221374));c=GeneratorConfig(frequency=5000000,low=1000,high=3000,duty=25);assert r.generator(c).active==c
   before=count[0];began=time.monotonic()
   while time.monotonic()-began<10:r.pump()
   report['native_ch1']={'rate':r.config.rate,'duty':25,'samples':count[0]-before,'seconds':time.monotonic()-began,'result':'PASS'}
  finally:
   r.configure(Configuration(prior['bits'],prior['rate']));r.generator(GeneratorConfig(**prior['generator']))
   report['restored']=r.config==Configuration(prior['bits'],prior['rate']) and r.generator().active==GeneratorConfig(**prior['generator'])
   save();print('RESTORED',report['restored'],flush=True)
except Exception as exc:
 report['error']=str(exc);save();raise
