"""Local advisory lock interoperable with V18; no Q/ADB operation.

Keep this context in the process that owns board I/O. A coordinator-only
context does not protect a surviving spawn child after coordinator death.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import tempfile


@contextmanager
def board_owner(serial, purpose='monitor V18'):
    key = hashlib.sha256(str(serial).encode()).hexdigest()[:20]
    path = Path(tempfile.gettempdir()) / f'serialmonitor-q-{os.getuid()}-{key}.lock'
    # Keep the inode after releasing: unlinking permits two independent locks.
    with path.open('a+', encoding='utf-8') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            owner = lock.read(200).strip()
            raise RuntimeError(f'Q ocupado por otra sesión ({owner or "adquisición activa"}). '
                               'Cerrar esa sesión antes de conectar.') from None
        try:
            lock.seek(0)
            lock.truncate()
            lock.write(f'PID {os.getpid()} · {purpose}')
            lock.flush()
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
