"""Nonblocking adapter for an already connected stream socket.

Does not discover Q, call ADB, connect/reconnect, reset hardware or restore it.
The caller transfers exclusive ownership of a connected socket on success.
"""
import math
import socket
import time


class SocketTransport:
    def __init__(self,connected,stall_timeout=2.,clock=time.monotonic):
        if not math.isfinite(stall_timeout) or stall_timeout<=0:raise ValueError('Invalid stream timeout')
        if not isinstance(connected,socket.socket):raise TypeError('Connected socket required')
        if connected.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_STREAM:raise ValueError('Stream socket required')
        connected.getpeername() # Validate connection before taking ownership.
        if connected.family in (socket.AF_INET,socket.AF_INET6):
            connected.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        connected.setblocking(False)
        self.socket=connected;self.closed=False;self.timeout=stall_timeout;self.clock=clock
        self.last_data=clock();self.sent_bytes=0;self.received_bytes=0

    def _open(self):
        if self.closed:raise RuntimeError('Transport closed')

    def send(self,data):
        self._open()
        if not isinstance(data,(bytes,memoryview)) or not 0<len(data)<=32*992:
            raise ValueError('Bounded bytes payload required')
        count=self.socket.send(data) # Exactly one syscall; short writes stay short.
        if count==0:raise ConnectionError('Socket write returned zero')
        self.sent_bytes+=count
        return count

    def recv(self,limit):
        self._open()
        if type(limit) is not int or not 1<=limit<=32*992:raise ValueError('Invalid read bound')
        try:data=self.socket.recv(limit)
        except BlockingIOError:
            if self.clock()-self.last_data>=self.timeout:raise TimeoutError('Stream stopped delivering data')
            raise
        if data:self.received_bytes+=len(data);self.last_data=self.clock()
        return data # EOF remains EOF, distinct from EAGAIN.

    def close(self):
        if self.closed:return
        self.closed=True;self.socket.close()
