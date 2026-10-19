"""Verify production after a competing monitor exited; no blind reset."""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
from monitor.v17.receiver.unoq_usb import Connection
from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode
from tools.unoq import Board,config_path
p=Path(sys.argv[1]);d=json.loads(p.read_text())
x=RelayCampaign.__new__(RelayCampaign);x.board=Board(json.loads(config_path('v17').read_text()));x.folder=p.parent;x.report=d;x.normal=d['normal_policy']
with board_owner(x.board.serial,'verificar restauración tras interferencia'):
 require_exclusive_monitor()
 if 'ESTAB' in x.board.shell('ss','-tn','sport','=',':8766',capture=True).stdout:raise RuntimeError('Q still has another reader')
 with Connection(x.board.serial) as c:
  r=OutputReceiver(c,lambda b:None);r.decoder.numeric=True;r.select(Mode.SPI);r.configure(Configuration(14,40000))
 info=json.loads(x.board.shell('docker','inspect','serialmonitor-usb-stream',capture=True).stdout)[0]
 mounted=next(m['Source'] for m in info['Mounts'] if m['Destination']=='/work/unoq_stream')
 if mounted!=d['old_relay']:raise RuntimeError('Unexpected mounted relay; cannot declare production restored')
 x.restore_settings()
 assert d['restored'] and d['recovery']['ok']
 d.setdefault('recovery_history',[]).append({'verified_at':time.strftime('%Y-%m-%d %H:%M:%S'),'method':'After user closed monitor; exclusive lock; production relay path and firmware verified; exact ADC/generator restored; 10s strict continuity','recovery':d['recovery']})
 d['interference']['restoration_pending_exclusive_access']=False
 x.save();print('RESTORED',d['restored'],d['recovery'],flush=True)
