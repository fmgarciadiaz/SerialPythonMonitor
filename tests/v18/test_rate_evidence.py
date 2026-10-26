import copy,json,tempfile,unittest
from pathlib import Path
from monitor.v18.rate_evidence import load_evidence,evidence_text
from monitor.v18.receiver.unoq_acquisition import Configuration


class RateEvidenceTests(unittest.TestCase):
    def test_current_maximum_does_not_inherit_historical_headroom(self):
        config=Configuration(8,1860465)
        self.assertTrue(config._native['headroom'])
        data=copy.deepcopy(load_evidence())
        for row in data['profiles']:
            if row['bits']==8 and row['ticks']==86:row['radio_a0']['visible']=False
        text=evidence_text(config,data)
        self.assertIn('prueba funcional de 120 s',text)
        self.assertIn('Dibujo visible: pendiente',text)
        self.assertIn('Holgura con RADIO/A0: sin medición',text)
        self.assertNotIn('Holgura ADC sin audio: medida',text)
    def test_headroom_is_adc_only_and_uses_exact_recorded_duration(self):
        text=evidence_text(Configuration(8,44101),load_evidence())
        self.assertIn('Holgura ADC sin audio: medida (15 s)',text)
        self.assertIn('prueba funcional de 30 s',text)
        self.assertNotIn('60 s',text)
    def test_geometry_cannot_borrow_another_profiles_evidence(self):
        config=Configuration(8,1860465);data=copy.deepcopy(load_evidence())
        for row in data['profiles']:
            if row['bits']==8 and row['ticks']==86:row['node_pairs']-=4
        text=evidence_text(config,data)
        self.assertIn('Sin medición registrada para esta geometría',text)
        self.assertNotIn('prueba funcional',text)
    def test_pair_mismatch_and_corrupt_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);receipt=base/'q_support/accepted/acceptance.json';receipt.parent.mkdir(parents=True)
            pair=load_evidence()['pair']
            receipt.write_text(json.dumps(dict(accepted=True,firmware=dict(sha256=pair['firmware_sha256']),relay=dict(sha256=pair['relay_sha256']))))
            evidence=base/'rate_evidence.json';data=load_evidence()
            evidence.write_text(json.dumps(data));self.assertIsNotNone(load_evidence(base))
            data['pair']['relay_sha256']='0'*64;evidence.write_text(json.dumps(data));self.assertIsNone(load_evidence(base))
            for invalid in ('{','[]','null',json.dumps(dict(schema=1,pair=pair,profiles=None))):
                evidence.write_text(invalid);self.assertIsNone(load_evidence(base))
    def test_rebuild_matches_shipped_provenance(self):
        from tools.build_rate_evidence_v18 import build
        self.assertEqual(build(),load_evidence())
        self.assertEqual(len(load_evidence()['profiles']),37)
