"""Experimental nondestructive socket queue samples; no production hooks."""
import array
from collections import deque
import fcntl
import termios
import time


def queued_bytes(sock):
    value = array.array('i', [0])
    try:
        fcntl.ioctl(sock.fileno(), termios.FIONREAD, value, True)
        return {'bytes': value[0], 'error': None}
    except OSError as exc:
        return {'bytes': None, 'error': exc.errno}


class SocketTrace:
    def __init__(self):
        self.recent = deque(maxlen=128)
        self.top = []
        self.count = 0

    def read(self, connection, original):
        before = queued_bytes(connection.socket)
        start = time.monotonic()
        error = None
        data = None
        try:
            data = original(connection)
            return data
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            end = time.monotonic()
            after = queued_bytes(connection.socket)
            item = dict(start=start, end=end, wall_seconds=end-start,
                        before=before, after=after,
                        returned_bytes=len(data) if data is not None else None, error=error)
            self.count += 1
            self.recent.append(item)
            if len(self.top) < 8 or item['wall_seconds'] > self.top[-1]['wall_seconds']:
                self.top.append(item)
                self.top.sort(key=lambda x: x['wall_seconds'], reverse=True)
                del self.top[8:]

    def snapshot(self):
        return dict(count=self.count, top=self.top, recent=list(self.recent), limitations=[
            'FIONREAD samples bytes queued at two instants, not arrival history or ACK identity.',
            'Read wall time includes blocking and scheduling; bytes may arrive during an unobserved pause.',
            'Two extra ioctls per read add experimental overhead; no production change.'])
