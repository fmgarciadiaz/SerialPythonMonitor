"""Offline process-owner contract. Synthetic device only; cannot connect to Q.

Control messages are FIFO; STOP intentionally supersedes queued audio.
RF is lossless until explicit overload failure. Progress snapshots may coalesce.
"""
from collections import deque
from dataclasses import dataclass
import multiprocessing as mp
import math
import queue
import struct
import time


@dataclass(frozen=True)
class Control:
    sequence:int
    op:str
    epoch:int=0
    session:int=0
    rate:int=40000


@dataclass(frozen=True)
class Audio:
    epoch:int
    session:int
    offset:int
    pcm:bytes

    def validate(self):
        if (type(self.epoch) is not int or not 0<self.epoch<2**63
                or type(self.session) is not int or not 0<self.session<2**32
                or type(self.offset) is not int):raise ValueError('Invalid audio identity')
        if not isinstance(self.pcm,bytes) or not 0<len(self.pcm)<=960 or len(self.pcm)%2:
            raise ValueError('Audio payload must be immutable PCM12, at most480points')
        if not 0<=self.offset<=0xffffffff-len(self.pcm)//2 or any(v[0]>4095 for v in struct.iter_unpack('<H',self.pcm)):
            raise ValueError('Invalid DAC codes or offset')


@dataclass(frozen=True)
class Rf:
    first:int
    count:int
    payload:bytes|tuple
    generation:int
    ordinal:int


class RfBarrier:
    """Parent-side gate. A caller retains at most one frame awaiting CONFIG.

    CONFIG acknowledgement may overtake RF. Publication changes only after
    all frames before its barrier have been consumed. No internal RF buffer.
    """
    def __init__(self,block_size=864):
        if block_size is not None and (type(block_size) is not int or not 1<=block_size<=904):raise ValueError('Invalid RF block size')
        self.block_size=block_size
        self.generation=0;self.consumed=0;self.pending=None;self.next_first=None

    def configure(self,generation,barrier,first_index=None):
        if (type(generation) is not int or generation!=self.generation+1
                or type(barrier) is not int or barrier<self.consumed or self.pending is not None
                or (first_index is not None and (type(first_index) is not int or not 0<=first_index<2**32))):
            raise ValueError('Invalid RF configuration barrier')
        self.pending=(generation,barrier,first_index)
        self._advance()

    def _advance(self):
        if self.pending is not None and self.consumed==self.pending[1]:
            self.generation=self.pending[0]
            if self.pending[2] is not None:self.next_first=self.pending[2]
            self.pending=None

    def consume(self,frame):
        if (frame.ordinal!=self.consumed or not 1<=frame.count<=904
                or (self.block_size is not None and frame.count!=self.block_size)
                or len(frame.payload)!=frame.count or not 0<=frame.first<2**32
                or (self.next_first is not None and frame.first!=self.next_first)):
            raise ValueError('RF gap, repetition or invalid frame')
        if frame.generation==self.generation+1 and self.pending is None:
            return False # CONFIG event has not arrived; caller retains this frame.
        if frame.generation!=self.generation:
            raise ValueError('RF generation mismatch')
        self.consumed+=1;self.next_first=(frame.first+frame.count)&0xffffffff
        self._advance()
        return True


class RequestJournal:
    """Bounded local RID ownership; wire replies carry no IPC epoch.

    RIDs never repeat during this owner lifetime. Retired entries are bounded;
    replies older than retained history fail closed rather than guess ownership.
    """
    def __init__(self,limit=256,first=1,last=0xffffffff):
        if type(limit) is not int or limit<1:raise ValueError('Invalid journal limit')
        if type(first) is not int or type(last) is not int or not 1<=first<=last<=0xffffffff:
            raise ValueError('Invalid RID range')
        self.limit=limit;self.next_rid=first-1;self.last_rid=last;self.pending={};self.retired={}

    def reserve(self,epoch,session):
        if len(self.pending)>=self.limit or self.next_rid>=self.last_rid:
            raise ValueError('RID journal exhausted')
        self.next_rid+=1;self.pending[self.next_rid]=(epoch,session)
        return self.next_rid

    def _retire(self,rid,identity,cancelled):
        self.retired[rid]=(identity,cancelled)
        while len(self.retired)>self.limit:del self.retired[next(iter(self.retired))]

    def cancel(self):
        for rid,identity in self.pending.items():self._retire(rid,identity,True)
        self.pending.clear()

    def acknowledge(self,rid,session,epoch):
        if rid in self.pending:
            identity=self.pending[rid]
            if identity!=(epoch,session):raise ValueError('ACK journal identity mismatch')
            del self.pending[rid];self._retire(rid,identity,False)
            return True
        if rid in self.retired:
            identity,cancelled=self.retired[rid]
            if identity[1]!=session:raise ValueError('ACK retired session mismatch')
            if cancelled:return False
            raise ValueError('Duplicate ACK')
        raise ValueError('Unknown ACK RID')


