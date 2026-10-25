"""Isolated recv-first experiment; retain the original timed read on EAGAIN."""
import os
import socket
import time


class ReadyRead:
    def __init__(self):
        self.handles = []
        self.immediate = self.fallback = 0

    def read(self, connection, original):
        # Python's positive-timeout sockets already use O_NONBLOCK. A duplicate
        # with timeout=0 bypasses Python's pre-recv select without changing the
        # original socket object's timeout/sendall policy.
        sock = connection.socket
        if sock.gettimeout() is None or sock.gettimeout() <= 0:
            return original(connection)
        handle = next((raw for owner, raw in self.handles if owner is sock), None)
        if handle is None:
            if len(self.handles) >= 16:
                return original(connection)
            handle = socket.socket(fileno=os.dup(sock.fileno()))
            handle.setblocking(False)
            self.handles.append((sock, handle))
        try:
            data = handle.recv(65536)
        except BlockingIOError:
            self.fallback += 1
            return original(connection)
        if not data:
            # Preserve the original EOF/error behavior.
            return original(connection)
        self.immediate += 1
        connection.last_data = time.monotonic()
        return data

    def close(self):
        for _, handle in self.handles:
            handle.close()
        self.handles.clear()

    def close_connection(self, connection, original):
        sock = connection.socket
        retained = []
        for owner, handle in self.handles:
            if owner is sock:
                handle.close()
            else:
                retained.append((owner, handle))
        self.handles = retained
        return original(connection)
