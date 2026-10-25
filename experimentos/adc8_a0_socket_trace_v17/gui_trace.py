"""Bounded GUI callback CPU/wall observations during active A0 playback."""
from collections import deque
import time


class GuiTrace:
    def __init__(self):
        self.stages = {}
        self.recent_slow = deque(maxlen=128)
        self.window = None

    def call(self, name, function, owner, *args, **kwargs):
        window = getattr(owner, 'owner', owner)
        self.window = window
        if not (getattr(window, 'is_running', False) and getattr(window, '_wav_active', False)):
            return function(owner, *args, **kwargs)
        start = time.monotonic()
        cpu = time.thread_time()
        try:
            return function(owner, *args, **kwargs)
        finally:
            thread_cpu = time.thread_time()-cpu
            end = time.monotonic()
            wall = end-start
            stage = self.stages.setdefault(name, dict(count=0, wall_seconds=0., thread_cpu_seconds=0., top=[]))
            stage['count'] += 1
            stage['wall_seconds'] += wall
            stage['thread_cpu_seconds'] += thread_cpu
            if wall >= .02:
                self.recent_slow.append(dict(stage=name,start=start,end=end,wall_seconds=wall,thread_cpu_seconds=thread_cpu))
            top = stage['top']
            if len(top) < 8 or wall > top[-1]['wall_seconds']:
                top.append(dict(start=start,end=end,wall_seconds=wall,thread_cpu_seconds=thread_cpu))
                top.sort(key=lambda x:x['wall_seconds'],reverse=True)
                del top[8:]

    def snapshot(self):
        return dict(stages=self.stages, recent_slow=list(self.recent_slow), limitation=
                    'Active A0 callbacks only; render callback excludes later asynchronous Qt paint events. '
                    'Overlap with a delayed ACK does not alone establish causality.')
