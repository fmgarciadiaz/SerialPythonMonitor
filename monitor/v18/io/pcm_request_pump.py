"""Service PCM requests independently of RF dispatch; never consume control ACKs."""
from threading import Event, Thread
from queue import Empty


class PcmRequestPump:
    def __init__(self, receive, dispatch, failed):
        self.receive=receive;self.dispatch=dispatch;self.failed=failed
        self.stopped=Event()
        self.thread=Thread(target=self._run,name='v18-pcm-requests',daemon=True)

    def start(self):
        self.thread.start()
        return self

    def _run(self):
        try:
            while not self.stopped.is_set():
                try:event=self.receive(timeout=.05)
                except Empty:continue
                if self.stopped.is_set():break
                if event.get('type')!='pcm_request':
                    raise ValueError('Canal PCM recibió un evento de control/RF')
                self.dispatch(event)
        except Exception as exc:
            if not self.stopped.is_set():self.failed(exc)

    def close(self):
        self.stopped.set()
        self.thread.join()