class Credits:
    def __init__(self,slots):
        self.slots=slots;self.free=slots;self.pending={};self.accepted=0;self.played=0

    @property
    def available(self):return max(0,self.free-len(self.pending))

    def reserve(self,rid,end):
        if rid in self.pending or not self.available:raise ValueError('No confirmed credit')
        self.pending[rid]=end

    def acknowledge(self,rid,free,accepted,played):
        if rid not in self.pending:raise ValueError('Unknown or duplicate ACK')
        if (not 0<=free<=self.slots or not self.played<=played<=accepted
                or accepted<self.accepted or accepted<self.pending[rid]):
            raise ValueError('Contradictory ACK')
        del self.pending[rid];self.free=free;self.accepted=accepted;self.played=played

    def query(self,free,accepted,played):
        if self.pending or not 0<=free<=self.slots or not self.played<=played<=accepted or accepted<self.accepted:
            raise ValueError('Contradictory or unserialized QUERY')
        self.free=free;self.accepted=accepted;self.played=played


class SimDevice:
    """No sockets/Qt/firmware. Models DAC consumption and delayed confirmed ACKs."""
    def __init__(self,ack_delay,drop_acks=False,simulate_disconnect=False,simulate_restore_failure=False):
        self.simulate_disconnect=simulate_disconnect;self.simulate_restore_failure=simulate_restore_failure
        self.original=dict(bits=14,rate=40000,generator=False)
        self.config=dict(self.original);self.delay=ack_delay;self.drop_acks=drop_acks;self.begin(40000)
        self.config=dict(self.original)

    def begin(self,rate,epoch=0,session=0):
        self.rate=rate;self.accepted=self.played=0;self.blocks=deque()
        self.acks=getattr(self,'acks',deque());self.epoch=epoch;self.session=session
        self.playing=False;self.last=time.monotonic();self.fraction=0.;self.underrun=False
        self.config['generator']=True

    def pump(self,now):
        if self.simulate_disconnect and self.accepted:raise ConnectionError('simulated_backend_disconnected')
        if self.playing:
            due=(now-self.last)*self.rate+self.fraction;consume=int(due);self.fraction=due-consume
            if consume>self.accepted-self.played:
                self.underrun=True;self.playing=False
            self.played+=min(consume,self.accepted-self.played)
            while self.blocks and self.blocks[0]<=self.played:self.blocks.popleft()
        self.last=now
        replies=[]
        while self.acks and self.acks[0][0]<=now:
            _,session,rid,accepted,played,free=self.acks.popleft()
            if not self.drop_acks:replies.append((session,rid,free,accepted,played))
        return replies

    def chunk(self,rid,points,now):
        if len(self.blocks)>=30:raise ValueError('Simulated DAC overflow')
        if len(self.acks)>=64:raise RuntimeError('simulated_ack_backpressure')
        self.accepted+=points;self.blocks.append(self.accepted)
        self.acks.append((now+self.delay,self.session,rid,self.accepted,self.played,30-len(self.blocks)))

    def restore(self):
        self.playing=False
        if self.simulate_restore_failure:raise RuntimeError('simulated_restore_failure')
        self.config=dict(self.original)

    def query(self):return 30-len(self.blocks),self.accepted,self.played


