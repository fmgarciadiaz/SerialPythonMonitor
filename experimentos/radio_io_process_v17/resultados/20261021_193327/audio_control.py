"""Offline asynchronous WAV/RADIO command state machine. No device I/O.

Returned packets must be sent once, in order, by the future owner transport.
Any send error must call fail(); no retry or assumed credit is provided here.
The default prebuffer is a test minimum, not V18's public audio policy.
"""
import math
from monitor.v17.receiver import unoq_wav as wav
from experimentos.radio_io_process_v17.prototype import Credits,RequestJournal
import numpy as np


class AudioControl:
    def __init__(self,window=2,timeout=.5,prebuffer=960):
        if type(window) is not int or not 1<=window<=30:raise ValueError('Invalid window')
        if not math.isfinite(timeout) or timeout<=0:raise ValueError('Invalid timeout')
        if type(prebuffer) is not int or prebuffer<1:raise ValueError('Invalid prebuffer')
        self.window=window;self.timeout=timeout;self.prebuffer=prebuffer
        self.journal=RequestJournal(first=0x80000000,last=0xfffffffe)
        self.pending={};self.state='new';self.epoch=0;self.session=0
        self.status=None;self.credits=None;self.offset=0;self.total=0;self.rate=40000
        self.last_now=-math.inf;self.error=None

    def fail(self,error):self.state='fault';self.error=str(error)

    def _clock(self,now):
        if not math.isfinite(now) or now<self.last_now:raise ValueError('Invalid clock')
        self.last_now=now

    def tick(self,now):
        self._clock(now)
        if self.pending and now-min(row[1] for row in self.pending.values())>=self.timeout:
            self.fail('ACK timeout; output uncertain')
            raise TimeoutError(self.error)

    def _command(self,op,now):
        self._clock(now)
        if self.pending:raise ValueError('Control must be serialized')
        rid=self.journal.reserve(self.epoch,self.session)
        packet=wav.command(rid,self.session,op,self.total if op==1 else 0,self.rate)
        self.pending[rid]=(op,now,0,self.session)
        return packet

    def query(self,now):
        if self.state not in ('new','ready','buffering','playing','stopped','occupied','done'):
            raise ValueError('QUERY in invalid state')
        return self._command(0,now)

    def begin(self,epoch,session,total,rate,now):
        if self.state not in ('ready','stopped','done') or self.pending or self.status is None:
            raise ValueError('BEGIN requires confirmed idle capability')
        if (type(epoch) is not int or not self.epoch<epoch<2**63 or
                type(session) is not int or not 0<session<2**32 or
                type(total) is not int or not 0<total<2**32 or rate not in wav.RATES or
                not self.status.rates_mask & (1<<wav.RATES.index(rate))):
            raise ValueError('Invalid or unsupported BEGIN')
        self._clock(now)
        self.epoch=epoch;self.session=session;self.total=total;self.rate=rate;self.offset=0
        self.credits=None;self.error=None
        packet=self._command(1,now);self.state='begin_wait'
        return packet

    def chunk(self,audio,now):
        audio.validate();self._clock(now)
        if self.state not in ('buffering','playing'):raise ValueError('CHUNK requires confirmed BEGIN')
        if (audio.epoch,audio.session,audio.offset)!=(self.epoch,self.session,self.offset):
            raise ValueError('Audio identity/offset mismatch')
        points=len(audio.pcm)//2
        if self.offset+points>self.total:raise ValueError('Audio exceeds total')
        if (len(self.pending)>=self.window or not self.credits.available or
                any(row[0]!=13 for row in self.pending.values())):return None
        rid=self.journal.reserve(self.epoch,self.session)
        packet=wav.chunk(rid,self.session,self.offset,np.frombuffer(audio.pcm,dtype='<u2'))
        self.credits.reserve(rid,self.offset+points)
        self.pending[rid]=(13,now,self.offset+points,self.session);self.offset+=points
        return packet

    def play(self,now):
        if (self.state!='buffering' or self.pending or
                self.credits.accepted<min(self.prebuffer,self.total)):
            raise ValueError('PLAY requires confirmed prebuffer')
        packet=self._command(2,now);self.state='play_wait';return packet

    def stop(self,now):
        if self.status is None and self.state=='new':raise ValueError('No known remote session')
        self._clock(now)
        self.journal.cancel();self.pending.clear()
        packet=self._command(3,now);self.state='stop_wait';return packet

    def acknowledge(self,status,now):
        self._clock(now)
        if self.state=='fault':raise RuntimeError('Audio controller faulted; STOP required')
        try:return self._acknowledge(status)
        except (ValueError,RuntimeError) as exc:
            self.fail(exc);raise

    def _acknowledge(self,status):
        row=self.pending.get(status.request_id)
        # QUERY discovery uses session=0 on the wire: response may describe a
        # pre-existing remote session. All other replies require exact session.
        discovery=row is not None and row[0]==0 and self.state=='new'
        identity_session=0 if discovery else status.session
        if not self.journal.acknowledge(status.request_id,identity_session,self.epoch):return False
        if row is None:raise ValueError('Missing request metadata')
        op,_,end,expected_session=row
        if status.reason:raise RuntimeError('Device rejected audio request')
        if status.state in (wav.State.UNDERRUN,wav.State.FAULT):raise RuntimeError('Device audio failure')
        if discovery:
            self.session=status.session;self.state='ready' if status.state==wav.State.IDLE else 'occupied'
        else:
            if status.session!=expected_session:raise ValueError('Wrong audio session')
            if op==3:
                if status.state!=wav.State.IDLE:raise ValueError('STOP not confirmed idle')
                self.state='stopped';self.credits=None
            elif op==1:
                if (status.state!=wav.State.BUFFERING or status.accepted or status.played or
                        status.total!=self.total or status.rate!=self.rate or status.free_blocks!=status.queue_slots):
                    raise ValueError('Contradictory BEGIN')
                self.credits=Credits(status.queue_slots);self.credits.query(status.free_blocks,0,0)
                self.state='buffering'
            elif self.credits is not None:
                if (status.rate!=self.rate or status.total!=self.total or
                        status.queue_slots!=self.credits.slots or status.accepted>self.offset):
                    raise ValueError('Audio configuration changed')
                if op==13:self.credits.acknowledge(status.request_id,status.free_blocks,status.accepted,status.played)
                else:self.credits.query(status.free_blocks,status.accepted,status.played)
                if status.state==wav.State.DONE:
                    if status.played!=self.total:raise ValueError('Premature DONE')
                    self.state='done'
                elif op==2:
                    if status.state!=wav.State.PLAYING:raise ValueError('PLAY not confirmed')
                    self.state='playing'
                elif status.state!=(wav.State.PLAYING if self.state=='playing' else wav.State.BUFFERING):
                    raise ValueError('Unexpected playback transition')
            elif op==0:
                self.state='ready' if status.state==wav.State.IDLE else 'occupied'
        del self.pending[status.request_id];self.status=status
        return True
