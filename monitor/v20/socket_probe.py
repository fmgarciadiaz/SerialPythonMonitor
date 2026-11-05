"""Diagnostic-only socket readiness/wakeup sampler; never consumes socket data.

A separate thread samples at 1 ms. This is an observation bound, not a packet
arrival timestamp: delayed wakeups can hide an earlier readiness transition.
"""
import select
import threading
import time
import numpy as np


class SocketProbe:
    def __init__(self, sock, capacity=200000, interval=.001):
        self.sock=sock;self.interval=interval
        self.samples=np.empty((capacity,3),dtype=np.float64)
        self.count=0;self.overwritten=0;self.error=None
        self._stop=threading.Event()
        self._thread=threading.Thread(target=self._run,name='diagnostic-socket-probe',daemon=True)

    def start(self):self._thread.start()

    def _run(self):
        previous=time.monotonic()
        try:
            while not self._stop.is_set():
                ready=bool(select.select([self.sock],[],[],0)[0])
                now=time.monotonic()
                if self.count<len(self.samples):
                    self.samples[self.count]=(now,now-previous,int(ready));self.count+=1
                else:self.overwritten+=1
                previous=now
                self._stop.wait(self.interval)
        except Exception as exc:self.error=str(exc)

    def close(self):
        self._stop.set();self._thread.join(5)
        if self._thread.is_alive():raise RuntimeError('Socket probe did not stop')

    def save(self,path):
        np.savez(path,samples=self.samples[:self.count],interval=self.interval,overwritten=self.overwritten)
        return dict(samples=self.count,overwritten=self.overwritten,error=self.error,
                    max_wake_gap_ms=float(self.samples[:self.count,1].max()*1000) if self.count else 0)


def _sample_process(sock, storage, count, omitted, stop, ready, errors, interval):
    samples=np.frombuffer(storage,dtype=np.float64).reshape(-1,3)
    previous=time.monotonic();ready.set()
    try:
        while not stop.is_set():
            readable=bool(select.select([sock],[],[],0)[0]);now=time.monotonic()
            if count.value<len(samples):
                samples[count.value]=(now,now-previous,int(readable));count.value+=1
            else:omitted.value+=1
            previous=now;stop.wait(interval)
    except Exception as exc:errors.send(str(exc))
    finally:errors.close();sock.close() # Close only the duplicate, never shutdown.


class ProcessSocketProbe:
    """Readiness sampler in a separate process, independent of owner's GIL.

    Still subject to OS scheduling. Never reads, writes or changes socket policy.
    """
    def __init__(self,sock,capacity=200000,interval=.001):
        import multiprocessing as mp
        context=mp.get_context('spawn')
        self.interval=interval;self.error=None
        self._storage=context.RawArray('d',capacity*3)
        self.samples=np.frombuffer(self._storage,dtype=np.float64).reshape(-1,3)
        self._count=context.RawValue('Q',0);self._omitted=context.RawValue('Q',0)
        self._stop=context.Event();self._ready=context.Event()
        self._errors,errors=context.Pipe(duplex=False)
        self._process=context.Process(target=_sample_process,args=(sock,self._storage,self._count,self._omitted,self._stop,self._ready,errors,interval),daemon=True)
        self._child_errors=errors

    @property
    def count(self):return self._count.value

    @property
    def overwritten(self):return self._omitted.value

    def start(self):
        self._process.start();self._child_errors.close()
        if not self._ready.wait(10):
            self.close();raise RuntimeError('Process socket probe did not become ready')

    def close(self):
        self._stop.set();self._process.join(5)
        if self._process.is_alive():
            self._process.terminate();self._process.join()
            raise RuntimeError('Process socket probe did not stop; terminated')
        if self._errors.poll():
            try:self.error=self._errors.recv()
            except EOFError:pass
        self._errors.close()

    def save(self,path):
        np.savez(path,samples=self.samples[:self.count],interval=self.interval,overwritten=self.overwritten)
        return dict(mode='process',samples=self.count,overwritten=self.overwritten,error=self.error,
            max_wake_gap_ms=float(self.samples[:self.count,1].max()*1000) if self.count else 0)
