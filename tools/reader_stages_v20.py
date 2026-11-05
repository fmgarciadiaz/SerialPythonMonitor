"""Private capture of V20's existing opt-in stage timers; no protocol changes."""
from collections import deque
from contextlib import contextmanager
from monitor.v19.q_support.prepare import atomic_report

@contextmanager
def capture(path):
    from monitor.v20.receiver import unoq_config_receiver as core
    if not core._child_stage_timing_enabled:raise RuntimeError('V20 child stage timers must be explicitly enabled')
    cls=core._ChildStageTiming;original=cls._observe;instances=[];slow=deque(maxlen=128)
    def observed(tracker,stage,start,end,cpu_seconds=None,**details):
        if not any(item is tracker for item in instances) and len(instances)<8:instances.append(tracker)
        original(tracker,stage,start,end,cpu_seconds,**details)
        if end-start>=.05:
            slow.append(dict(stage=stage,start=start,end=end,wall_ms=(end-start)*1000,
                cpu_ms=cpu_seconds*1000 if cpu_seconds is not None else None,details=details))
    cls._observe=observed
    try:yield
    finally:
        cls._observe=original
        atomic_report(path,dict(slow=list(slow),trackers=[tracker.snapshot(detail=True) for tracker in instances],
            note='Existing V20 wall/thread-CPU timers, bounded slow ring >=50ms; observer overhead changes timing. No RF arrays.'))
