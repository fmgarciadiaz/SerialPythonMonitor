"""Experimental bounded single-producer/single-consumer ADC shared ring.

Slots remain owned by the reader until copied. Full queues raise queue.Full;
no samples are dropped. No pickling or feeder thread in the audio owner.
Only the dedicated audio-owner diagnostic uses this transport.
"""
import queue
import numpy as np


class SharedAdcRing:
    def __init__(self, context, slots=32, rows=4096):
        if slots < 1 or rows < 1:
            raise ValueError('Invalid ADC ring capacity')
        self.slots, self.rows = slots, rows
        self._storage = context.RawArray('I', slots * rows * 4)
        self._lengths = context.RawArray('I', slots)
        self._free = context.Semaphore(slots)
        self._ready = context.Semaphore(0)
        self._write = self._read = 0
        self._view = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_view'] = None
        return state

    def _array(self):
        if self._view is None:
            self._view = np.frombuffer(self._storage, dtype=np.uint32).reshape(self.slots, self.rows, 4)
        return self._view

    def put_nowait(self, data):
        if data.dtype != np.uint32 or data.ndim != 2 or data.shape[1] != 4 or not 0 < len(data) <= self.rows:
            raise ValueError('Invalid ADC shared batch')
        if not self._free.acquire(False):
            raise queue.Full
        slot = self._write % self.slots
        try:
            np.copyto(self._array()[slot, :len(data)], data)
            self._lengths[slot] = len(data)
        except BaseException:
            self._free.release()
            raise
        self._write += 1
        self._ready.release()

    def get(self, timeout=None):
        acquired = self._ready.acquire() if timeout is None else self._ready.acquire(timeout=timeout)
        if not acquired:
            raise queue.Empty
        slot = self._read % self.slots
        try:
            # Copy before releasing ownership; callers may retain this batch.
            data = self._array()[slot, :self._lengths[slot]].copy()
        finally:
            self._read += 1
            self._free.release()
        return data

    def get_nowait(self):
        return self.get(timeout=0)

    def close(self):
        self._view = None

    def join_thread(self):
        pass
