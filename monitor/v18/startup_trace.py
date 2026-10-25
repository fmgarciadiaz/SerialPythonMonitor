"""Opt-in, in-memory milestones for acquisition startup (no sample logging)."""
from collections import deque
from threading import Lock
import os
import time


class StartupTrace:
    def __init__(self, enabled=None, clock=None):
        self.enabled = os.environ.get('SPM_STARTUP_TRACE') == '1' if enabled is None else enabled
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._requests = deque(maxlen=4)
        self._generation = 0

    def begin(self, kind, config):
        if not self.enabled:
            return None
        with self._lock:
            self._generation += 1
            self._requests.append(dict(generation=self._generation, kind=kind,
                bits=config.bits, rate=config.rate, events=[], seen=set()))
            self._record(self._requests[-1], 'request_begin', {})
            return self._generation

    def _record(self, request, event, details):
        if len(request['events']) >= 128:
            return
        request['events'].append(dict(event=event, monotonic=self._clock(), **details))
        request['seen'].add(event)

    def record(self, generation, event, *, once=False, **details):
        if not self.enabled or generation is None:
            return
        with self._lock:
            request = next((r for r in self._requests if r['generation'] == generation), None)
            if request is not None and (not once or event not in request['seen']):
                self._record(request, event, details)

    def snapshot(self):
        with self._lock:
            return [dict(generation=r['generation'], kind=r['kind'], bits=r['bits'],
                rate=r['rate'], events=[dict(e) for e in r['events']]) for r in self._requests]