def _owner(control,audio,rf,events,progress,terminal,liveness,options):
    device=SimDevice(**options);last_control=0;epoch=0;session=0
    active=False;configured=False;generation=0;credits=None;held=None;offset=0;rid=0
    next_rf=time.monotonic();first=0;step=864/1600000
    stats=dict(chunks=0,acks=0,queries=0,rf_blocks=0,cancelled_audio=0,cancelled_acks=0,pumps=0)
    sent_at={};journal=RequestJournal()
    next_query=0.
    reason='shutdown';error=None;next_progress=0.
    try:
        events.put_nowait(dict(op='READY'))
        while True:
            now=time.monotonic();stats['pumps']+=1
            if not mp.parent_process().is_alive():
                reason='parent_lost';break
            if liveness.poll():
                try:liveness.recv_bytes()
                except EOFError:
                    reason='parent_disconnected';break
                raise ValueError('Unexpected liveness payload')
            for reply_session,*reply in device.pump(now):
                if not journal.acknowledge(reply[0],reply_session,epoch):
                    stats['cancelled_acks']+=1
                else:
                    credits.acknowledge(*reply);sent_at.pop(reply[0]);stats['acks']+=1
            if device.underrun:raise RuntimeError('simulated_audio_underrun')
            if sent_at and now-min(sent_at.values())>.5:raise RuntimeError('ACK_timeout')
            # Control queue remains usable even if audio/RF queues fill.
            try:command=control.get_nowait()
            except queue.Empty:command=None
            if command is not None:
                if command.sequence!=last_control+1:raise ValueError('Control sequence gap')
                last_control=command.sequence
                if command.op=='CONFIG':
                    if active or command.rate!=1600000:raise ValueError('CONFIG requires idle supported profile')
                    device.config.update(bits=8,rate=command.rate)
                    configured=True;generation+=1;next_rf=now
                elif command.op=='BEGIN':
                    if not configured or active or command.epoch<=epoch or command.session<=0 or command.rate!=40000:
                        raise ValueError('Invalid session transition')
                    epoch,session=command.epoch,command.session;active=True;offset=0;held=None
                    device.begin(command.rate,epoch,session);credits=Credits(30);sent_at.clear();next_query=now
                elif command.op=='PLAY':
                    if not active or command.epoch!=epoch or command.session!=session or credits.accepted<960:
                        raise ValueError('PLAY without confirmed prebuffer/session')
                    device.playing=True;device.last=now
                elif command.op=='STOP':
                    if command.epoch!=epoch or command.session!=session:raise ValueError('STOP session mismatch')
                    active=False;device.playing=False;held=None;journal.cancel();sent_at.clear()
                elif command.op=='SHUTDOWN':break
                else:raise ValueError('Unknown control command')
                events.put_nowait(dict(op=command.op,sequence=command.sequence,epoch=epoch,session=session,
                    generation=generation,rf_barrier=stats['rf_blocks']))
            if held is None:
                try:held=audio.get_nowait()
                except queue.Empty:pass
            if held is not None:
                if held.epoch<epoch or (not active and held.epoch==epoch):
                    stats['cancelled_audio']+=1;held=None
                elif held.epoch!=epoch or held.session!=session:
                    raise ValueError('Audio epoch/session mismatch')
                elif credits.available:
                    held.validate()
                    if held.offset!=offset:raise ValueError('Audio offset gap/repetition')
                    points=len(held.pcm)//2;rid=journal.reserve(epoch,session)
                    credits.reserve(rid,offset+points);sent_at[rid]=now;device.chunk(rid,points,now)
                    offset+=points;held=None;stats['chunks']+=1
            # Refresh confirmed device occupancy even with no chunk ACKs pending.
            # This is a synchronous simulated QUERY reply, never wall-time credit estimation.
            if active and not credits.pending and now>=next_query:
                credits.query(*device.query());stats['queries']+=1;next_query=now+.04
            burst=0
            # Bound work per turn; catch up on later turns without skipping RF.
            # Queue capacity, not an arbitrary scheduler-gap cutoff, bounds retention.
            while configured and now>=next_rf and burst<32:
                try:rf.put_nowait(Rf(first,864,bytes(864),generation,stats['rf_blocks']))
                except queue.Full:raise RuntimeError('rf_backpressure: no samples silently dropped')
                first=(first+864)&0xffffffff;stats['rf_blocks']+=1
                next_rf+=step;burst+=1
            if now>=next_progress:
                snapshot=dict(**stats,at=now,accepted=device.accepted,played=device.played,
                    pending=len(credits.pending) if credits else 0,playing=device.playing)
                try:progress.put_nowait(snapshot)
                except queue.Full:pass # Explicitly best-effort diagnostics only.
                next_progress=now+.02
            time.sleep(.0002)
    except BaseException as exc:
        reason='fault';error=repr(exc)
    finally:
        restoration_error=None
        try:device.restore()
        except BaseException as exc:
            restoration_error=repr(exc);reason='fault'
        orphaned=not mp.parent_process().is_alive()
        result=dict(reason=reason,error=error,restoration_error=restoration_error,
                    restored=restoration_error is None and device.config==device.original,
                    config=device.config,stats=stats,
                    output_policy='abandon_on_parent_loss' if orphaned else 'drain')
        try:terminal.send(result)
        except (BrokenPipeError,EOFError,OSError):orphaned=True
        finally:terminal.close();liveness.close()
        # Without a live parent there is no RF consumer: never wait forever on
        # queue feeder flush. Admitted RF may be abandoned, explicitly on loss.
        for output in (rf,events,progress):
            if orphaned:output.cancel_join_thread()
            output.close()
            if not orphaned:output.join_thread()



