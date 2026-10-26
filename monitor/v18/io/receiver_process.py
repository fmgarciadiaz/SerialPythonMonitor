"""Spawned owner of the mature V18 receiver. No Qt imports or GUI callbacks.

RF and control confirmations share one FIFO; explicit batch credits bound RF.
A separate pipe carries the final outcome even when the FIFO is full.
"""
from contextlib import ExitStack
from collections import deque
from monitor.v18.flow_limits import FlowLimitExceeded
from dataclasses import replace
import multiprocessing as mp
import os
import queue
import time
import numpy as np

_flow_trace = None
if os.environ.get("MONITOR_V18_FLOW_TRACE"):
    from monitor.v18.io.flow_trace import record as _flow_trace


class RemotePcmSource:
    """Nonblocking DAC-code source. Rendering and gain happen in the parent."""
    live = True
    def __init__(self, descriptor, emit):
        self.__dict__.update(descriptor)
        self.session = descriptor['session']
        self.rate = descriptor.get('rate', 20000)
        self.length = descriptor.get('length', self.rate * 86400)
        self.emit = emit
        self.pending = None
        self.requested_at=None
        self.roundtrip_max_ms=0.
        self.stage_max_ms={}
        self.last_reply_timing=None
        self.delivery_max_ms={}
        self.slow_delivery=deque(maxlen=16)
        self.pending_levels = None
        self.ready = None
        self.last_dac_levels = None
        self.render_dac_codes = True  # receiver capability marker
    def __len__(self):
        return self.length
    def prepare_burst(self, start, chunk_points, credits):
        if getattr(self,'radio_audio',False):
            self._burst=(start,chunk_points,max(1,min(8,int(credits))))
    def try_codes(self, start, end, levels=None):
        key = (start, end)
        radio=getattr(self,'radio_audio',False)
        if self.ready is not None and (self.ready[:2] == key or
                (radio and self.ready[0]==start and end<=self.ready[1])):
            ready_start,ready_end,codes=self.ready
            result = codes[:end-start]
            self.ready = None if end==ready_end else (end,ready_end,codes[end-start:])
            self.pending = None
            self.last_dac_levels = self.ready_levels
            return result
        if radio and (self.pending is not None or self.ready is not None):return None
        if self.pending != key:
            request_end=end
            chunk_points=None
            burst=getattr(self,'_burst',None)
            if radio and burst is not None and burst[0]==start and end-start==burst[1]:
                chunk_points=burst[1]
                request_end=min(len(self),start+chunk_points*burst[2])
            self.pending = (start,request_end)
            self.pending_chunk_points=chunk_points
            self.pending_levels=(None if levels is None else tuple(float(np.asarray(value).reshape(-1)[-1]) for value in levels))
            if _flow_trace is not None:_flow_trace('pcm_child_request',f'pcm:{self.session}:{start}')
            self.requested_at=time.monotonic()
            self.emit({'type':'pcm_request', 'session':self.session,
                       'requested_at':self.requested_at,
                       'start':start, 'end':request_end, 'levels':levels,
                       'chunk_points':chunk_points,
                       'amplitude':None if levels is None else levels[0],
                       'offset':None if levels is None else levels[1]})
        return None
    def accept(self, session, offset, codes, timing=None):
        if session != self.session or self.pending is None or offset != self.pending[0]:
            return False
        accepted_at=time.monotonic()
        if self.requested_at is not None:
            self.roundtrip_max_ms=max(self.roundtrip_max_ms,(accepted_at-self.requested_at)*1000)
            if timing is not None:
                points=[self.requested_at]+[timing.get(k) for k in
                    ('parent_received_at','render_started_at','render_finished_at')]+[accepted_at]
                # Diagnostic metadata never changes PCM acceptance or credits.
                if all(isinstance(v,(int,float)) and np.isfinite(v) for v in points) and all(a<=b for a,b in zip(points,points[1:])):
                    stages=dict(zip(('request_to_parent','executor_wait','render','reply_to_child'),
                                    ((b-a)*1000 for a,b in zip(points,points[1:]))))
                    for name,ms in stages.items():self.stage_max_ms[name]=max(self.stage_max_ms.get(name,0.),ms)
                    self.last_reply_timing=dict(offset=offset,accepted_at=accepted_at,**stages)
        if codes is None:
            self.pending = None
            return False
        codes = np.asarray(codes)
        expected=self.pending[1]-offset
        chunk_points=getattr(self,'pending_chunk_points',None)
        prefix=(getattr(self,'radio_audio',False) and chunk_points is not None and
                0<len(codes)<=expected and len(codes)%chunk_points==0)
        if codes.ndim != 1 or codes.dtype != np.dtype('uint16') or (len(codes)!=expected and not prefix):
            raise ValueError('PCM remoto inválido')
        self.ready = (offset, offset + len(codes), codes)
        self.ready_levels = self.pending_levels
        return True
    def transport_snapshot(self, *, child_timing=None, detail=False):
        result = dict(pending=self.pending,
            pending_age_ms=(time.monotonic()-self.requested_at)*1000 if self.pending is not None and self.requested_at is not None else None,
            cached_samples=0 if self.ready is None else self.ready[1]-self.ready[0],
            roundtrip_max_ms=self.roundtrip_max_ms,
            stage_max_ms=dict(self.stage_max_ms),last_reply_timing=self.last_reply_timing,
            delivery_max_ms=dict(self.delivery_max_ms),slow_delivery=list(self.slow_delivery))
        if child_timing is not None:
            result['child_stages'] = child_timing.snapshot(detail=detail)
        return result
    def observe_transport(self,stage,seconds):
        ms=seconds*1000
        self.delivery_max_ms[stage]=max(self.delivery_max_ms.get(stage,0.),ms)
        if seconds>=.02:
            self.slow_delivery.append(dict(stage=stage,ms=ms,observed_at=time.monotonic()))
    def observe_status(self, status):
        pass


