"""Passive bounded host GC timing. Never forces collection or changes policy."""
from collections import deque
from contextlib import contextmanager
import gc
import threading
import time


class GcAudit:
    def __init__(self,clock=time.monotonic,cpu=time.thread_time,thread=threading.get_ident):
        self.clock,self.cpu,self.thread=clock,cpu,thread
        self.pending={};self.top=[];self.recent=deque(maxlen=64)
        self.unmatched=0
        self.generations={g:dict(count=0,wall_ms=0.,max_ms=0.,over20ms=0,over100ms=0) for g in range(3)}

    def observe(self,phase,info):
        generation=info['generation']
        if generation not in self.generations:return
        now,cpu,thread=self.clock(),self.cpu(),self.thread()
        key=(thread,generation)
        if phase=='start':
            self.pending[key]=(now,cpu)
        elif phase=='stop':
            start=self.pending.pop(key,None)
            if start is None:
                self.unmatched+=1;return
            duration=(now-start[0])*1000
            record=dict(start=start[0],end=now,wall_ms=duration,
                thread_cpu_ms=(cpu-start[1])*1000,thread=thread,generation=generation,
                collected=info.get('collected',0),uncollectable=info.get('uncollectable',0))
            stats=self.generations[generation]
            stats['count']+=1;stats['wall_ms']+=duration
            stats['max_ms']=max(stats['max_ms'],duration)
            stats['over20ms']+=duration>=20;stats['over100ms']+=duration>=100
            self.recent.append(record);self.top.append(record)
            self.top.sort(key=lambda row:row['wall_ms'],reverse=True)
            del self.top[16:]

    def snapshot(self):
        return dict(generations=self.generations,top=list(self.top),recent=list(self.recent),
                    unfinished=len(self.pending),unmatched_stops=self.unmatched)


@contextmanager
def observe_gc(audit):
    callback=audit.observe
    gc.callbacks.append(callback)
    try:yield audit
    finally:
        if callback in gc.callbacks:gc.callbacks.remove(callback)
