import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.probe_relay_transport_v19 import ROOT,checked_artifact
from monitor.v19.relay_identity import relay_sources


class PrivateArtifactTests(unittest.TestCase):
    def test_separate_source_directory_is_hash_bound_and_cannot_escape(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnosticos/resultados_v19') as folder:
            root=Path(folder);sources=root/'sources';sources.mkdir()
            for name in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h'):
                (sources/name).write_text('/* private fixture */')
            binary=root/'relay.bin';binary.write_bytes(b'private test artifact')
            artifact=dict(path=str(binary),sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                source_directory=str(sources),compiled_with_pair_stopped=True,
                sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in relay_sources(sources)})
            report=root/'report.json'
            def save():report.write_text(json.dumps(dict(ok=True,restoration=dict(ok=True),artifact=artifact)))
            save();self.assertEqual(checked_artifact(report),artifact)
            (sources/'base_verifier.c').write_text('changed')
            with self.assertRaisesRegex(ValueError,'sources changed'):checked_artifact(report)
            artifact['source_directory']='/tmp';save()
            with self.assertRaisesRegex(ValueError,'Private diagnostic sources'):checked_artifact(report)
