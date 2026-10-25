import json
from pathlib import Path
import tempfile
import unittest
from experimentos.fs_max_v18.probe_journal import APP,NAME,ProbeJournal,adoption_decision,source_manifest,verified_identity
class JournalTests(unittest.TestCase):
    def test_adoption_exact_stopped(self):
        apps=[{'name':NAME,'path':APP,'running':False}];sources={'app.yaml':'a'}
        self.assertEqual(adoption_decision(apps,[],sources,sources),'adopt')
        self.assertEqual(adoption_decision([],[],sources,{}),'create')
        with self.assertRaises(ValueError):adoption_decision(apps,[],sources,{'app.yaml':'b'})
        with self.assertRaises(ValueError):adoption_decision([{'name':NAME}],[],sources,sources)
        with self.assertRaises(ValueError):adoption_decision(apps,[{'Name':'/scope-v18-rate-probe-main-1','State':{'Running':True}}],sources,sources)
        with self.assertRaises(ValueError):adoption_decision(apps,[],sources,dict(sources,extra='c'))
    def test_spi40_variant_has_distinct_identity_and_exact_source_check(self):
        path=APP+'-spi40';name='Scope V18 Rate Probe SPI40'
        app={'name':name,'path':path,'running':False};sources={'sketch.ino':'hash'}
        self.assertEqual(adoption_decision([app],[],sources,sources,remote_app=path),'adopt')
        with self.assertRaises(ValueError):
            adoption_decision([dict(app,path=APP)],[],sources,sources,remote_app=path)
        with self.assertRaises(ValueError):
            adoption_decision([app],[],sources,{'sketch.ino':'different'},remote_app=path)
        with self.assertRaises(ValueError):
            adoption_decision([],[],sources,sources,remote_app=APP+'-unknown')

    def test_write_ahead_and_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';report={};journal=ProbeJournal(path,report)
            journal.capture(saved_name='original-saved',identity={'firmware':'original'})
            def action():
                self.assertEqual(json.loads(path.read_text())['journal'][-1]['state'],'intent')
                raise RuntimeError('boundary')
            with self.assertRaises(RuntimeError):journal.mutate('stop_relay',action)
            self.assertEqual(json.loads(path.read_text())['journal'][-1]['state'],'failed')
            journal.mutate('start_original',lambda:42)
            self.assertEqual(json.loads(path.read_text())['journal'][-1]['state'],'completed')
    def test_identity_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'app.yaml').write_text('name: probe')
            (root/'.cache').mkdir();(root/'.cache'/'binary').write_text('ignored')
            self.assertEqual(list(source_manifest(root)),['app.yaml'])
        self.assertTrue(verified_identity('a'*64,'b'*64,{'firmware_sha256':'a'*64,'relay_sha256':'b'*64}))
        self.assertFalse(verified_identity('a'*64,'b'*64,{'firmware_sha256':'b'*64,'relay_sha256':'b'*64}))
if __name__=='__main__':unittest.main()
