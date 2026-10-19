"""One-owner sustained GUI/DSP/A0 qualification; no firmware edits."""
import sys,time,json,traceback,contextlib,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from diagnosticos.validar_generador_radio_v17 import main as trial
from monitor.v17.bode_calibration import instrument_identity
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_switch import Mode
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig

def main():
 require_exclusive_monitor()
 folder=ROOT/'diagnosticos/resultados_v17'/('desacople_campaign_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
 report=dict(ok=False,restored=False,cases=[],scope=__doc__)
 def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 files=('app.py','radio_delivery_budget.py','processing.py','radio_output.py','radio_output_panel.py','radio_stream.py','radio_multiscan.py','receiver/unoq_config_receiver.py')
 report['hashes']={n:hashlib.sha256((ROOT/'monitor/v17'/n).read_bytes()).hexdigest() for n in files}
 report['identity']=instrument_identity('1060031107')
 with board_owner('1060031107','Validación prolongada desacople RADIO'):
  with Connection('1060031107') as c:
   r=OutputReceiver(c,lambda _:None);r.select(Mode.SPI);g=r.generator().active
   if g.enabled:raise RuntimeError('Generador ocupado')
   r.wav_request();end=time.monotonic()+3
   while r.wav_pending and time.monotonic()<end:r.pump()
   if r.wav_status is None or r.wav_status.state.value not in (0,3):raise RuntimeError('WAV ocupado')
   report['prior']=dict(adc={'bits':r.config.bits,'rate':r.config.rate},generator=__import__('dataclasses').asdict(g));save()
  matrix=[]
  for bits,rate in ((14,851063),(10,1250000)):
   for i,seconds in enumerate((60,120,120,120)):matrix.append((bits,rate,seconds,40000,False,i==0,f'qualification_{i}'))
  matrix.extend([(12,1066666,60,20000,True,True,'filter20_gain'),(16,76226,60,40000,False,True,'dual_gain'),(8,1403508,60,40000,False,True,'high_validated_gain')])
  if '--remaining' in sys.argv:
   matrix=[(10,1250000,120,40000,False,True,'independent_gui_gain'),(12,1066666,60,20000,True,True,'filter20_gain'),(16,76226,60,40000,False,True,'dual_gain'),(8,1403508,60,40000,False,True,'high_validated_gain')]
   report['scope']+=' Remaining matrix after ADC14 sustained underrun; no global qualification.'
  try:
   for index,(bits,rate,seconds,audio,filtered,gain,phase) in enumerate(matrix):
    row=dict(index=index,bits=bits,rate=rate,seconds=seconds,audio_rate=audio,filtered=filtered,phase=phase,ok=False)
    report['cases'].append(row);save();print('BEGIN',json.dumps(row),flush=True)
    sys.argv=['validar_generador_radio_v17','--bits',str(bits),'--rate',str(rate),'--seconds',str(seconds),'--audio-rate',str(audio),'--bandwidth','8000','--gui-stress']
    if filtered:sys.argv.append('--filter-input')
    if gain:sys.argv.append('--gain-stress')
    with (folder/f'case_{index}.log').open('w') as log,contextlib.redirect_stdout(log):
     outcome,where=trial(owner_context=contextlib.nullcontext())
    stats=outcome.get('joint_send_statistics') or {}
    row.update(ok=outcome['ok'] and outcome.get('restored',False),report=str(where/'report.json'),errors=outcome['errors'],source_error=outcome.get('source_error'),queue_peak=outcome.get('adc_queue_peak'),margin=stats.get('mean_margin'),slack=stats.get('minimum_slack_ticks'),gui_pending_peak=outcome.get('pending_peak'),dsp_pending_peak=outcome.get('dsp_pending_peak'),retained_bytes_peak=outcome.get('retained_bytes_peak'),gui_pauses=len(outcome.get('gui_pauses',[])),played=outcome.get('max_played'))
    row['headroom_ok']=bool(stats and stats['mean_margin']>=.1 and row['queue_peak']<4 and stats['minimum_slack_ticks']>0)
    save();print('END',json.dumps(row),flush=True)
    if not outcome.get('restored') or outcome.get('identity_after')!=report['identity']:raise RuntimeError('Restauración/identidad no confirmadas; campaña detenida')
    if not row['ok']:
     report.setdefault('failed_cases',[]).append(index)
     if '--remaining' not in sys.argv:
      report['stopped_after_failure']=index;break
  except Exception as exc:report['error']=str(exc);report['traceback']=traceback.format_exc()
  finally:
   try:
    with Connection('1060031107') as c:
     r=OutputReceiver(c,lambda _:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(**report['prior']['adc']));reply=r.generator(GeneratorConfig(**report['prior']['generator']));start=time.monotonic();before=r.decoder.pairs
     while time.monotonic()-start<10:r.pump()
     report['restored']=r.config==Configuration(**report['prior']['adc']) and __import__('dataclasses').asdict(reply.active)==report['prior']['generator']
     report['recovery']=dict(samples=r.decoder.pairs-before,status=dict(r.decoder.status))
    report['final_identity']=instrument_identity('1060031107')
   except Exception as exc:report['recovery_error']=str(exc)
   report['ok']=len(report['cases'])==len(matrix) and all(r['ok'] for r in report['cases']) and report['restored'] and report.get('final_identity')==report['identity']
   save();print('CAMPAIGN',folder,'ok',report['ok'],'restored',report['restored'],flush=True)
if __name__=='__main__':main()