class Prototype:
    def __init__(self,rf_capacity=1024,ack_delay=.003,drop_acks=False,
                 simulate_disconnect=False,simulate_restore_failure=False,
                 _target=None,_options=None):
        if type(rf_capacity) is not int or not 1<=rf_capacity<=1024:raise ValueError('Invalid RF capacity')
        if not math.isfinite(ack_delay) or not 0<=ack_delay<.5:raise ValueError('Invalid simulated ACK delay')
        if any(type(value) is not bool for value in (drop_acks,simulate_disconnect,simulate_restore_failure)):
            raise ValueError('Invalid simulated fault option')
        ctx=mp.get_context('spawn')
        self.control=ctx.Queue(4);self.audio=ctx.Queue(48)
        self.rf=ctx.Queue(rf_capacity);self.events=ctx.Queue(8);self.progress=ctx.Queue(1)
        self.terminal,child=ctx.Pipe(duplex=False);self.sequence=0
        life_reader,self.liveness=ctx.Pipe(duplex=False)
        self.process=ctx.Process(target=_target or _owner,args=(self.control,self.audio,self.rf,
            self.events,self.progress,child,life_reader,_options if _options is not None else dict(ack_delay=ack_delay,drop_acks=drop_acks,
                simulate_disconnect=simulate_disconnect,simulate_restore_failure=simulate_restore_failure)))
        self.process.start();child.close();life_reader.close();self.closed_result=None

    def command(self,op,epoch=0,session=0,rate=None):
        if op not in ('CONFIG','BEGIN','PLAY','STOP','SHUTDOWN'):raise ValueError('Unknown command')
        if (type(epoch) is not int or not 0<=epoch<2**63 or
                type(session) is not int or not 0<=session<2**32):raise ValueError('Invalid command identity')
        resolved_rate=rate if rate is not None else 1600000 if op=='CONFIG' else 40000
        if type(resolved_rate) is not int or resolved_rate!=(1600000 if op=='CONFIG' else 40000):
            raise ValueError('Unsupported model rate')
        message=Control(self.sequence+1,op,epoch,session,resolved_rate)
        self.control.put(message,timeout=.5);self.sequence+=1

    def send_audio(self,message):
        message.validate()
        self.audio.put(message,timeout=.5)

    def close(self):
        if self.closed_result is not None:return self.closed_result
        if self.process.is_alive():self.command('SHUTDOWN')
        result=None;drained=[];cancelled=0;deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            for channel in (self.rf,self.events,self.progress,self.audio):
                for _ in range(64):
                    try:value=channel.get_nowait()
                    except queue.Empty:break
                    if channel is self.rf:drained.append(value)
                    elif channel is self.audio:cancelled+=1
            if result is None and self.terminal.poll():result=self.terminal.recv()
            if result is not None and not self.process.is_alive():break
            time.sleep(.001)
        if result is None or self.process.is_alive():
            self.process.terminate();self.process.join(2)
            raise RuntimeError('Sim owner did not confirm restoration')
        self.process.join()
        result['rf_drained_on_close']=drained;result['cancelled_input_audio_on_close']=cancelled
        for channel in (self.control,self.audio,self.rf,self.events,self.progress):
            channel.cancel_join_thread();channel.close()
        self.terminal.close();self.liveness.close()
        self.closed_result=result
        return result
