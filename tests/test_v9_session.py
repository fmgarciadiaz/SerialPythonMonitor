"""Old Qt signals cannot mutate a new or disconnected V9 capture."""
import unittest
from types import SimpleNamespace
from monitor.historico.v9.app import SerialMonitorWindow


class SessionSignalTests(unittest.TestCase):
    def test_only_current_worker_can_deliver_data_status_or_errors(self):
        old, current = object(), object()
        window = SimpleNamespace(serial_worker=current)
        received = []
        dispatch = SerialMonitorWindow._from_worker
        dispatch(window, old, received.append, 'old batch')
        dispatch(window, old, received.append, 'old error')
        dispatch(window, current, received.append, 'new batch')
        self.assertEqual(received, ['new batch'])

    def test_queued_signal_after_disconnect_is_discarded(self):
        window = SimpleNamespace(serial_worker=None)
        received = []
        SerialMonitorWindow._from_worker(window, object(), received.append, 'late confirmation')
        self.assertEqual(received, [])
