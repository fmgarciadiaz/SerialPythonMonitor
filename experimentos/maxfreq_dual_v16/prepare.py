"""Compile/import isolated sweep app and relay, without changing stable sources."""
import sys,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from unoq import Board,config_path
import usb_stream
def boards():
 stable=Board(json.loads(config_path('v16').read_text()));config=dict(stable.config)
 config.update(name='Scope V16 Max Frequency Dual Experimental',remote_app='/home/arduino/ArduinoApps/scope-v16-maxfreq-dual-experimental',local_app='experimentos/maxfreq_dual_v16/arduino/historico/v16/oscilloscope')
 return stable,Board(config)
def main():
 stable,candidate=boards()
 if not (EXP/'prior.json').exists():raise RuntimeError('Capture the current production profile after CH1 integration')
 candidate.compile()
 manifest={'backup':str(stable.backup()),'stable_relay':usb_stream.binary(stable,p992=True,audio=True)}
 apps=json.loads(candidate.cli('app','list','--format','json',capture=True).stdout).get('apps',[])
 if any(a.get('name')==candidate.config['name'] for a in apps):candidate.push_sources(candidate.check_sources(),candidate.remote)
 else:candidate.create()
 usb_stream.ROOT=EXP
 try:
  try:manifest['candidate_relay']=usb_stream.binary(candidate,p992=True,audio=True)
  except subprocess.CalledProcessError:manifest['candidate_relay']=usb_stream.binary(candidate,build=True,p992=True,audio=True)
 finally:usb_stream.ROOT=ROOT
 (EXP/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(manifest,flush=True)
if __name__=='__main__':main()
