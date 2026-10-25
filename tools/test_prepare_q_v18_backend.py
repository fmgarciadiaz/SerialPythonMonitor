"""Offline failure cases for the production adapter and exact archive core."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimentos.fs_max_v18 import rehearsal_archive as archive
from tools import prepare_q_v18 as contract
from tools.prepare_q_v18_backend import (
    APP_CONTAINER, CONTAINER, HELPER, ProductionBackend, _relay_policy_equal,
)


RECEIPT = (contract.ROOT / 'monitor/v18/q_support/accepted/acceptance.json')


class FakeBoard:
    serial = '1060031107'
    def __init__(self):
        self.commands = []
    def run(self, *args, capture=False):
        self.commands.append(args)
    def shell(self, *args, capture=False):
        self.commands.append(args)


class BackendTests(unittest.TestCase):
    def test_real_receipt_preflight_checks_proof_without_contacting_board(self):
        accepted = contract.load_acceptance(RECEIPT)
        board = FakeBoard()
        backend = ProductionBackend(accepted, board=board)
        proof = json.loads(Path(accepted['artifacts']['prebuild_proof']['path']).read_text())
        def output(*args):
            if args[:2] == ('docker', 'ps'):
                return APP_CONTAINER + '\n' + CONTAINER
            if args == ('arduino-app-cli', 'version'):
                return proof['launcher']['version'].strip()
            if args == ('arduino-app-cli','app','list','--format','json'):
                return json.dumps({'apps':[{'name':'Scope V18','status':'running'}]})
            raise AssertionError(args)
        backend._output = output
        backend._hash = lambda path: (proof['launcher']['sha256'] if path == proof['launcher']['path']
                                      else contract.sha256(HELPER))
        backend._no_reader = lambda: True
        result = backend.preflight(accepted)
        self.assertTrue(result['production_backend_qualified'])
        self.assertEqual([command[0] for command in board.commands], ['get-state', 'push'])
        wrong = dict(accepted, candidate_identity=dict(accepted['candidate_identity'],
                                                       firmware_sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'rehearsal tested another binary pair'):
            backend.preflight(wrong)

    def test_partial_cache_rename_can_restore_exact_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root, backup = Path(folder) / 'scope-v18', Path(folder) / 'backup'
            (root / 'sketch').mkdir(parents=True)
            (root / '.cache/sketch').mkdir(parents=True)
            (root / 'app.yaml').write_text('name: Scope V18\n')
            (root / 'sketch/sketch.ino').write_text('original')
            (root / '.cache/sketch/sketch.ino.bin').write_bytes(b'old bin')
            (root / '.cache/sketch/sketch.ino.elf').write_bytes(b'old elf')
            proof = archive.backup(root, backup)
            for name in archive.PRODUCTION_ADDED:
                (root / name).write_text('new')
            (root / '.cache').rename(backup / 'quarantined_original_cache')
            with patch.object(archive, 'PRODUCTION_APP', str(root)):
                restored = archive.restore(root, backup, proof['manifest_sha256'])
            self.assertTrue(restored['sources_exact'] and restored['cache_exact'])
            self.assertEqual((root / '.cache/sketch/sketch.ino.bin').read_bytes(), b'old bin')
            self.assertFalse(any((root / name).exists() for name in archive.PRODUCTION_ADDED))

    def test_unowned_added_file_blocks_restore_before_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root, backup = Path(folder) / 'scope-v18', Path(folder) / 'backup'
            (root / '.cache').mkdir(parents=True)
            (root / 'app.yaml').write_text('name: Scope V18\n')
            proof = archive.backup(root, backup)
            (root / 'unexpected.h').write_text('unowned')
            with patch.object(archive, 'PRODUCTION_APP', str(root)):
                with self.assertRaisesRegex(ValueError, 'Unowned new source'):
                    archive.restore(root, backup, proof['manifest_sha256'])
            self.assertTrue((root / 'unexpected.h').is_file())

    def test_rollback_recognizes_original_and_partially_created_relay(self):
        accepted = {'receipt_path': str(RECEIPT)}
        board = FakeBoard()
        backend = ProductionBackend(accepted, board=board)
        backend.original_relay_id = 'old'
        backend._output = lambda *args: CONTAINER if args[:2] == ('docker', 'ps') else ''
        backend._inspect = lambda name: {'Id': 'old', 'State': {'Running': True}}
        backend.stop_new_relay({}, None)
        self.assertEqual(board.commands[-1], ('docker', 'stop', '--time', '3', 'old'))
        board.commands.clear()
        backend._inspect = lambda name: {'Id': 'new', 'State': {'Running': True}}
        backend._relay_bin = lambda info: backend.new_relay + '/unoq_stream'
        backend.stop_new_relay({}, None)
        self.assertEqual(board.commands[-1], ('docker', 'rm', '-f', 'new'))

    def test_relay_policy_requires_same_mount_and_runtime_controls(self):
        original = dict(Image='image', HostConfig=dict(NetworkMode='host', CapAdd=['SYS_NICE']),
                        Config=dict(Env=['SCOPE_EXPERIMENT_RT=1'], Entrypoint=['/work/unoq_stream']),
                        Mounts=[dict(Source='/old/relay', Destination='/work/unoq_stream')])
        new = json.loads(json.dumps(original))
        new['Mounts'][0]['Source'] = '/new/relay'
        self.assertTrue(_relay_policy_equal(original, new, '/old/relay', '/new/relay'))
        new['HostConfig']['NetworkMode'] = 'bridge'
        self.assertFalse(_relay_policy_equal(original, new, '/old/relay', '/new/relay'))


if __name__ == '__main__':
    unittest.main()
