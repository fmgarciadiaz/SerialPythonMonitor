import json,tempfile,unittest
from pathlib import Path
from experimentos.radio_dac_headroom_v17.evidence import validated_identity
class FirmwareEvidenceTests(unittest.TestCase):
 def test_matrix_rejects_short_changed_or_unrestored_candidates(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);path=root/'evidence.json';trial=root/'trial.json'
   identity={'firmware_sha256':'a'*64}
   data={'ok':True,'restored':True,'requested_audio_seconds':120,'adc':{'bits':8,'rate':1600000},'max_played':4700000,'identity_before':identity,'identity_after':identity}
   outer={'ok':True,'restored':True,'recovery':{'ok':True},'candidate_hashes':{'crc':'abc'},'cases':[{'ok':True,'report':str(trial)}]}
   trial.write_text(json.dumps(data));path.write_text(json.dumps(outer))
   self.assertEqual(validated_identity(path,{'crc':'abc'}),identity)
   with self.assertRaisesRegex(ValueError,'hashes'):validated_identity(path,{'crc':'changed'})
   data['requested_audio_seconds']=60;trial.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'120-s'):validated_identity(path,{'crc':'abc'})
   outer['restored']=False;path.write_text(json.dumps(outer))
   with self.assertRaisesRegex(ValueError,'restoration'):validated_identity(path,{'crc':'abc'})
