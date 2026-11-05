from contextlib import contextmanager
import hashlib
import importlib
import multiprocessing as mp
import os
from pathlib import Path
import signal
import tempfile
import unittest
import uuid


def hold_owner(version,serial,channel):
    try:
        owner=importlib.import_module(f'monitor.v{version}.board_owner').board_owner
        with owner(serial,'local interoperability fixture'):
            channel.send('held')
            if channel.recv()!='release':raise ValueError('Unexpected fixture command')
        channel.send('released')
    finally:channel.close()


class BoardOwnerTests(unittest.TestCase):
    def serial(self):return 'local-v18-lock-test-'+uuid.uuid4().hex

    def path(self,serial):
        key=hashlib.sha256(str(serial).encode()).hexdigest()[:20]
        return Path(tempfile.gettempdir())/f'serialmonitor-q-{os.getuid()}-{key}.lock'

    def owner(self,version):
        return importlib.import_module(f'monitor.v{version}.board_owner').board_owner

    @contextmanager
    def holder(self,version,serial):
        ctx=mp.get_context('spawn');channel,child=ctx.Pipe()
        process=ctx.Process(target=hold_owner,args=(version,serial,child))
        process.start();child.close()
        try:
            self.assertTrue(channel.poll(3),'Holder did not start')
            self.assertEqual(channel.recv(),'held')
            yield process,channel
        finally:
            if process.is_alive():
                channel.send('release');process.join(3)
            if process.is_alive():process.terminate();process.join(2)
            channel.close();process.close()

    def test_v17_and_v18_contend_in_both_directions_and_release_on_exit(self):
        for holder_version,contender_version in ((17,18),(18,17)):
            with self.subTest(holder=holder_version):
                serial=self.serial()
                with self.holder(holder_version,serial) as (process,channel):
                    with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
                        with self.owner(contender_version)(serial):self.fail('Second owner admitted')
                    channel.send('release');self.assertTrue(channel.poll(3))
                    self.assertEqual(channel.recv(),'released');process.join(3)
                    self.assertFalse(process.is_alive());self.assertEqual(process.exitcode,0)
                    with self.owner(contender_version)(serial):pass

    def test_distinct_serial_is_independent_while_other_version_holds_board(self):
        serial=self.serial()
        with self.holder(17,serial):
            with self.owner(18)(self.serial()):pass
            with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
                with self.owner(18)(serial):self.fail('Held board admitted')

    def test_error_releases_v18_lock_and_preserves_inode(self):
        serial=self.serial();path=self.path(serial)
        with self.assertRaisesRegex(ValueError,'fixture error'):
            with self.owner(18)(serial,'exception fixture'):
                inode=path.stat().st_ino
                self.assertIn(f'PID {os.getpid()}',path.read_text())
                raise ValueError('fixture error')
        self.assertTrue(path.exists());self.assertEqual(path.stat().st_ino,inode)
        with self.owner(17)(serial):self.assertEqual(path.stat().st_ino,inode)
        self.assertEqual(path.stat().st_ino,inode)

    def test_v18_sigterm_releases_kernel_lock_without_unlink(self):
        serial=self.serial();path=self.path(serial)
        with self.holder(18,serial) as (process,_):
            inode=path.stat().st_ino
            with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
                with self.owner(17)(serial):self.fail('Held board admitted')
            process.terminate();process.join(3)
            self.assertFalse(process.is_alive());self.assertEqual(process.exitcode,-signal.SIGTERM)
            with self.owner(17)(serial):self.assertEqual(path.stat().st_ino,inode)
            self.assertTrue(path.exists())
