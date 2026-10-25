"""Isolated refresh policy. No Qt, audio credits or sample ownership."""
from collections import Counter, deque
from threading import Lock


class AdaptiveRefresh:
    def __init__(self):
        self.lock = Lock()
        self.session = None
        self.reduced = False
        self.last_pressure = None
        self.ack_at = None
        self.ack_seconds = 0.
        self.reduced_seconds = 0.
        self.entered_at = None
        self.reasons = Counter()
        self.transitions = deque(maxlen=32)
        self.entries = self.exits = 0

    def _leave(self, now, reason):
        if self.reduced:
            self.reduced_seconds += max(0., now-self.entered_at)
            self.exits += 1
            self.transitions.append(dict(at=now, state='normal', reason=reason))
        self.reduced = False
        self.entered_at = None
        self.last_pressure = None

    def _session(self, session, now):
        if session is not self.session:
            self._leave(now, 'session')
            self.session = session
            self.ack_at = None
            self.ack_seconds = 0.

    def observe_ack(self, session, seconds, now):
        with self.lock:
            # A late ACK from a detached source must not switch ownership back.
            if session is self.session:
                self.ack_at, self.ack_seconds = now, seconds

    def interval(self, now, session, pending_gui=0, pending_dsp=0, eligible=True):
        with self.lock:
            self._session(session, now)
            if session is None or not eligible:
                self._leave(now, 'inactive' if session is None else 'bypass')
                return 0.
            reason = ('delivery' if pending_gui >= 3 or pending_dsp >= 3 else
                      'ack' if self.ack_at is not None and 0 <= now-self.ack_at <= .5
                      and self.ack_seconds >= .04 else None)
            if reason:
                self.reasons[reason] += 1
                self.last_pressure = now
                if not self.reduced:
                    self.reduced, self.entered_at = True, now
                    self.entries += 1
                    self.transitions.append(dict(at=now,state='reduced',reason=reason))
            elif self.reduced and now-self.last_pressure >= 3.:
                self._leave(now, 'quiet')
            return .125 if self.reduced else 0.

    def snapshot(self, now):
        with self.lock:
            duration = self.reduced_seconds
            if self.reduced:
                duration += max(0., now-self.entered_at)
            return dict(entries=self.entries, exits=self.exits, reduced_seconds=duration,
                        reduced=self.reduced, reasons=dict(self.reasons),
                        transitions=list(self.transitions))
