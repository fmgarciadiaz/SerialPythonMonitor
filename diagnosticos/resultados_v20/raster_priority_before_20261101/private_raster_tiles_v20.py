"""Private tiled raster adapter. Explicit opt-in; never owns acquisition or Q."""
import multiprocessing as mp
from multiprocessing import shared_memory
import time
import numpy as np
from PySide6 import QtGui
from tools.benchmark_raster_tiles_v20 import tile


def _child(pipe):
    try:
        while True:
            job=pipe.recv()
            if job is None:return
            start=time.perf_counter()
            try:tile(job);pipe.send(dict(ok=True,ms=(time.perf_counter()-start)*1000))
            except Exception as exc:pipe.send(dict(ok=False,error=repr(exc)))
    except (EOFError,BrokenPipeError):pass
    finally:pipe.close()


class TiledRasterProcess:
    def __init__(self,workers,baseline):
        if workers not in (2,4):raise ValueError('Private experiment requires 2 or 4 strips')
        self.workers=workers;self.baseline=baseline;self.fallback=None;self.mode='tiles'
        self.children=[];self._pending=None;self.closed=False
        ctx=mp.get_context('spawn')
        try:
            for _ in range(workers):
                parent,child=ctx.Pipe();process=ctx.Process(target=_child,args=(child,),daemon=True,name='Arduscopio private raster strip')
                process.start();child.close();self.children.append((parent,process))
        except Exception:self.close();raise
    @property
    def pending(self):return self.fallback.pending if self.mode=='fallback' else self._pending
    @property
    def busy(self):return self.pending is not None
    def submit(self,traces,rect,size,options,token,frame):
        if self.closed or self.busy:return False
        # Antialias clipping has measured pixel differences. Keep its original
        # worker; reject any X sequence the private strip experiment cannot split.
        if options['style']=='Suave' or any(not np.all(np.isfinite(x)) or np.any(np.diff(x)<0) for x,y,c in traces):
            if self.fallback is None:self.fallback=self.baseline()
            self.mode='fallback';return self.fallback.submit(traces,rect,size,options,token,frame)
        self.mode='tiles';width,height=size
        if width<=0 or height<=0 or width*height>32000000:raise ValueError('Invalid raster dimensions')
        inputs=shared_memory.SharedMemory(create=True,size=max(1,sum(len(x)*16 for x,y,c in traces)));output=None
        try:
            output=shared_memory.SharedMemory(create=True,size=width*height*4)
            pixels=np.ndarray((height,width,4),np.uint8,output.buf);pixels[:]=0;del pixels
            descriptors=[];offset=0
            for x,y,color in traces:
                n=len(x);np.ndarray((n,),np.float64,inputs.buf,offset)[:]=x
                np.ndarray((n,),np.float64,inputs.buf,offset+n*8)[:]=y
                descriptors.append((offset,n,color));offset+=n*16
            self._pending=dict(inputs=inputs,output=output,token=token,frame=frame,rect=rect,size=size,received={},start=time.perf_counter())
            for i,(pipe,process) in enumerate(self.children):
                pipe.send(dict(source=inputs.name,target=output.name,traces=descriptors,rect=rect,options=options,size=size,clip=(i*width//self.workers,(i+1)*width//self.workers)))
            return True
        except Exception:
            # A partial dispatch may still borrow these buffers. Stop only the
            # owned graphics children before unlinking the pending arenas.
            if self._pending:self.close()
            else:
                inputs.close();inputs.unlink()
                if output is not None:output.close();output.unlink()
            raise
    def poll(self):
        if self.mode=='fallback':return self.fallback.poll()
        pending=self._pending
        if pending is None:return None
        for i,(pipe,process) in enumerate(self.children):
            if i in pending['received']:continue
            if pipe.poll():
                reply=pipe.recv()
                if not reply['ok']:raise RuntimeError(reply['error'])
                pending['received'][i]=reply
            elif not process.is_alive():raise RuntimeError('Private strip worker exited')
        if len(pending['received'])<self.workers:return None
        width,height=pending['size']
        try:
            image=QtGui.QImage(pending['output'].buf,width,height,width*4,QtGui.QImage.Format.Format_ARGB32_Premultiplied).copy()
            return dict(image=image,frame=pending['frame'],token=pending['token'],rect=pending['rect'],milliseconds=(time.perf_counter()-pending['start'])*1000)
        finally:
            self._pending=None
            for name in ('inputs','output'):pending[name].close();pending[name].unlink()
    def close(self):
        if self.closed:return
        self.closed=True
        for pipe,process in self.children:
            if process.is_alive():process.terminate()
        deadline=time.monotonic()+.4
        for pipe,process in self.children:
            process.join(max(0,deadline-time.monotonic()))
            if process.is_alive():process.kill();process.join(.25)
            pipe.close()
        if self._pending:
            for name in ('inputs','output'):self._pending[name].close();self._pending[name].unlink()
            self._pending=None
        if self.fallback is not None:self.fallback.close()
