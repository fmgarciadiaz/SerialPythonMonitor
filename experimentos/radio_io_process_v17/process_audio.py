"""Spawn integration of AudioPump, using ONLY the local simulated peer.

Optional synthetic RF/configuration shares the decoder; no real transport.
Reuses Prototype's bounded IPC, liveness pipe and draining/idempotent close.
"""
from dataclasses import dataclass,asdict
import multiprocessing as mp
import queue
import time
from experimentos.radio_io_process_v17.prototype import Prototype
from experimentos.radio_io_process_v17.audio_pump import AudioPump
from experimentos.radio_io_process_v17.local_transport import LocalTransport
from monitor.v17.receiver import unoq_wav as wav
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_generator import GeneratorConfig
from experimentos.radio_io_process_v17.acquisition_path import AcquisitionPath
from experimentos.radio_io_process_v17.socket_model_peer import SocketModelPeer
from experimentos.radio_io_process_v17.generator_path import GeneratorPath


@dataclass(frozen=True)
class SessionControl:
    sequence:int
    op:str
    epoch:int=0
    session:int=0
    rate:int=40000
    total:int=0
    configuration:object=None
    generator_config:object=None


def _audio_owner(control,audio,rf,events,progress,terminal,liveness,options):
    connected=options.get('connected')
    peer=(SocketModelPeer(connected) if connected is not None else
          LocalTransport(realtime=True,write_limit=options['write_limit'],rf_enabled=options['rf_enabled']))
    pump=AudioPump(peer,prebuffer=options['prebuffer'])
    path=AcquisitionPath(pump,rf,events) if options['rf_enabled'] else None
    generator=GeneratorPath(pump)
    def dispatch(kind,value):
        previous=generator.observed
        generator.event(kind,value)
        if generator.observed is not previous and mp.parent_process().is_alive():
            events.put_nowait(dict(op='GENERATOR_READBACK',request_id=value.request_id,
                                   config=value.active,running=value.running))
        if path is not None:path.event(kind,value)
    pump.on_event=dispatch
    if connected is not None:peer.bind(pump,path)
    sequence=0;held=None;shutdown=False;stop_requested=False;started=False;ready=False;next_progress=0.
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
                    if shutdown or stop_requested or generator.pending is not None or (path is not None and path.pending is not None):raise ValueError('BEGIN during shutdown/CONFIG')
                    if generator.observed is not None and (generator.observed.running or generator.observed.active.enabled):
                        raise ValueError('Known active generator; no experiment takeover')
                    pump.begin(command.epoch,command.session,command.total,command.rate,now)
                    started=True
                elif command.op in ('GEN_QUERY','GEN_SET'):
                    if shutdown or (path is not None and path.pending is not None):raise ValueError('Generator query during CONFIG/shutdown')
                    if command.op=='GEN_QUERY':generator.query(now)
                    else:generator.set_off(command.generator_config,now)
                elif command.op=='CONFIG':
                    if path is None or shutdown or stop_requested or generator.pending is not None:raise ValueError('RF configuration unavailable')
                    path.configure(command.configuration,now)
                elif command.op=='STOP':
                    if (command.epoch,command.session)!=(pump.control.epoch,pump.control.session):
                        raise ValueError('STOP identity mismatch')
                    stop_requested=True
                elif command.op=='SHUTDOWN':
                    shutdown=True
                    if pump.control.status is not None and (path is None or path.pending is None) and generator.pending is None:pump.stop(now)
                else:raise ValueError('Unknown process command')
                events.put_nowait(dict(op=command.op,sequence=sequence)) # Acceptance, not device ACK.
            if held is None:
                try:held=audio.get_nowait()
                except queue.Empty:pass
            if held is not None:
                if (held.epoch<pump.control.epoch or shutdown or stop_requested or pump.stop_at is not None or
                        pump.control.state in ('stop_wait','stopped')):
                    stats['cancelled_audio']+=1;held=None
                else:
                    if not started:raise ValueError('Audio before BEGIN')
                    try:pump.enqueue(held)
                    except queue.Full:pass # Retain exactly this block; never skip an offset.
                    else:stats['received']+=1;held=None
            generator.tick(now)
            if path is not None:path.tick(now)
            if ((shutdown or stop_requested) and pump.stop_at is None and pump.control.state!='stopped' and
                    pump.control.status is not None and (path is None or path.pending is None) and generator.pending is None):
                pump.stop(now)
            peer.advance(now);pump.turn(now)
            if path is not None:stats['rf_blocks']=path.emitted
            if not ready and pump.control.state=='ready' and (path is None or path.config is not None):
                events.put_nowait(dict(op='READY'));ready=True
            if pump.control.state=='stopped':
                stop_requested=False
                if shutdown:break
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
        if path is not None and not mp.parent_process().is_alive():path.publishing=False
        if path is not None and not pump.closed and path.pending is not None:
            try:
                deadline=time.monotonic()+pump.control.timeout
                while path.pending is not None and time.monotonic()<deadline:
                    now=time.monotonic();peer.advance(now);pump.turn(now);path.tick(now)
                if path.pending is not None:raise TimeoutError('Model CONFIG pending before STOP')
            except BaseException as exc:restoration_error=repr(exc)
        if generator.pending is not None and not pump.closed:
            try:
                deadline=time.monotonic()+pump.control.timeout
                while generator.pending is not None and time.monotonic()<deadline:
                    now=time.monotonic();peer.advance(now);pump.turn(now);generator.tick(now)
                if generator.pending is not None:raise TimeoutError('Generator query still pending')
            except BaseException as exc:restoration_error=repr(exc)
        # This is only a model stop. No dictionary/IDLE assignment is hardware restoration.
        # Try the real control path through the local peer, not a forced state reset.
        if not pump.closed and pump.control.status is not None and pump.control.state!='stopped':
            try:
                pump.stop(time.monotonic());deadline=time.monotonic()+pump.control.timeout
                while pump.control.state!='stopped' and time.monotonic()<deadline:
                    now=time.monotonic();peer.advance(now);pump.turn(now);time.sleep(.0002)
                if pump.control.state!='stopped':raise TimeoutError('Model STOP not confirmed')
            except BaseException as exc:restoration_error=repr(exc)
        if path is not None and not pump.closed:
            try:
                deadline=time.monotonic()+pump.control.timeout
                while path.pending is not None and time.monotonic()<deadline:
                    now=time.monotonic();peer.advance(now);pump.turn(now);path.tick(now)
                if path.pending is not None:raise TimeoutError('Model CONFIG still pending')
                if peer.config!=peer.original_config:
                    path.configure(peer.original_config,time.monotonic())
                    deadline=time.monotonic()+pump.control.timeout
                    while path.pending is not None and time.monotonic()<deadline:
                        now=time.monotonic();peer.advance(now);pump.turn(now);path.tick(now)
                    if path.pending is not None:raise TimeoutError('Model acquisition restore not confirmed')
            except BaseException as exc:restoration_error=repr(exc)
        generator_verified=False
        if generator.baseline is not None and not pump.closed and pump.control.state=='stopped':
            try:
                def await_generator():
                    deadline=time.monotonic()+pump.control.timeout
                    while generator.pending is not None and time.monotonic()<deadline:
                        now=time.monotonic();peer.advance(now);pump.turn(now);generator.tick(now)
                    if generator.pending is not None:raise TimeoutError('Generator final confirmation missing')
                if generator.observed.active!=generator.baseline:
                    generator.set_off(generator.baseline,time.monotonic());await_generator()
                # Separate QUERY after STOP/SET; an echoed SET is not final readback.
                generator.query(time.monotonic());await_generator()
                generator_verified=(generator.observed.active==generator.baseline and not generator.observed.running)
                if not generator_verified:raise RuntimeError('Final generator differs from initial baseline')
            except BaseException as exc:restoration_error=repr(exc)
        if path is not None:stats['rf_blocks']=path.emitted
        restored=(pump.control.state=='stopped' and peer.state==wav.State.IDLE and
                  peer.config==peer.original_config and (path is None or path.pending is None) and
                  restoration_error is None)
        if not restored:
            reason='fault'
            if restoration_error is None:restoration_error='Model STOP not confirmed; output uncertain'
        pump.close()
        orphaned=not mp.parent_process().is_alive()
        result=dict(reason=reason,error=error,restoration_error=restoration_error,
                    restored=restored,model_only=True,generator_verified=generator_verified,config=dict(generator=None if peer.state is None else peer.state!=wav.State.IDLE),
                    stats=stats,accepted=peer.accepted,played=peer.played,
                    cancelled_pcm=pump.cancelled_pcm,
                    output_policy='abandon_on_parent_loss' if orphaned else 'drain')
        if path is not None:
            observed_config=peer.config
            result['config'].update(bits=observed_config.bits if observed_config is not None else None,
                                    rate=observed_config.rate if observed_config is not None else None)
            result['abandoned_rf_blocks']=path.abandoned_blocks
        if generator.observed is not None:
            result['generator_readback']=asdict(generator.observed.active)
            result['generator_running']=generator.observed.running
        try:terminal.send(result)
        except (BrokenPipeError,EOFError,OSError):orphaned=True
        finally:terminal.close();liveness.close()
        for channel in (rf,events,progress):
            if orphaned:channel.cancel_join_thread()
            channel.close()
            if not orphaned:channel.join_thread()


