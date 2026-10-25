"""Opt-in compact flow records; one append-only JSONL file per process."""
import json
import os
import threading
import time

_lock = threading.Lock()

def record(event, batch_id=None):
    directory = os.environ.get('MONITOR_V18_FLOW_TRACE')
    if not directory:
        return
    entry = dict(event=event, monotonic=time.monotonic(), pid=os.getpid(),
                 thread_id=threading.get_ident(), batch_id=batch_id)
    payload = (json.dumps(entry, separators=(',', ':')) + '\n').encode()
    try:
        with _lock:
            os.makedirs(directory, exist_ok=True)
            fd = os.open(os.path.join(directory, f'flow-{os.getpid()}.jsonl'),
                         os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
    except OSError:
        # Evidence failure must never interrupt acquisition or credit delivery.
        pass
