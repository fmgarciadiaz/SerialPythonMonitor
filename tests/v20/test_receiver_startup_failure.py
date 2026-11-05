"""A failed spawn must not leave the connection pending forever. No Q access."""
import multiprocessing as mp
import os
import time
import unittest
from monitor.v20.io.receiver_process import ReceiverProcess
from monitor.v20.receiver.unoq_acquisition import Configuration


def crash_before_receiver():
    os._exit(7)


class StartupFailureTests(unittest.TestCase):
    def test_child_exit_before_terminal_message_is_reported(self):
        owner=ReceiverProcess('fake',0,Configuration())
        owner.process=mp.get_context('spawn').Process(target=crash_before_receiver)
        try:
            owner.start()
            deadline=time.monotonic()+30
            result=None
            while result is None and time.monotonic()<deadline:
                result=owner.poll_terminal()
                time.sleep(.01)
            self.assertIsNotNone(result)
            self.assertFalse(result['ok'])
            self.assertTrue(result['error'])
            self.assertIsNone(owner.poll_terminal())
        finally:
            owner.close(timeout=1)
            owner.terminal.close()


if __name__=='__main__':unittest.main()
