"""Bounded shutdown for Python 3.13 computation workers; never owns the Q."""
from concurrent.futures import CancelledError, TimeoutError, Executor, Future
from queue import Queue, Empty
from threading import Lock, Thread, current_thread
import time


class ComputationExecutor(Executor):
    """One ordered computation thread with Future semantics and no exit hook.

    Pure computation may outlive a cancelled UI, so this thread is a daemon.
    It must never own Q I/O. Unlike ThreadPoolExecutor, interpreter shutdown
    does not join an unresponsive native computation through its atexit hook.
    """
    def __init__(self,max_workers=1,thread_name_prefix='v20-compute'):
        if max_workers!=1:raise ValueError('Ordered computation requires one worker')
        self._jobs=Queue();self._lock=Lock();self._shutdown=False;self._threads=set()
        self._name=thread_name_prefix

    def submit(self,fn,/,*args,**kwargs):
        with self._lock:
            if self._shutdown:raise RuntimeError('Computation executor is closed')
            future=Future()
            if not self._threads:
                thread=Thread(target=self._run,name=self._name,daemon=True)
                self._threads.add(thread);thread.start()
            self._jobs.put((future,fn,args,kwargs))
            return future

    def _run(self):
        while True:
            job=self._jobs.get()
            if job is None:return
            future,fn,args,kwargs=job
            if not future.set_running_or_notify_cancel():continue
            try:result=fn(*args,**kwargs)
            except BaseException as exc:future.set_exception(exc)
            else:future.set_result(result)
            finally:
                # Do not retain the last RF/audio payload while idle.
                job=future=fn=args=kwargs=result=None

    def shutdown(self,wait=True,*,cancel_futures=False):
        cancelled=[]
        with self._lock:
            if not self._shutdown:
                self._shutdown=True
                if cancel_futures:
                    while True:
                        try:cancelled.append(self._jobs.get_nowait()[0])
                        except Empty:break
                self._jobs.put(None)
        for future in cancelled:future.cancel()
        if wait:
            for thread in self._threads:
                if thread is not current_thread():thread.join()


def wait_result(future, running, timeout=30.):
    deadline=time.monotonic()+timeout
    while running():
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise TimeoutError('El proceso de cálculo excedió su plazo')
        try:
            return future.result(timeout=min(.05,remaining))
        except TimeoutError:
            if future.done():
                raise  # TimeoutError raised by the task itself.
    future.cancel()
    raise CancelledError('Cálculo cancelado al cerrar')


def close_process_pool(pool, timeout=1.):
    """Python 3.13 has no public terminate_workers; keep its adapter here.

    Snapshot children before shutdown clears the executor's process registry.
    Only these computation children may be terminated, never the Q receiver.
    """
    processes=tuple((getattr(pool,'_processes',None) or {}).values())
    manager=getattr(pool,'_executor_manager_thread',None)
    errors=[]
    def request_shutdown():
        try:pool.shutdown(wait=False,cancel_futures=True)
        except Exception as exc:errors.append(str(exc))
    request=Thread(target=request_shutdown,name='v20-pool-close',daemon=True)
    deadline=time.monotonic()+timeout
    request.start();request.join(max(0.,deadline-time.monotonic()))
    if manager is not None:manager.join(max(0.,deadline-time.monotonic()))
    # The executor manager alone reaps its children. Concurrent Process.join()
    # calls can race waitpid on macOS and leave a false 'still alive' result.
    def unreaped():
        return [p for p in processes if p._popen is not None and p._popen.returncode is None]
    forced=unreaped()
    for process in forced:process.terminate()
    if manager is not None:manager.join(.5)
    for process in unreaped():process.kill()
    if manager is not None:manager.join(1.)
    request.join(.2)
    if manager is None:
        for process in processes:process.join(.2)
    if request.is_alive() or (manager is not None and manager.is_alive()) or unreaped() or errors:
        detail=[(p.pid,p._popen.returncode if p._popen else None) for p in processes]
        raise RuntimeError(f'No se pudo cerrar un proceso de cálculo: {detail}; {errors}')
    return len(forced)


def close_thread_pool(pool, timeout=1.):
    threads=tuple(getattr(pool,'_threads',()))
    pool.shutdown(wait=False,cancel_futures=True)
    deadline=time.monotonic()+timeout
    for thread in threads:thread.join(max(0.,deadline-time.monotonic()))
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError('Un hilo de cálculo no respondió al cierre')
