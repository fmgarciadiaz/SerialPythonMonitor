"""Renew an existing loopback reference only after a new held-out measurement passes."""
import sys,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import diagnosticos.validar_bode_v16 as check
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
class NumericReceiver(OutputReceiver):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.decoder.numeric=True
check.OutputReceiver=NumericReceiver
if __name__=='__main__':
 require_exclusive_monitor();check.main()
 if not check.report['ok']:raise SystemExit('Loopback reference not accepted; existing references preserved')
 cases=[c for c in check.report['cases'] if c['label']=='loopback_20_5000']
 a,b=[np.asarray(c['curve'],dtype=float) for c in cases[:2]]
 points=np.column_stack((a[:,0],(a[:,1]+b[:,1])/2,np.angle(np.exp(1j*np.deg2rad(a[:,2]))+np.exp(1j*np.deg2rad(b[:,2])),deg=True)))
 reference={'instrument':check.report['instrument'],'method':'tone','acquisition':check.report['profile'],'points':points.tolist(),'held_out_validation':check.report['held_out_reference'],'source_report':str(check.OUTPUT.relative_to(ROOT))}
 path=ROOT/'monitor/historico/v16/calibraciones'/f'bode_reference_{time.strftime("%Y%m%d_%H%M%S")}_1060031107_{check.PROFILE.bits}bit_{check.PROFILE.rate}_tone.json'
 path.write_text(json.dumps(reference,indent=2)+'\n');print('REFERENCE',path,flush=True)
