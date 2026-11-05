from pathlib import Path
from types import SimpleNamespace
import json,subprocess,sys,tarfile,tempfile,unittest
from tools.v20_trial_cleanup import finish_steps
from tools.v20_memory_fix import cache_inventory

class CleanupTests(unittest.TestCase):
    def test_each_cleanup_failure_still_reaches_all_remaining_steps_and_rollback(self):
        for position in range(4):
            calls=[];report={}
            def operation(index):
                calls.append(index)
                if index==position:raise OSError('injected cleanup failure')
            def restore(errors):calls.append('undo');self.assertEqual(len(errors),1)
            with self.assertRaises(RuntimeError):finish_steps([(str(i),lambda i=i:operation(i)) for i in range(4)],restore,report,lambda:None)
            self.assertEqual(calls,[0,1,2,3,'undo']);self.assertFalse(report['trial_cleanup_active'])
    def test_cancellation_and_restore_failure_are_recorded_without_skipping_stop(self):
        calls=[];report={}
        def interrupted():raise KeyboardInterrupt()
        def restore(errors):calls.append('rollback-attempt');raise RuntimeError('quiescence unconfirmed')
        with self.assertRaises(RuntimeError):finish_steps([('log',interrupted),('stop',lambda:calls.append('stop'))],restore,report,lambda:None)
        self.assertEqual(calls,['stop','rollback-attempt']);self.assertEqual([e['step'] for e in report['trial_cleanup_errors']],['log','restore_v20'])
    def test_no_cleanup_errors_preserves_success(self):
        report={};calls=[]
        finish_steps([('stop',lambda:calls.append('stop'))],lambda errors:calls.append(tuple(errors)),report,lambda:None)
        self.assertEqual(calls,['stop',()]);self.assertEqual(report['trial_cleanup_errors'],[])

class CacheTests(unittest.TestCase):
    def test_archive_inventory_matches_all_files_symlinks_and_empty_directories(self):
        class Board:
            def shell(self,*args,capture=False):
                result=subprocess.run([sys.executable,*args[1:]],check=True,capture_output=True,text=True)
                return SimpleNamespace(stdout=result.stdout)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cache=root/'.cache/sketch';cache.mkdir(parents=True)
            for name in ('sketch.ino.bin','sketch.ino.elf','sketch.ino_debug.elf','options.json'):(cache/name).write_text(name)
            (cache/'empty').mkdir();(cache/'alias').symlink_to('sketch.ino.bin')
            archive=root/'saved.tar'
            with tarfile.open(archive,'w') as stream:stream.add(cache,arcname='.cache/sketch')
            before=cache_inventory(Board(),'archive',str(archive))
            self.assertEqual(before,cache_inventory(Board(),'directory',str(root)))
            (cache/'sketch.ino_debug.elf').write_text('changed debug, BIN identical')
            self.assertNotEqual(before,cache_inventory(Board(),'directory',str(root)))

class OwnershipTests(unittest.TestCase):
    def test_app_absence_requires_successful_inventory(self):
        from unittest.mock import Mock
        from tools.v20_trial_cleanup import app_is_stopped
        backend=Mock();backend._output.return_value=''
        self.assertTrue(app_is_stopped(backend,'app'));backend._inspect.assert_not_called()
        backend._output.side_effect=RuntimeError('device unavailable')
        with self.assertRaises(RuntimeError):app_is_stopped(backend,'app')
    def test_foreign_relay_rejected_and_owned_stop_can_fall_back_to_kill(self):
        from unittest.mock import Mock
        from tools.v20_trial_cleanup import owned_relay,stop_relay_id
        backend=Mock();board=Mock();backend._output.return_value='relay\n'
        backend._inspect.return_value={'Id':'owned','Config':{'Labels':{'arduscopio.v20-trial':'foreign'}},'State':{'Running':False}}
        with self.assertRaises(RuntimeError):owned_relay(backend,'relay','token')
        board.shell.assert_not_called()
        backend._inspect.return_value['Config']['Labels']['arduscopio.v20-trial']='token'
        self.assertEqual(owned_relay(backend,'relay','token'),'owned')
        board.shell.side_effect=[RuntimeError('stop timed out'),None];report={}
        stop_relay_id(backend,board,'owned',report)
        self.assertEqual([call.args for call in board.shell.call_args_list],[('docker','stop','owned'),('docker','kill','owned')])
        self.assertEqual(len(report['cleanup_fallbacks']),1)
    def test_unconfirmed_private_writer_blocks_undo_and_v19_restart(self):
        from tools.build_relay_candidate_v19 import execute_build
        from tools.v20_trial_cleanup import confirm_quiescence
        from tests.v19.test_q_update_transaction import Backend
        backend=Backend();report={};capture=backend.capture;identity=dict(firmware_sha256='b'*64,relay_sha256='c'*64)
        backend.capture=lambda:dict(capture(),identity=identity)
        calls=[]
        def builder(*args):
            confirm_quiescence(backend,dict(app=True,relay=False,compiler=True))
            calls.append('undo')
        execute_build(backend,dict(candidate_identity=identity),Path('.'),Path('.'),report,lambda:None,builder)
        self.assertFalse(report['ok']);self.assertFalse(report['restoration']['ok'])
        self.assertNotIn('start_original_app',backend.calls);self.assertNotIn('undo',calls)
    def test_missing_owned_directories_are_tolerated_but_permission_errors_propagate(self):
        from unittest.mock import patch
        from tools.v20_memory_fix import _REMOVE_OWNED_DIRS
        with patch('sys.argv',['cleanup','/owned']),patch('shutil.rmtree',side_effect=FileNotFoundError):exec(_REMOVE_OWNED_DIRS,{})
        with patch('sys.argv',['cleanup','/owned']),patch('shutil.rmtree',side_effect=PermissionError):
            with self.assertRaises(PermissionError):exec(_REMOVE_OWNED_DIRS,{})
