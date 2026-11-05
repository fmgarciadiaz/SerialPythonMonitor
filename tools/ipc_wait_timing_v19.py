"""Private bounded timing of Queue.get; never retain or inspect messages."""
from collections import deque
from contextlib import contextmanager
import multiprocessing.queues
import sys
import time

_wall = time.monotonic


class QueueWaitTiming:
    def __init__(self, active=lambda: ()):
        self.active = active
        self.groups = {}
        self.slow = deque(maxlen=32)
        self.omitted = 0

    @contextmanager
    def installed(self):
        cls = multiprocessing.queues.Queue
        original = cls.get

        def measured(queue, *args, **kwargs):
            # Preserve blocking/timeout arguments and all return/exception paths.
            wall = _wall()
            cpu = time.thread_time()
            try:
                return original(queue, *args, **kwargs)
            finally:
                elapsed_cpu = time.thread_time() - cpu
                end = _wall()
                key = id(queue)
                if key not in self.groups and len(self.groups) < 16:
                    caller = sys._getframe(1)
                    while caller.f_back is not None and caller.f_code.co_name in ('get', 'get_nowait', 'measured'):
                        caller = caller.f_back
                    self.groups[key] = dict(queue=f'q{len(self.groups)+1}', calls=0,
                        first_callsite=f'{caller.f_code.co_name}:{caller.f_lineno}',
                        max_ms=0., max_cpu_ms=0., total_ms=0., total_cpu_ms=0.)
                group = self.groups.get(key)
                if group is None:
                    self.omitted += 1
                else:
                    ms = (end-wall)*1000
                    cpu_ms = elapsed_cpu*1000
                    group['calls'] += 1
                    group['total_ms'] += ms
                    group['total_cpu_ms'] += cpu_ms
                    group['max_ms'] = max(group['max_ms'], ms)
                    group['max_cpu_ms'] = max(group['max_cpu_ms'], cpu_ms)
                    if ms >= 20:
                        self.slow.append(dict(queue=group['queue'], start=wall, end=end,
                            wall_ms=ms, cpu_ms=cpu_ms, active=list(self.active())))

        cls.get = measured
        try:
            yield self
        finally:
            cls.get = original

    def report(self):
        return dict(queues=list(self.groups.values()), slow=list(self.slow),
            omitted_calls=self.omitted,
            note='Queue.get wall/thread-CPU includes locks, poll, receive and deserialization. Anonymous queue ids; no message data retained. A long call does not alone identify the blocking operation or scheduler.')
