"""Bounded nonblocking owner-loop component. No sockets, Qt or Q connection.

Transport contract: send(bytes-like)->positive count; recv(limit)->bytes;
BlockingIOError means not ready. Every method must itself be nonblocking.
This component cannot restore hardware; any failure leaves output uncertain.
"""
from collections import deque
import math
import queue
from monitor.v18.io.audio_control import AudioControl
from monitor.v18.io.wire_adapter import ProtocolIngress


class AudioPump:
    def __init__(self,transport,on_event=lambda *_:None,pcm_capacity=48,poll_interval=.02,**control_options):
        if type(pcm_capacity) is not int or not 1<=pcm_capacity<=48:raise ValueError('Invalid PCM capacity')
        if not math.isfinite(poll_interval) or not .004<=poll_interval<=.1:raise ValueError('Invalid poll interval')
        self.transport=transport;self.on_event=on_event;self.control=AudioControl(**control_options)
        self.ingress=ProtocolIngress(self._event);self.pcm=deque();self.capacity=pcm_capacity
        self.outgoing=None;self.written=0;self.queued_end=0;self.next_query=0
        self.interval=poll_interval;self.now=0.;self.closed=False;self.error=None
        self.stop_at=None;self.cancelled_pcm=0;self.transport_closed=False

    def _check_open(self):
        if self.closed:raise RuntimeError('Pump closed; output uncertain')

    def _close_transport(self):
        if not self.transport_closed:
            self.transport_closed=True;self.transport.close()

    def _fail(self,exc):
        self.closed=True;self.error=repr(exc);self.control.fail(exc)
        try:self._close_transport()
        except Exception as close_error:self.error+='; close='+repr(close_error)

    def begin(self,epoch,session,total,rate,now):
        self._check_open()
        if self.outgoing is not None or self.stop_at is not None:raise ValueError('Transport busy')
        packet=self.control.begin(epoch,session,total,rate,now)
        self.pcm.clear();self.queued_end=0;self.outgoing=packet;self.written=0

    def enqueue(self,audio):
        self._check_open();audio.validate()
        if self.stop_at is not None or self.control.state not in ('begin_wait','buffering','play_wait','playing'):
            raise ValueError('No active audio session')
        if (audio.epoch,audio.session,audio.offset)!=(self.control.epoch,self.control.session,self.queued_end):
            raise ValueError('Queued audio gap/session mismatch')
        if self.queued_end+len(audio.pcm)//2>self.control.total:raise ValueError('PCM exceeds total')
        if len(self.pcm)>=self.capacity:raise queue.Full('PCM queue full; retry without dropping')
        self.pcm.append(audio);self.queued_end+=len(audio.pcm)//2

    def stop(self,now):
        self._check_open();self.control._clock(now)
        if self.control.status is None:raise ValueError('Remote session not discovered')
        if self.stop_at is None:self.stop_at=now
        self.cancelled_pcm+=len(self.pcm);self.pcm.clear()
        # A partially written frame must finish before STOP to preserve framing.
        # An unsent frame can be superseded; control.stop() cancels its journal.
        if self.outgoing is not None and self.written==0:
            # Unsent BEGIN never changed the peer's session. STOP must target
            # the last confirmed remote identity, not the proposed new one.
            if self.control.state=='begin_wait':self.control.session=self.control.status.session
            self.outgoing=None

    def _write(self):
        if self.outgoing is None:return
        try:count=self.transport.send(memoryview(self.outgoing)[self.written:])
        except BlockingIOError:return
        if type(count) is not int or not 0<count<=len(self.outgoing)-self.written:
            raise ConnectionError('Invalid/closed transport write')
        self.written+=count
        if self.written==len(self.outgoing):self.outgoing=None;self.written=0

    def _schedule(self):
        c=self.control
        if self.outgoing is not None:return
        if self.stop_at is not None:
            if c.state!='stop_wait':self.outgoing=c.stop(self.now)
            return
        if c.state in ('begin_wait','play_wait','stop_wait','fault','done','occupied'):return
        if c.state=='buffering' and not c.pending and c.credits.accepted>=min(c.prebuffer,c.total):
            self.outgoing=c.play(self.now)
        elif c.state in ('buffering','playing') and self.pcm:
            packet=c.chunk(self.pcm[0],self.now)
            if packet is not None:self.pcm.popleft();self.outgoing=packet
        if self.outgoing is None and not c.pending and c.state in ('new','buffering','playing') and self.now>=self.next_query:
            self.outgoing=c.query(self.now);self.next_query=self.now+self.interval

    def _event(self,kind,value):
        if kind=='wav':
            self.control.acknowledge(value,self.now)
            if self.control.state=='stopped':self.stop_at=None
            self._schedule();self._write() # Service ACK before decoding subsequent RF.
        self.on_event(kind,value)

    def turn(self,now):
        self._check_open()
        try:
            self.now=now
            if self.stop_at is not None and now-self.stop_at>=self.control.timeout:
                raise TimeoutError('STOP deadline; output uncertain')
            # STOP may supersede expired requests, but never incomplete framing.
            self._schedule()
            self.control.tick(now);self._write()
            try:data=self.transport.recv(32*992)
            except BlockingIOError:data=None
            if data is not None:
                if data==b'':
                    self.ingress.eof();raise EOFError('Transport ended; output uncertain')
                self.ingress.feed(data)
            self._schedule();self._write()
        except Exception as exc:
            self._fail(exc);raise

    def close(self):
        """Local release only. Call STOP and await stopped before normal release."""
        if self.closed:return
        if self.control.state not in ('new','ready','stopped','done') or self.control.pending:
            self._fail(RuntimeError('Closed without confirmed STOP; output uncertain'))
            return
        self.closed=True;self._close_transport()
