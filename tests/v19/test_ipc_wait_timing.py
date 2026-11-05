import multiprocessing as mp
import multiprocessing.queues
import queue
import unittest
from unittest.mock import patch

from tools.ipc_wait_timing_v19 import QueueWaitTiming


class QueueWaitTests(unittest.TestCase):
    def test_preserves_data_exceptions_and_restores_method(self):
        q = mp.get_context('spawn').Queue()
        original = multiprocessing.queues.Queue.get
        tracker = QueueWaitTiming()
        try:
            with tracker.installed():
                with self.assertRaises(queue.Empty):
                    q.get_nowait()
                q.put(('opaque', 17))
                self.assertEqual(q.get(timeout=2), ('opaque', 17))
            self.assertIs(multiprocessing.queues.Queue.get, original)
            self.assertEqual(tracker.report()['queues'][0]['calls'], 2)
            self.assertNotIn('opaque', str(tracker.report()))
            with self.assertRaisesRegex(RuntimeError, 'test'):
                with tracker.installed():
                    raise RuntimeError('test')
            self.assertIs(multiprocessing.queues.Queue.get, original)
        finally:
            q.close()
            q.join_thread()

    def test_bounded_slow_ring_with_active_context(self):
        tracker = QueueWaitTiming(lambda: ['tick'])
        q = mp.get_context('spawn').Queue()
        try:
            with tracker.installed(), patch('tools.ipc_wait_timing_v19._wall',
                    side_effect=[v for i in range(40) for v in (float(i), i+.025)]):
                for _ in range(40):
                    with self.assertRaises(queue.Empty):
                        q.get_nowait()
            report = tracker.report()
            self.assertEqual(len(report['slow']), 32)
            self.assertEqual(report['queues'][0]['calls'], 40)
            self.assertEqual(report['slow'][0]['active'], ['tick'])
        finally:
            q.close()
            q.join_thread()
