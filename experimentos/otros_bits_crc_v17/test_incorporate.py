import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experimentos.otros_bits_crc_v17 import incorporate as gate
class EvidenceTests(unittest.TestCase):
 def test_promote_requires_complete_restored_unchanged_four_stage_evidence(self):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name).resolve();exp=root/'experiment';(exp/'oscilloscope/sketch').mkdir(parents=True);(exp/'relay').mkdir()
   hashes={}
   for key in ['sketch/'+n for n in gate.FILES]+['relay/main.c']:
    p=exp/('oscilloscope/'+key if key.startswith('sketch/') else key);p.write_text(key)
    hashes[key]=hashlib.sha256(p.read_bytes()).hexdigest()
   profiles=[dict(bits=b,channels=1,ticks=t,node_pairs=n,internal_only=True,headroom=False,validation='unmeasured') for b,t,n in ((10,128,5568),(12,150,4608))]
   (exp/'candidate_profiles.json').write_text(json.dumps(profiles))
   base=dict(ok=True,restored=True,target_bits=[10,12],recovery=dict(ok=True,status=dict(dropped=0,fatal=0)),source_hashes=hashes,candidate_identity=dict(firmware_sha256='f'*64),prior_identity={'firmware_sha256':'a'*64},final_identity={'firmware_sha256':'a'*64})
   screen=copy.deepcopy(base);acceptance=copy.deepcopy(base);screen['cases']=[];acceptance['cases']=[]
   for profile in profiles:
    for report,stage,seconds in [(screen,'screen60',60)]+[(acceptance,'acceptance_'+str(i),120) for i in (1,2,3)]:
     report['cases'].append(dict(stage='adc'+str(profile['bits'])+'_'+stage,ok=True,headroom_ok=True,seconds=seconds,requested_seconds=seconds,adc=dict(bits=profile['bits'],rate=160000000//profile['ticks']),node_pairs=profile['node_pairs'],period=profile['ticks'],scheduler=dict(policy=1,priority=10),wall_monotonic_drift_seconds=0,status=dict(dropped=0,fatal=0),metrics=dict(mean_send_headroom=.18,maxima=dict(queue_peak=3,slack_ticks=10))))
   s=root/'screen.json';a=root/'accepted.json'
   def check():
    s.write_text(json.dumps(screen));a.write_text(json.dumps(acceptance));return gate.qualified_profiles(s,a)
   with patch.object(gate,'ROOT',root),patch.object(gate,'EXP',exp):
    self.assertEqual([p['bits'] for p in check()[0]],[10,12])
    for field,value in [('restored',False),('candidate_identity',{'firmware_sha256':'changed'})]:
     previous=acceptance[field];acceptance[field]=value
     with self.assertRaises(ValueError):check()
     acceptance[field]=previous
    acceptance['cases'][-1]['seconds']=119
    with self.assertRaises(ValueError):check()
    acceptance['cases'][-1]['seconds']=120
    acceptance['cases'][-1]['metrics']['maxima']['queue_peak']=4
    with self.assertRaises(ValueError):check()
    acceptance['cases'][-1]['metrics']['maxima']['queue_peak']=3
    (exp/'oscilloscope/sketch/crc32_fast.h').write_text('changed')
    with self.assertRaisesRegex(ValueError,'Candidate changed'):check()
if __name__=='__main__':unittest.main()
