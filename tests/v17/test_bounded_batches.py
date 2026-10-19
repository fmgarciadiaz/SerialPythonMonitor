import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from monitor.v17.app import OutputWorker,SerialMonitorWindow
from monitor.v17.receiver.unoq_switch import Mode

class BatchTests(unittest.TestCase):
    def test_limit_ack_and_no_growth_after_overload(self):
        worker=OutputWorker('test',Mode.SPI)
        for _ in range(8):worker.publish_batch(SimpleNamespace())
        with self.assertRaises(RuntimeError):worker.publish_batch(SimpleNamespace())
        self.assertEqual(worker.pending_batches,8)
        self.assertEqual(worker.pending_batches_peak,8)
        worker.batch_consumed();worker.publish_batch(SimpleNamespace())
        self.assertEqual(worker.pending_batches,8)

    def test_ack_even_if_old_worker_or_processing_fails(self):
        worker=Mock();owner=SimpleNamespace(serial_worker=worker,handle_batch=Mock(),_from_worker=Mock(side_effect=ValueError('test')))
        with self.assertRaises(ValueError):SerialMonitorWindow._deliver_worker_batch(owner,worker,object())
        worker.batch_consumed.assert_called_once()
