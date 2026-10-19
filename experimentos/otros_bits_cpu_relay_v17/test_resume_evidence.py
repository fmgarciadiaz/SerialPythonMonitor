import copy,unittest
from experimentos.otros_bits_cpu_relay_v17.resume_evidence import accepted_prefix
class EvidenceTests(unittest.TestCase):
 def fixture(self):
  d={'cases':[],'normal_policy_checks':[]};stages=[('screen60',60),('acceptance_1',120)]
  for stage,seconds in stages:
   name='adc12_'+stage
   d['cases'] += [{'stage':name,'ok':True,'headroom_ok':True,'requested_seconds':seconds,'seconds':seconds+.01,'status':{'dropped':0,'fatal':0}}, {'stage':name+'_normal','ok':True,'requested_seconds':10,'seconds':10.01}]
   d['normal_policy_checks'].append({'stage':name+'_normal','policy':{'cpus':[0,1,2,3]}})
  return d,stages
 def test_failure_in_normal_check_excludes_otherwise_good_high_rate(self):
  d,stages=self.fixture();d['cases'][-1]['ok']=False
  rows,checks,names=accepted_prefix(d,12,stages,{'cpus':[0,1,2,3]})
  self.assertEqual(names,['screen60']);self.assertEqual(len(rows),2);self.assertEqual(len(checks),1)
 def test_no_reuse_past_missing_prefix_and_no_wrong_policy(self):
  d,stages=self.fixture();d['cases'].pop(0)
  self.assertEqual(accepted_prefix(d,12,stages,{'cpus':[0,1,2,3]})[2],[])
  d,stages=self.fixture()
  self.assertEqual(accepted_prefix(d,12,stages,{'cpus':[2]})[2],[])
 def test_duplicate_stage_rejected(self):
  d,stages=self.fixture();d['cases'].append(copy.deepcopy(d['cases'][0]))
  with self.assertRaises(ValueError):accepted_prefix(d,12,stages,{'cpus':[0,1,2,3]})
if __name__=='__main__':unittest.main()
