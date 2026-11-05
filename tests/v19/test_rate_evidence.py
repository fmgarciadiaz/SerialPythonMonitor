import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from monitor.v19.rate_evidence import load_evidence, evidence_text
from monitor.v19.receiver.unoq_acquisition import Configuration


class RateEvidenceTests(unittest.TestCase):
    def test_v19_profile_uses_its_own_physical_evidence(self):
        config = Configuration(8, 1860465)
        text = evidence_text(config, load_evidence())
        self.assertIn('RADIO/A0: prueba funcional de 120 s.', text)
        self.assertIn('Dibujo visible: comprobado en esa prueba.', text)
        self.assertIn('Holgura con RADIO/A0: sin medición registrada', text)
        self.assertNotIn('no acredita esta pareja V19', text)
        self.assertNotIn('Holgura ADC sin audio: medida', text)

    def test_evidence_is_scoped_to_exact_geometry(self):
        config = Configuration(8, 1860465)
        evidence = dict(schema=1, pair=dict(firmware_sha256='a' * 64, relay_sha256='b' * 64),
                        profiles=[dict(bits=8, channels=1, ticks=86, node_pairs=3488,
                                       radio_a0=dict(seconds=120, visible=True))])
        text = evidence_text(config, evidence)
        self.assertIn('RADIO/A0: prueba funcional de 120 s', text)
        self.assertIn('Dibujo visible: comprobado en esa prueba.', text)
        wrong_geometry = dict(evidence, profiles=[dict(evidence['profiles'][0], node_pairs=3492)])
        self.assertIn('Sin medición registrada para esta geometría', evidence_text(config, wrong_geometry))

    def test_pair_mismatch_and_corrupt_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            accepted = base / 'q_support/accepted/acceptance.json'
            accepted.parent.mkdir(parents=True)
            pair = dict(firmware_sha256='a' * 64, relay_sha256='b' * 64)
            accepted.write_text(json.dumps(dict(accepted=True,
                firmware=dict(sha256=pair['firmware_sha256']),
                relay=dict(sha256=pair['relay_sha256']))))
            data = dict(schema=1, pair=pair,
                        profiles=[dict(bits=8, channels=1, ticks=86, node_pairs=3488,
                                       radio_a0=dict(seconds=120, visible=True))])
            evidence = base / 'rate_evidence.json'
            evidence.write_text(json.dumps(data))
            self.assertIsNotNone(load_evidence(base))
            data['pair']['relay_sha256'] = '0' * 64
            evidence.write_text(json.dumps(data))
            self.assertIsNone(load_evidence(base))
            for invalid in ('{', '[]', 'null', json.dumps(dict(schema=1, pair=pair, profiles=None))):
                evidence.write_text(invalid)
                self.assertIsNone(load_evidence(base))


if __name__ == '__main__':
    unittest.main()