def wav_delivery_snapshot(receiver,now):
    inflight=getattr(receiver,'wav_inflight',{})
    oldest=min((entry[0] for entry in inflight.values()),default=None)
    status=getattr(receiver,'wav_status',None)
    return dict(inflight=len(inflight),oldest_inflight_ms=None if oldest is None else (now-oldest)*1000,
        inflight_kinds=[entry[1] for entry in inflight.values()],
        next_offset=getattr(receiver,'wav_next_offset',None),
        accepted=getattr(status,'accepted',None),played=getattr(status,'played',None),
        free_blocks=getattr(status,'free_blocks',None))


class ReceiverProcess:
    """Parent endpoint. ``release`` is mandatory after every consumed batch."""
    def __init__(self, port, mode, config, r4_port=None, initial_generator=None,
                 startup_gui_ack=False, connection_factory=None, receiver_factory=None,
                 max_batches=8, **options):
        ctx = mp.get_context('spawn')
        self.commands = ctx.Queue(32)
        self.pcm = ctx.Queue(8)
        self.events = ctx.Queue(32)
        self.pcm_requests = ctx.Queue(2)
        self.credits = ctx.Queue(max_batches * 2)
        self.terminal, terminal_child = ctx.Pipe(duplex=False)
        self.cancel = ctx.Event()
        self.process = ctx.Process(target=receiver_main, args=(
            dict(port=port,mode=mode,config=config,r4_port=r4_port,
                 initial_generator=initial_generator,startup_gui_ack=startup_gui_ack,
                 connection_factory=connection_factory,receiver_factory=receiver_factory,
                 max_batches=max_batches, **options),
            self.commands,self.pcm,self.events,self.credits,terminal_child,self.cancel,self.pcm_requests))
    def start(self):
        self.process.start()
        return self
    def submit(self, op, **payload):
        if op == 'shutdown':
            self.cancel.set()
            return
        (self.pcm if op == 'pcm' else self.commands).put_nowait(dict(op=op, **payload))
    def poll(self):
        result=[]
        while len(result)<64:
            try: result.append(self.events.get_nowait())
            except queue.Empty: break
        return result
    def release(self, batch_id):
        self.credits.put_nowait(batch_id)
        if _flow_trace is not None:_flow_trace("parent_credit_put",batch_id)
    def receive_pcm_request(self,timeout=.05):
        return self.pcm_requests.get(timeout=timeout)
    def poll_terminal(self):
        return self.terminal.recv() if self.terminal.poll() else None
    def close(self, timeout=60):
        self.cancel.set()
        self.process.join(timeout)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(1)
        return self.process.exitcode


