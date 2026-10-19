"""A functional matrix may only reuse an exact, restored 120-s candidate."""
import json
from pathlib import Path
def validated_identity(path,hashes):
 evidence=json.loads(Path(path).read_text())
 if not (evidence.get('ok') and evidence.get('restored') and evidence.get('recovery',{}).get('ok')):
  raise ValueError('Firmware evidence incomplete or restoration unverified')
 if evidence.get('candidate_hashes')!=hashes:raise ValueError('Candidate source hashes changed')
 for case in evidence.get('cases',[]):
  if not case.get('ok'):continue
  trial=json.loads(Path(case['report']).read_text())
  if (trial.get('ok') and trial.get('restored') and trial.get('requested_audio_seconds',0)>=120
      and trial.get('adc')=={'bits':8,'rate':1600000}
      and trial.get('max_played',0)>40000*(trial['requested_audio_seconds']-4)
      and abs(trial.get('wall_monotonic_drift_seconds',0))<=2):
   identity=trial.get('identity_before')
   if identity and identity==trial.get('identity_after'):return identity
 raise ValueError('No complete 120-s ADC1.6M + Radio40k evidence')