class ProcessAudio(Prototype):
    def __init__(self,prebuffer=960,write_limit=992,rf_enabled=False,rf_capacity=1024,_connected=None):
        if type(prebuffer) is not int or not 1<=prebuffer<=30*480:raise ValueError('Invalid model prebuffer')
        if type(write_limit) is not int or not 1<=write_limit<=992:raise ValueError('Invalid write limit')
        if type(rf_enabled) is not bool:raise ValueError('Invalid RF option')
        super().__init__(rf_capacity=rf_capacity,_target=_audio_owner,
                         _options=dict(prebuffer=prebuffer,write_limit=write_limit,rf_enabled=rf_enabled,connected=_connected))
        if _connected is not None:_connected.close() # Child owns the only client descriptor after spawn.

    def command(self,op,epoch=0,session=0,rate=40000,total=0,configuration=None,generator_config=None):
        if op not in ('BEGIN','STOP','SHUTDOWN','CONFIG','GEN_QUERY','GEN_SET'):raise ValueError('Unsupported process command')
        if (type(epoch) is not int or not 0<=epoch<2**63 or type(session) is not int or
                not 0<=session<2**32 or type(total) is not int or not 0<=total<2**32 or type(rate) is not int or rate!=40000):
            raise ValueError('Invalid process command')
        if op=='CONFIG' and (not isinstance(configuration,Configuration) or configuration.bits!=14 or configuration.rate not in (40000,125000)):
            raise ValueError('Unsupported local RF model profile')
        if op=='GEN_SET' and (not isinstance(generator_config,GeneratorConfig) or generator_config.enabled):
            raise ValueError('Only OFF generator configurations allowed in this experiment')
        message=SessionControl(self.sequence+1,op,epoch,session,rate,total,configuration,generator_config)
        self.control.put(message,timeout=.5);self.sequence+=1


class ProcessSocketAudio(ProcessAudio):
    """Local-test fixture backend. Not an entrypoint for a physical Q.

    Transfers connected TCP socket to child and closes parent's copy on success.
    RF/generator baseline is known by the emulation fixture, not discovered.
    """
    def __init__(self,connected,prebuffer=960,rf_enabled=True,rf_capacity=1024):
        import socket
        if not isinstance(connected,socket.socket):raise TypeError('Connected fixture socket required')
        address=connected.getpeername()
        if connected.family!=socket.AF_INET or address[0]!='127.0.0.1':
            raise ValueError('Local fixture TCP connection required')
        super().__init__(prebuffer=prebuffer,rf_enabled=rf_enabled,rf_capacity=rf_capacity,_connected=connected)
