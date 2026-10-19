import unittest
from contextlib import contextmanager
from unittest.mock import patch
from monitor.v17.board_owner import board_owner
from monitor.v17.receiver.unoq_autoload import connect_scope

class BoardOwnerTests(unittest.TestCase):
    def test_conflict_blocks_autostart_before_touching_q(self):
        with board_owner('unit-test-q-ownership','campaña de prueba'):
            with patch('monitor.v17.receiver.unoq_autoload.ensure_scope') as start:
                with patch('monitor.v17.receiver.unoq_autoload.Connection') as connection:
                    with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
                        with connect_scope('unit-test-q-ownership'):
                            self.fail('Second owner admitted')
                    start.assert_not_called()
                    connection.assert_not_called()

    def test_release_after_error_and_independent_boards(self):
        with self.assertRaisesRegex(ValueError,'test failure'):
            with board_owner('unit-test-q-release'):
                with board_owner('unit-test-q-independent'):
                    raise ValueError('test failure')
        with board_owner('unit-test-q-release'):
            pass

    def test_monitor_keeps_ownership_through_connected_session(self):
        events=[]
        @contextmanager
        def connected(*args):
            events.append('open')
            try:yield 'connection'
            finally:events.append('close')
        with patch('monitor.v17.receiver.unoq_autoload._connect_scope_unlocked',connected):
            with connect_scope('unit-test-q-live') as connection:
                self.assertEqual(connection,'connection')
                with self.assertRaisesRegex(RuntimeError,'Q ocupado'):
                    with board_owner('unit-test-q-live','campaign'):pass
        self.assertEqual(events,['open','close'])
        with board_owner('unit-test-q-live'):pass

if __name__=='__main__':unittest.main()
