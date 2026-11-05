import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from monitor.v20.memory_contract import load_contract
from tools import v20_storage_fix as fix

class PatchTests(unittest.TestCase):
    def test_only_two_files_and_restored_matching_memory_baseline_are_allowed(self):
        digest=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();folder=root/'arduino/v20/oscilloscope';folder.mkdir(parents=True)
            old={}
            for name in ('sketch/acquisition.h','sketch/acquisition_storage.h','sketch/other.h'):
                p=folder/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'new' if name!='sketch/other.h' else b'old');old[name]=digest(b'old')
            proof=root/'diagnosticos/resultados_v20/baseline/report.json';proof.parent.mkdir(parents=True)
            baseline=dict(private=True,promoted=False,ok=True,restoration={'ok':True},memory_contract=load_contract(),v20_sources=old)
            proof.write_text(json.dumps(baseline))
            with patch.object(fix,'ROOT',root):
                _,before,after=fix.validate(proof);self.assertEqual(set(before),set(after))
                (folder/'sketch/other.h').write_bytes(b'extra')
                with self.assertRaises(ValueError):fix.validate(proof)
                (folder/'sketch/other.h').write_bytes(b'old')
                for change in ({'ok':False},{'restoration':{'ok':False}},{'memory_contract':{}},{'promoted':True}):
                    proof.write_text(json.dumps(dict(baseline,**change)))
                    with self.assertRaises(ValueError):fix.validate(proof)
