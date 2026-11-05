"""Private experiment: briefly defer rechecking an input queue found empty."""
from contextlib import contextmanager
import multiprocessing.queues
import queue
from time import monotonic

ENV = 'ARDUSCOPIO_PRIVATE_IPC_EMPTY_BACKOFF_US'


@contextmanager
def empty_backoff(microseconds):
    if microseconds not in (0, 500):
        raise ValueError('Only control/500 us private backoff supported')
    result = dict(microseconds=microseconds, deferred_polls=0, real_polls=0)
    if not microseconds:
        yield result
        return
    cls = multiprocessing.queues.Queue
    original = cls.get
    deadlines = {}

    def get(source, block=True, timeout=None):
        # Blocking reads are untouched. Cancellation uses its own Event.
        key = id(source)
        if not block and monotonic() < deadlines.get(key, 0):
            result['deferred_polls'] += 1
            raise queue.Empty
        result['real_polls'] += 1
        try:
            return original(source, block, timeout)
        except queue.Empty:
            if not block and (key in deadlines or len(deadlines) < 16):
                deadlines[key] = monotonic() + microseconds / 1e6
            raise

    cls.get = get
    try:
        yield result
    finally:
        cls.get = original
