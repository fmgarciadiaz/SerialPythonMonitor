"""Spawn integration of AudioPump, using ONLY the local simulated peer.

RF/acquisition configuration and a real transport are not yet integrated.
Reuses Prototype's bounded IPC, liveness pipe and draining/idempotent close.
"""
from dataclasses import dataclass
import multiprocessing as mp
import queue
import time
from experimentos.radio_io_process_v17.prototype import Prototype
from experimentos.radio_io_process_v17.audio_pump import AudioPump
from experimentos.radio_io_process_v17.local_transport import LocalTransport
from monitor.v17.receiver import unoq_wav as wav


@dataclass(frozen=True)
class SessionControl:
    sequence:int
    op:str
    epoch:int=0
    session:int=0
    rate:int=40000
    total:int=0


def _audio_owner(control,audio,rf,events,progress,terminal,liveness,options):
    peer=LocalTransport(realtime=True,write_limit=options['write_limit'])
    pump=AudioPump(peer,prebuffer=options['prebuffer'])
    sequence=0;held=None;shutdown=False;started=False;ready=False;next_progress=0.
    reason='shutdown';error=None;restoration_error=None
    stats=dict(rf_blocks=0,received=0,cancelled_audio=0,pumps=0)
    try:
        while True:
            now=time.monotonic();stats['pumps']+=1
            if not mp.parent_process().is_alive():reason='parent_lost';break
            if liveness.poll():
                try:liveness.recv_bytes()
                except EOFError:reason='parent_disconnected';break
                raise ValueError('Unexpected liveness payload')
            try:command=control.get_nowait()
            except queue.Empty:command=None
            if command is not None:
                if command.sequence!=sequence+1:raise ValueError('Control sequence gap')
                sequence=command.sequence
                if command.op=='BEGIN':
                    if shutdown:raise ValueError('BEGIN after shutdown')
                    pump.begin(command.epoch,command.session,command.total,command.rate,now)
                    started=True
                elif command.op=='STOP':
                    if (command.epoch,command.session)!=(pump.control.epoch,pump.control.session):
                        raise ValueError('STOP identity mismatch')
                    pump.stop(now)
                elif command.op=='SHUTDOWN':
                    shutdown=True
                    if pump.control.status is not None:pump.stop(now)
                else:raise ValueError('Unknown process command')
                events.put_nowait(dict(op=command.op,sequence=sequence)) # Acceptance, not device ACK.
            if held is None:
                try:held=audio.get_nowait()
                except queue.Empty:pass
            if held is not None:
                if (held.epoch<pump.control.epoch or shutdown or pump.stop_at is not None or
                        pump.control.state in ('stop_wait','stopped')):
                    stats['cancelled_audio']+=1;held=None
                else:
                    if not started:raise ValueError('Audio before BEGIN')
                    try:pump.enqueue(held)
                    except queue.Full:pass # Retain exactly this block; never skip an offset.
                    else:stats['received']+=1;held=None
            peer.advance(now);pump.turn(now)
            if not ready and pump.control.state=='ready':
                events.put_nowait(dict(op='READY'));ready=True
            if shutdown and pump.control.state=='stopped':break
            if now>=next_progress:
                row=dict(**stats,at=now,state=pump.control.state,epoch=pump.control.epoch,
                         accepted=peer.accepted,played=peer.played,queued_pcm=len(pump.pcm),
                         pending=len(pump.control.pending),frames=peer.frame_count)
                try:progress.put_nowait(row)
                except queue.Full:pass
                next_progress=now+.02
            time.sleep(.0002)
    except BaseException as exc:reason='fault';error=repr(exc)
    finally:
        # This is only a model stop. No dictionary/IDLE assignment is hardware restoration.
        # Try the real control path through the local peer, not a forced state reset.
        if not pump.closed and pump.control.status is not None and pump.control.state!='stopped':
            try:
                pump.stop(time.monotonic());deadline=time.monotonic()+pump.control.timeout
                while pump.control.state!='stopped' and time.monotonic()<deadline:
                    now=time.monotonic();peer.advance(now);pump.turn(now);time.sleep(.0002)
                if pump.control.state!='stopped':raise TimeoutError('Model STOP not confirmed')
            except BaseException as exc:restoration_error=repr(exc)
        restored=pump.control.state=='stopped' and peer.state==wav.State.IDLE
        if not restored:
            reason='fault'
            if restoration_error is None:restoration_error='Model STOP not confirmed; output uncertain'
        pump.close()
        orphaned=not mp.parent_process().is_alive()
        result=dict(reason=reason,error=error,restoration_error=restoration_error,
                    restored=restored,model_only=True,config=dict(generator=peer.state!=wav.State.IDLE),
                    stats=stats,accepted=peer.accepted,played=peer.played,
                    cancelled_pcm=pump.cancelled_pcm,
                    output_policy='abandon_on_parent_loss' if orphaned else 'drain')
        try:terminal.send(result)
        except (BrokenPipeError,EOFError,OSError):orphaned=True
        finally:terminal.close();liveness.close()
        for channel in (rf,events,progress):
            if orphaned:channel.cancel_join_thread()
            channel.close()
            if not orphaned:channel.join_thread()


class ProcessAudio(Prototype):
    def __init__(self,prebuffer=960,write_limit=992):
        if type(prebuffer) is not int or not 1<=prebuffer<=30*480:raise ValueError('Invalid model prebuffer')
        if type(write_limit) is not int or not 1<=write_limit<=992:raise ValueError('Invalid write limit')
        super().__init__(_target=_audio_owner,_options=dict(prebuffer=prebuffer,write_limit=write_limit))

    def command(self,op,epoch=0,session=0,rate=40000,total=0):
        if op not in ('BEGIN','STOP','SHUTDOWN'):raise ValueError('Unsupported process command')
        if (type(epoch) is not int or not 0<=epoch<2**63 or type(session) is not int or
                not 0<=session<2**32 or type(total) is not int or not 0<=total<2**32 or type(rate) is not int or rate!=40000):
            raise ValueError('Invalid process command')
        message=SessionControl(self.sequence+1,op,epoch,session,rate,total)
        self.control.put(message,timeout=.5);self.sequence+=1
