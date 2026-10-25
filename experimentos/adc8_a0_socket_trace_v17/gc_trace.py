"""Passive bounded GC observations; never changes collection policy."""
import time


class GcTrace:
    def __init__(self, active):
        self.active = active
        self.starts = {}
        self.count = 0
        self.top = []

    def callback(self, phase, info):
        generation = info['generation']
        if phase == 'start':
            self.starts[generation] = (time.monotonic(), time.thread_time(), self.active())
        elif phase == 'stop':
            start = self.starts.pop(generation, None)
            if start is None:
                return
            end = time.monotonic()
            cpu = time.thread_time()-start[1]
            self.count += 1
            wall = end-start[0]
            if len(self.top)<8 or wall>self.top[-1]['wall_seconds']:
                self.top.append(dict(generation=generation,start=start[0],end=end,
                                     wall_seconds=wall,thread_cpu_seconds=cpu,active_a0=start[2],
                                     collected=info.get('collected'),uncollectable=info.get('uncollectable')))
                self.top.sort(key=lambda x:x['wall_seconds'],reverse=True)
                del self.top[8:]

    def snapshot(self):
        return dict(count=self.count,top=self.top,limitation='Passive Python cyclic GC callbacks only; no policy change.')
