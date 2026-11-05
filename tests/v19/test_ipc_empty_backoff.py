import multiprocessing.queues
import multiprocessing as mp
import queue
import time
from unittest import TestCase
from unittest.mock import Mock, patch
from tools.ipc_empty_backoff_v19 import empty_backoff


class EmptyBackoffTests(TestCase):
    def test_real_queue_preserves_fifo_across_empty_to_ready_transition(self):
        source=mp.get_context('spawn').Queue()
        received=[]
        try:
            with empty_backoff(500):
                with self.assertRaises(queue.Empty):source.get_nowait()
                for value in range(200):source.put(value)
                deadline=time.monotonic()+2
                while len(received)<200 and time.monotonic()<deadline:
                    try:received.append(source.get_nowait())
                    except queue.Empty:time.sleep(.0001)
            self.assertEqual(received,list(range(200)))
        finally:
            source.close();source.join_thread()

    def test_defers_only_empty_nonblocking_poll_without_consuming_message(self):
        cls = multiprocessing.queues.Queue
        source = object()
        original = Mock(side_effect=[queue.Empty, 'message', 'blocking'])
        with patch.object(cls, 'get', original), patch('tools.ipc_empty_backoff_v19.monotonic', return_value=10.) as clock:
            with empty_backoff(500) as stats:
                with self.assertRaises(queue.Empty): cls.get(source, False)
                with self.assertRaises(queue.Empty): cls.get(source, False)
                self.assertEqual(original.call_count, 1)
                clock.return_value = 10.001
                self.assertEqual(cls.get(source, False), 'message')
                self.assertEqual(cls.get(source, True, .2), 'blocking')
            self.assertIs(cls.get, original)
            self.assertEqual(stats['deferred_polls'], 1)
            original.assert_called_with(source, True, .2)

    def test_control_is_noop_and_exception_restores_method(self):
        cls = multiprocessing.queues.Queue
        original = cls.get
        with empty_backoff(0): self.assertIs(cls.get, original)
        with self.assertRaises(RuntimeError):
            with empty_backoff(500): raise RuntimeError('test')
        self.assertIs(cls.get, original)
        with self.assertRaises(ValueError):
            with empty_backoff(1000): pass
