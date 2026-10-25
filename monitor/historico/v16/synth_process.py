"""Experimental asynchronous Synth worker; at most one requested audio block.

The receiver still owns the Q and its credits. This isolates generation from
host GC, but does not yet isolate delivery from ADC or GUI pauses.
"""
import multiprocessing as mp
import time
import numpy as np
from monitor.historico.v16.fm_source import FMSource

def read_with_audio_wakeup(connection, source):
    """Wake the receiver for finished audio without consuming its reply.

    The receiver remains the only socket reader. Prefer socket data if both
    inputs are ready, so ACK/ADC processing cannot be starved by the worker.
    """
    handle=source.audio_ready_handle
    if handle is None:return connection.read()
    import select
    ready,_,_=select.select([connection.socket,handle],[],[],connection.socket.gettimeout())
    if connection.socket in ready or not ready:return connection.read()
    return b''

def _worker(pipe,rate,parameters):
    try:
        from monitor.historico.v16.virtual_instruments import warmup
        from monitor.historico.v16.fm_feedback import warmup as feedback_warmup
        warmup();feedback_warmup()
        source=FMSource(rate,parameters);source.prepare_audio()
        pipe.send(('ready',))
        while True:
            command=pipe.recv()
            if command[0]=='stop':break
            if command[0]=='update':source.update(command[1]);continue
            _,start,end,levels=command
            began=time.perf_counter()
            codes=source[start:end] if levels is None else source.render_dac_codes(start,end,*levels)
            pipe.send(('block',start,end,codes,(time.perf_counter()-began)*1000))
    except EOFError:pass
    except Exception as exc:
        try:pipe.send(('error',repr(exc)))
        except (BrokenPipeError,EOFError):pass
    finally:pipe.close()

class SynthProcess(FMSource):
    def __init__(self,rate,parameters,wait_ready=True):
        super().__init__(rate,parameters)
        context=mp.get_context('spawn');self._pipe,child=context.Pipe()
        self._process=context.Process(target=_worker,args=(child,rate,parameters),daemon=True)
        self._pending_block=None;self.max_worker_render_ms=0.
        self.last_dac_levels=None
        self._ready=False
        self._process.start();child.close()
        try:
            if wait_ready:
                if not self._pipe.poll(30):raise TimeoutError('Synth worker no inició')
                self.is_ready()
        except Exception:self.close();raise

    def is_ready(self):
        if self._ready:return True
        if not self._pipe.poll():
            if not self._process.is_alive():raise RuntimeError('Synth worker no inició')
            return False
        reply=self._pipe.recv()
        if reply[0]!='ready':raise RuntimeError(str(reply))
        self._ready=True;return True

    def prepare_audio(self):
        if not self.is_ready():raise RuntimeError('Synth worker todavía no está preparado')

    @property
    def audio_ready_handle(self):
        return self._pipe if self._pending_block is not None else None

    def update(self,parameters):
        super().update(parameters)
        if hasattr(self,'_pipe'):self._pipe.send(('update',parameters))

    def __getitem__(self,selection):
        raise RuntimeError('SynthProcess requiere reposición asincrónica')

    def try_codes(self,start,end,levels=None):
        self.prepare_audio()
        if start!=self.position or not start<end:raise ValueError('Bloque worker fuera de secuencia')
        if self._pending_block is None:
            self._pipe.send(('render',start,end,levels));self._pending_block=(start,end)
            self._pending_levels=(float(np.asarray(levels[0]).reshape(-1)[-1]),float(np.asarray(levels[1]).reshape(-1)[-1])) if levels is not None else None
        elif self._pending_block!=(start,end):raise ValueError('Más de un bloque solicitado al worker')
        if not self._pipe.poll():
            if not self._process.is_alive():raise RuntimeError('Synth worker se cerró')
            return None
        reply=self._pipe.recv()
        if reply[0]=='error':raise RuntimeError(reply[1])
        if reply[:3]!=('block',start,end):raise RuntimeError('Respuesta worker fuera de secuencia')
        self._pending_block=None;self.position=end
        self.last_dac_levels=self._pending_levels
        self.max_worker_render_ms=max(self.max_worker_render_ms,reply[4])
        return reply[3]

    def close(self):
        if getattr(self,'_pipe',None) is None:return
        try:self._pipe.send(('stop',))
        except (BrokenPipeError,EOFError,OSError):pass
        self._process.join(2)
        if self._process.is_alive():self._process.terminate();self._process.join(2)
        self._pipe.close();self._pipe=None