def receiver_main(options, commands, pcm, events, credits, terminal, cancel, pcm_requests=None):
    from monitor.v18.receiver.unoq_config_receiver import OutputReceiver, _ChildStageTiming, _child_stage_timing_enabled
    from monitor.v18.receiver import unoq_wav as wav_protocol
    from monitor.v18.receiver.unoq_switch import Mode
    from monitor.v18.receiver.unoq_acquisition import UART_RATES
    from monitor.v18.io.rf_batch import RawRfBatch,CompactAdc8RfBatch,should_compact_adc8_ipc,take_rf_prefix
    from monitor.v18.wav_source import seek_playback
    parent = mp.parent_process()
    stack=ExitStack()
    receiver_activity=None
    receiver_activity_evidence=None
    receiver = None
    child_timing = _ChildStageTiming() if _child_stage_timing_enabled else None
    chunks=[]
    retained={}
    count=0
    ordinal=0
    last_flush=time.monotonic()
    current_mode=options['mode']
    current_r4=options.get('r4_port')
    config=options['config']
    compact_override=os.environ.get('MONITOR_V18_COMPACT_ADC8_IPC')
    compact_adc8_ipc=None if compact_override is None else compact_override=='1'
    published=False
    startup=not options['startup_gui_ack']
    source=None
    deferred=deque()
    origin=0
    source_path=None
    failure=None
    shutdown_ok=False
    closing=False
    lifecycle=None
    restoration={}
    generation=0
    deferred_failure=None
    failure_snapshot=None
    last_credit_monotonic=None
    wav_progress_key=None
    wav_progress_at=0.0
    def fail(error):
        nonlocal deferred_failure,failure_snapshot
        if deferred_failure is not None:return
        now=time.monotonic()
        retained_duration=sum(retained.values())
        buffered_duration=count/config.actual_rate
        failure_snapshot=dict(
            error=str(error),monotonic_s=now,wall_time_s=time.time(),
            retained_batches=[dict(id=batch_id,duration_s=duration) for batch_id,duration in retained.items()],
            retained_duration_s=retained_duration,buffered_samples=count,buffered_chunks=len(chunks),
            buffered_duration_s=buffered_duration,pending_duration_s=retained_duration+buffered_duration,
            actual_rate=config.actual_rate,bits=config.bits,
            last_credit_monotonic_s=last_credit_monotonic,
            last_credit_age_s=None if last_credit_monotonic is None else now-last_credit_monotonic)
        if hasattr(error,'details'):failure_snapshot['limit_details']=error.details
        if child_timing is not None:
            failure_snapshot['child_stages']=child_timing.snapshot(detail=True)
        if isinstance(source,RemotePcmSource):
            failure_snapshot['pcm_transport']=source.transport_snapshot()
        deferred_failure=error
    def emit(event):
        if closing or deferred_failure is not None:return
        destination=pcm_requests if pcm_requests is not None and event.get('type')=='pcm_request' else events
        try: destination.put_nowait(event)
        except queue.Full:
            fail(RuntimeError('FIFO del receptor V18 agotada; no se descartan eventos'))
    def signal(name,*args):
        emit(dict(type='signal',name=name,args=args))
    def tick(check=True):
        nonlocal startup,last_credit_monotonic
        if closing:return True
        while True:
            try:
                credit=credits.get_nowait()
                if _flow_trace is not None:_flow_trace("child_credit_recv",credit)
                retained.pop(credit,None)
                last_credit_monotonic=time.monotonic()
            except queue.Empty: break
        for _ in range(8):
            try: message=pcm.get_nowait()
            except queue.Empty: break
            if isinstance(source,RemotePcmSource):
                accepted=source.accept(message['session'],message['offset'],message.get('codes'),message.get('timing'))
                if _flow_trace is not None:
                    _flow_trace('pcm_child_accepted' if accepted else 'pcm_child_rejected',
                                f"pcm:{message['session']}:{message['offset']}")
        alive = not cancel.is_set() and (parent is None or parent.is_alive())
        if check and deferred_failure is not None:raise deferred_failure
        if check and not alive: raise InterruptedError('Receptor V18 detenido')
        return alive
    def flush(force=False):
        nonlocal chunks,count,last_flush,ordinal,deferred_failure
        # collect() has already serviced PCM/credits for each ADC frame. Do
        # not poll three IPC queues again when there is no batch to publish.
        if not chunks or (not force and time.monotonic()-last_flush<.02): return
        tick(False)
        if deferred_failure is not None:return
        if not force and len(retained)>=4: return
        if len(retained)>=options['max_batches']:
            fail(FlowLimitExceeded('Receptor DSP/GUI',dict(batches=len(retained)),
                dict(batches=len(retained)+1),dict(batches=options['max_batches']),['batches'],
                context=dict(bits=config.bits,channels=config.channels,actual_rate=config.actual_rate,generation=generation)))
            return
        ordinal+=1
        if force:
            prefix=chunks;remaining=[];sent_count=count
        else:
            # A stalled consumer must not turn the next credit into a giant
            # pickle/copy. Retain all remaining samples under the same 1 s cap.
            prefix,remaining,sent_count=take_rf_prefix(chunks,max(1,int(config.actual_rate*.04)))
        records=np.concatenate(prefix)
        published_at=time.monotonic()
        if should_compact_adc8_ipc(config,compact_adc8_ipc):
            block=CompactAdc8RfBatch.from_records(records,config,generation,ordinal,published_at)
        else:
            block=RawRfBatch(records,config,generation,ordinal,published_at)
        retained[ordinal]=len(block)/config.actual_rate
        emit(dict(type='batch',id=ordinal,batch=block))
        if _flow_trace is not None:_flow_trace('child_enqueue_batch',ordinal)
        chunks=remaining;count-=sent_count;last_flush=time.monotonic()
    def collect(samples):
        nonlocal count,deferred_failure
        tick(False)
        if not published or deferred_failure is not None:return
        array=samples.array if hasattr(samples,'array') else np.asarray(samples)
        chunks.append(array);count+=len(array)
        if sum(retained.values())+count/config.actual_rate>1.+1e-9:
            fail(FlowLimitExceeded('RF pendiente',dict(seconds=sum(retained.values())+(count-len(array))/config.actual_rate),
                dict(seconds=sum(retained.values())+count/config.actual_rate),dict(seconds=1.),['seconds'],
                context=dict(bits=config.bits,channels=config.channels,actual_rate=config.actual_rate,generation=generation,
                             buffered_samples_before=count-len(array),buffered_samples=count)))
            chunks.clear();count=0
            return
        flush()
    def configured(active):
        nonlocal config,generation
        flush(True)
        config=active;generation+=1
        signal('acquisition_confirmed',active.bits,active.rate)
    def generator(reply):
        flush(True);signal('generator_confirmed',reply)
    def wav(status):
        nonlocal wav_progress_key,wav_progress_at
        key=(status.session,int(status.state),status.reason,status.rate,status.rates_mask,status.queue_slots,origin)
        now=time.monotonic()
        # Every ACK still updates OutputReceiver credits immediately. Only GUI
        # progress notifications are coalesced; transitions remain ordered.
        if key==wav_progress_key and now-wav_progress_at<.05:return
        wav_progress_key=key;wav_progress_at=now
        transport=(source.transport_snapshot(child_timing=child_timing, detail=status.state==wav_protocol.State.UNDERRUN)
                   if isinstance(source,RemotePcmSource) else None)
        if transport is not None:transport['dac']=wav_delivery_snapshot(receiver,now)
        emit(dict(type='signal',name='wav_confirmed',args=(replace(status,played=status.played+origin,total=status.total+origin),),source_session=getattr(source,'session',None),
            pcm_transport=transport,
            status_observed_at=now))
    class PumpReceiver(OutputReceiver):
        def pump(self):
            if child_timing is None:
                return self._pump_global()
            return child_timing.pump('pump_global', self._pump_global)
        def _pump_global(self):
            tick()
            # A returned PCM chunk can be sent before another blocking read.
            # Keep refill independent of the next ADC/ACK packet arrival.
            self.service_wav()
            if getattr(self.connection,'socket',None) is not None:
                self.connection.socket.settimeout(.001 if isinstance(self.wav_codes,RemotePcmSource) else .01)
            return super().pump()
    if child_timing is not None:
        tick = child_timing.wrap('tick', tick)
        collect = child_timing.wrap('collect', collect)
        flush = child_timing.wrap('flush', flush)
        wav = child_timing.wrap('wav_callback', wav)
    try:
        from monitor.v18.process_activity import MacActivity,acquisition_activity_mode
        activity_mode=acquisition_activity_mode('receiver')
        if activity_mode!='off':
            # Explicit process scope, including restoration; no sleep settings.
            receiver_activity=stack.enter_context(MacActivity(activity_mode))
            receiver_activity_evidence=dict(pid=os.getpid(),mode=activity_mode,active=receiver_activity.active)
        factory=options.get('connection_factory')
        if factory is None:
            from monitor.v18.io.live_connection import installed_connection
            factory=lambda port: installed_connection(port,lambda text:signal('status_changed',text),lambda:tick(False))
        connection=stack.enter_context(factory(options['port']))
        if hasattr(connection,'socket'):connection.socket.settimeout(.01)
        cls=options.get('receiver_factory') or PumpReceiver
        receiver=cls(connection,collect,lambda text:signal('status_changed',text),lambda:tick(False))
        if child_timing is not None:
            receiver.child_stage_timing=child_timing
            receiver.service_wav=child_timing.wrap('wav_service',receiver.service_wav)
        receiver.decoder.numeric=True
        receiver.on_configuration=configured
        receiver.on_generator=generator
        receiver.on_wav=wav
        if options.get('connection_factory') is None or options.get('capture_lifecycle',False):
            from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
            lifecycle=ReceiverLifecycle(receiver,getattr(connection,'identity',{}),options.get('snapshot_dir'))
            receiver.on_configuration=lambda active:None
            receiver.on_generator=lambda reply:None
            receiver.on_wav=lambda status:None
            lifecycle.capture()
            receiver.on_configuration=configured
            receiver.on_generator=generator
            receiver.on_wav=wav
            if getattr(connection,'identity',None):signal('instrument_confirmed',connection.identity)
        def apply(mode,r4,active):
            nonlocal current_mode,current_r4
            if int(mode)==int(Mode.UART) and active.rate not in UART_RATES:
                raise ValueError('UART admite hasta 31,25 kHz')
            signal('switching',True)
            changed=receiver.configure(active)
            if not changed and not published:configured(active)
            receiver.select(Mode(mode),r4)
            current_mode=mode;current_r4=r4
            flush(True)
            signal('output_confirmed',int(mode),r4 if int(mode)==int(Mode.UART) else '')
            signal('switching',False)
        apply(options['mode'],options.get('r4_port'),config)
        if not startup:
            deadline=time.monotonic()+10
            while not startup:
                tick()
                if time.monotonic()>deadline:raise TimeoutError('GUI sin confirmar configuración inicial')
                try: message=commands.get_nowait()
                except queue.Empty:receiver.pump();continue
                if message['op']=='startup':startup=(message['bits'],message['rate'])==(config.bits,config.rate)
                else:
                    if len(deferred)>=32:raise RuntimeError('Cola de comandos inicial V18 agotada')
                    deferred.append(message)
        published=True
        if receiver.wav_candidate:receiver.reset_wav_output()
        receiver.generator(options.get('initial_generator'))
        while tick(False):
            tick()
            try: message=deferred.popleft() if deferred else commands.get_nowait()
            except queue.Empty:message=None
            if message:
                op=message['op']
                if op in ('output','configure'):
                    apply(message.get('mode',current_mode),message.get('r4_port',current_r4),message['config'])
                elif op=='generator':receiver.generator(message.get('config'))
                elif op=='levels':receiver.set_wav_levels(message['amplitude'],message['offset'])
                elif op=='seek':origin=seek_playback(receiver,source,origin,message['seconds'])
                elif op=='wav':
                    opcode=message['opcode'];codes=message.get('codes')
                    if opcode==1:
                        old_source=source
                        old_path=source_path
                        source_path=codes.get('path') if isinstance(codes,dict) and codes.get('kind')=='npy' else None
                        if isinstance(codes,dict):
                            codes=(np.load(codes['path'],mmap_mode='r',allow_pickle=False)
                                   if codes['kind']=='npy' else RemotePcmSource(codes,emit))
                        if getattr(codes,'radio_audio',False):
                            receiver.generator(replace(receiver.generator().active,enabled=0))
                        source=codes;origin=0
                    receiver.wav_request(opcode,codes,message.get('rate',20000))
                    if opcode==1:
                        if isinstance(old_source,RemotePcmSource):emit(dict(type='pcm_released',session=old_source.session))
                        if old_path is not None:emit(dict(type='wav_released',path=old_path))
                elif op!='startup':raise ValueError(f'Comando desconocido: {op}')
            elif receiver.wav_codes is None and receiver.wav_pending is None and time.monotonic()-receiver.last_generator_poll>=1:
                receiver.generator()
            else:receiver.pump()
            flush()
    except InterruptedError:
        if not cancel.is_set() and (parent is None or parent.is_alive()):failure='Recepción interrumpida'
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        try:emit(dict(type='error',text=failure))
        except Exception:pass
    finally:
        closing=True
        published=False
        if receiver is not None:
            try:
                if lifecycle is not None:
                    restoration=lifecycle.restore(recovery_seconds=options.get("recovery_seconds",10))
                    shutdown_ok=bool(restoration.get('hardware_restored',False))
                    if not shutdown_ok:failure=failure or '; '.join(restoration.get('errors',[])) or 'Restauración sin confirmar'
                else:
                    receiver.shutdown_output();shutdown_ok=True
            except Exception as exc:
                failure=failure or f'Apagado sin confirmar: {exc}'
            finally:
                try:
                    if lifecycle is None or lifecycle.snapshot is not None:receiver.close()
                except Exception as exc:
                    failure=failure or str(exc)
                    shutdown_ok=False
                    restoration['hardware_restored']=False
                    restoration.setdefault('errors',[]).append(f'Cierre del receptor: {exc}')
        try:stack.close()
        except Exception as exc:
            failure=failure or str(exc)
            shutdown_ok=False
            restoration['hardware_restored']=False
            restoration.setdefault('errors',[]).append(f'Cierre/transporte: {exc}')
        if receiver_activity_evidence is not None:
            receiver_activity_evidence['released']=not receiver_activity.active
            restoration['receiver_activity']=receiver_activity_evidence
        if lifecycle is not None:
            try:lifecycle.finalize(restoration)
            except Exception as exc:
                failure=failure or f'Evidencia final sin persistir: {exc}'
                shutdown_ok=False
                restoration['hardware_restored']=False
        terminal.send(dict(type='error' if failure else 'finished',text=failure,ok=failure is None,error=failure,shutdown_confirmed=shutdown_ok,failure_snapshot=failure_snapshot,**restoration))
        terminal.close()
        # Never wait for a stalled/dead parent to drain the event feeder.
        events.cancel_join_thread()
