"""Recover an unreadable initial stream using the last verified saved settings."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.unoq import Board,config_path
from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
from monitor.v17.board_owner import board_owner
from diagnosticos.probar_audio_owner_v16 import require_exclusive_monitor
import usb_stream
folder=ROOT/'experimentos/radio_dac_headroom_v17/probe_20261017_032105'
x=RelayCampaign.__new__(RelayCampaign);x.folder=folder;x.board=Board(json.loads(config_path('v17').read_text()))
x.report=json.loads((folder/'report.json').read_text())
known=json.loads((ROOT/'diagnosticos/resultados_v17/generador_radio_20261017_030024/report.json').read_text())
policy=json.loads((ROOT/'experimentos/otros_bits_cpu_relay_v17/qualification_20261017_021922/report.json').read_text())
x.normal=policy['normal_policy']
with board_owner(x.board.serial,'recuperar flujo inicial Radio V17'):
 require_exclusive_monitor()
 x.logs('initial_failure_relay.log')
 info=json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
 x.report.update(old_mounts=info['Mounts'],old_cpuset=info['HostConfig']['CpusetCpus'],old_cap_add=info['HostConfig']['CapAdd'] or [],old_scope_environment=[e for e in info['Config']['Env'] if e.startswith('SCOPE_')])
 x.report['old_relay']=next(m['Source'] for m in info['Mounts'] if m['Destination']=='/work/unoq_stream')
 x.report['prior']=known['prior'];x.report['prior_identity']=known['identity_after']
 x.report['recovery_settings_source']='Last verified Radio report; initial stream unreadable before mutation'
 x.report['backup']=str(x.board.backup());x.save()
 usb_stream.stop(x.board);x.board.start();x.start_relay(x.report['old_relay'],prior=True);x.restore_settings();x.save()
 print('RESTORED',x.report['restored'],x.report['recovery'],flush=True)
