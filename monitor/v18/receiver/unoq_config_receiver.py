"""V18 receiver: permanent Q control, configurable ADC/DAC and confirmed SPI/UART output."""
import os
from collections import deque
from functools import wraps
_flow_trace=None
if os.environ.get("MONITOR_V18_FLOW_TRACE"):
    from monitor.v18.io.flow_trace import record as _flow_trace
import numpy as np
import queue
import secrets
import struct
import threading
import time

from monitor.v18.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.v18.receiver.unoq_generator import generator_request, GeneratorConfig
from monitor.v18.receiver import unoq_wav as wav
from monitor.v18.receiver.unoq_acquisition import Configuration, acquisition_request
from monitor.v18.receiver.unoq_switch import Mode, Phase, switch_request
from monitor.v18.receiver.unoq_control import status_request
from monitor.v18.receiver.unoq_usb import MASK, ProtocolError


_child_stage_timing_enabled = os.environ.get("MONITOR_V18_CHILD_STAGE_TIMING") == "1"


class _ChildStageTiming:
    """Opt-in scalar diagnostics. No RF arrays, files, or transport callbacks.

    The bounded ring retains slow stages and every WAV send/ACK for three
    seconds. Open stages matter: UNDERRUN is notified inside decoder events,
    before the surrounding pump/events timers can finish.
    """
    def __init__(self):
        if not hasattr(time, 'thread_time'):
            raise RuntimeError('MONITOR_V18_CHILD_STAGE_TIMING requiere Python con time.thread_time')
        self.events = deque(maxlen=1024)
        self.max_ms = {}
        self.active = []
        self.bytes_read = 0
        self.read_bytes_max = 0
        self._pump_depth = 0
        self._pump_ended = None

    def _observe(self, stage, start, end, cpu_seconds=None, **details):
        wall_ms = max(0., end-start)*1000
        cpu_ms = None if cpu_seconds is None else max(0., cpu_seconds)*1000
        maxima = self.max_ms.setdefault(stage, dict(wall=0., cpu=0.))
        maxima['wall'] = max(maxima['wall'], wall_ms)
        if cpu_ms is not None:
            maxima['cpu'] = max(maxima['cpu'], cpu_ms)
        size = details.get('bytes_read')
        if size is not None:
            self.bytes_read += size
            self.read_bytes_max = max(self.read_bytes_max, size)
        self._prune(end)
        if wall_ms > 5. or stage in ('send', 'ack'):
            self.events.append(dict(stage=stage, start=start, end=end,
                                    wall_ms=wall_ms, cpu_ms=cpu_ms, **details))

    def _prune(self, now):
        while self.events and self.events[0]['end'] < now-3.:
            self.events.popleft()

    def begin(self, stage):
        token = (stage, time.monotonic(), time.thread_time())
        self.active.append(token)
        return token

    def end(self, token):
        end, cpu_end = time.monotonic(), time.thread_time()
        self.active.pop()
        self._observe(token[0], token[1], end, cpu_end-token[2])
        return end, cpu_end

    def call(self, stage, callback, *args, **kwargs):
        token = self.begin(stage)
        try:
            return callback(*args, **kwargs)
        finally:
            self.end(token)

    def wrap(self, stage, callback):
        @wraps(callback)
        def timed(*args, **kwargs):
            return self.call(stage, callback, *args, **kwargs)
        return timed

    def pump(self, stage, callback):
        outermost = self._pump_depth == 0
        token = self.begin(stage)
        if outermost and self._pump_ended is not None:
            self._observe('pump_gap', self._pump_ended[0], token[1],
                          token[2]-self._pump_ended[1])
        self._pump_depth += 1
        try:
            return callback()
        finally:
            self._pump_depth -= 1
            ended = self.end(token)
            if outermost:
                self._pump_ended = ended

    def snapshot(self, detail=False):
        result = dict(max_ms={stage: dict(values) for stage, values in self.max_ms.items()},
                      bytes_read=self.bytes_read, read_bytes_max=self.read_bytes_max)
        if detail:
            now, cpu_now = time.monotonic(), time.thread_time()
            self._prune(now)
            result.update(observed_at=now, events=[dict(event) for event in self.events],
                          active=[dict(stage=stage, began_at=start,
                                       wall_ms=max(0., now-start)*1000,
                                       cpu_ms=max(0., cpu_now-cpu_start)*1000)
                                  for stage, start, cpu_start in self.active])
        return result


class LegacyDecoder:
    """Strict DATA reader. Only the initial incomplete packet may be skipped."""
    def __init__(self, config=Configuration()):
        self.config = config
        self.buffer = bytearray()
        self.locked = False
        self.skipped = 0

    def feed(self, data):
        self.buffer.extend(data)
        batches = []
        while len(self.buffer) >= 7:
            if not self.locked:
                start = self.buffer.find(b'DATA')
                skip = start if start >= 0 else max(0, len(self.buffer)-3)
                self.skipped += skip
                del self.buffer[:skip]
                if self.skipped > 4102:
                    raise ProtocolError('R4: demasiados bytes sin cabecera DATA')
                if len(self.buffer) < 7:
                    break
            if self.buffer[:4] != b'DATA' or struct.unpack_from('<BH', self.buffer, 4) != (1, 512):
                raise ProtocolError('R4: cabecera DATA inválida o pérdida de sincronización')
            if len(self.buffer) < 4103:
                break
            records = list(struct.iter_unpack('<IHH', self.buffer[7:4103]))
            if any(a > self.config.maximum or b > self.config.maximum for _, a, b in records):
                raise ProtocolError('R4: muestra fuera del rango de 14 bits')
            if any((b[0]-a[0])&MASK != self.config.period for a, b in zip(records, records[1:])):
                raise ProtocolError('R4: timestamps discontinuos dentro de DATA')
            batches.append(records)
            self.locked = True
            del self.buffer[:4103]
        return batches


class R4Reader:
    def __init__(self, path, config):
        import serial
        self.path = path
        self.config = config
        self.port = serial.Serial(path, 3000000, timeout=0.05)
        self.batches = queue.Queue(maxsize=128)
        self.error = None
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        decoder = LegacyDecoder(self.config)
        try:
            while not self.stopping.is_set():
                for records in decoder.feed(self.port.read(self.port.in_waiting or 1)):
                    self.batches.put_nowait(records)
        except Exception as exc:
            if not self.stopping.is_set():
                self.error = exc

    def drain(self):
        if self.error:
            raise self.error
        records = []
        while True:
            try:
                records.extend(self.batches.get_nowait())
            except queue.Empty:
                return records

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=1)
        self.port.close()


R4_BOOT_SECONDS = 3


class OutputReceiver:
    def __init__(self, connection, on_samples, on_status=lambda text: None,
                 running=lambda: True, reader_factory=R4Reader):
        self.connection = connection
        self.on_samples = on_samples
        self.on_status = on_status
        self.running = running
        self.reader_factory = reader_factory
        self.decoder = ConfigurationDecoder()
        self.config = Configuration()
        self.config_pending = None
        self.config_applied = None
        self.on_configuration = lambda config: None
        self.on_generator = lambda reply: None
        self.generator_pending = None
        self.generator_applied = None
        self.last_generator_poll = time.monotonic()
        self.on_wav = lambda status: None
        self.wav_status = None
        self.wav_pending = None
        self.wav_inflight = {}
        self.wav_live_credits = 2 # Experimental override; keep production window.
        self.wav_chunk_points = wav.CHUNK # Explicit paired experimental firmware only.
        self.transport_trace = None # Opt-in bounded diagnostic; no wire changes.
        self.child_stage_timing = _ChildStageTiming() if _child_stage_timing_enabled else None
        self.startup_trace = None # Optional milestone callback, never sample I/O.
        self.wav_next_offset = 0
        self.wav_low_ack = None
        self.wav_low_episode = False
        self.wav_levels = None
        self.wav_previous_levels = None
        self.wav_codes = None
        self.wav_session = 0
        self.wav_poll_at = 0
        self.wav_buffer_adjust_at = time.monotonic()
        self.wav_rate = 20000
        self.wav_started = False
        self.wav_candidate = (os.environ.get("MONITOR_V18_WAV_FIRMWARE", "v18") == "v18"
                              or getattr(connection, "wav_firmware", False) is True)
        self.r4 = None
        self.mode = None
        self.next_index = None
        self.timestamp = None
        self.pending = None
        self.applied = None
        self.uart_end = None
        self.spi_waiting = []
        self.visible = False
        self.last_samples = time.monotonic()
        self.next_id = 0x80000000 + secrets.randbelow(0x7fffffff)
        self.ping = None
        self.last_ping = time.monotonic()

    def _id(self):
        rid = self.next_id
        self.next_id = 0x80000000 if rid == 0xfffffffe else rid+1
        return rid

    def _emit(self, records, *, validated_spi=False):
        if not records:
            return
        period=self.config.period
        if validated_spi:
            # Only decoder-produced SPI batches enter here. The decoder checks
            # the wire boundary and derives every interior timestamp/index.
            # Still validate the receiver's boundary, including uint32 wrap.
            first=records[0];last=records[-1]
            if first[3]!=self.next_index or last[3]!=((first[3]+len(records)-1)&MASK):
                raise ProtocolError(f'Índice discontinuo al cambiar el destino: esperado {self.next_index}, recibido {int(first[3])}, último {int(last[3])}, count {len(records)}')
            if ((self.timestamp is not None and (first[0]-self.timestamp)&MASK!=period)
                    or ((last[0]-first[0])&MASK)!=(((len(records)-1)*period)&MASK)):
                raise ProtocolError('Pérdida o repetición de muestras entre Q y R4')
            self.timestamp=last[0]
            self.next_index=(last[3]+1)&MASK
            self.last_samples=time.monotonic()
            if self.visible:self.on_samples(records)
            return
        for timestamp, a, b, index in records:
            if index != self.next_index:
                raise ProtocolError('Índice discontinuo al cambiar el destino')
            if self.timestamp is not None and (timestamp-self.timestamp)&MASK != period:
                raise ProtocolError('Pérdida o repetición de muestras entre Q y R4')
            self.timestamp = timestamp
            self.next_index = (index+1)&MASK
        self.last_samples = time.monotonic()
        if self.visible:
            self.on_samples(records)

    def _reply(self, reply):
        if self.pending is None or reply.request_id != self.pending[0]:
            return
        if reply.requested != self.pending[1]:
            raise ProtocolError('El Q respondió para otro destino')
        if reply.phase == Phase.REJECTED:
            raise RuntimeError(f'El Q rechazó el destino: {reply.reason.name}')
        if reply.phase != Phase.APPLIED:
            return
        self.applied = reply
        if self.mode is None:
            self.mode = reply.active
            self.next_index = reply.boundary
        elif self.mode == Mode.SPI:
            if self.next_index != reply.boundary:
                raise ProtocolError('La frontera APPLIED no coincide con el final de SPI')
            self.mode = reply.active
        elif reply.active == Mode.SPI:
            self.uart_end = reply.boundary
            self._finish_uart()

    def _finish_uart(self):
        if self.uart_end is not None and self.next_index == self.uart_end:
            self.mode = Mode.SPI
            self.uart_end = None
            waiting, self.spi_waiting = self.spi_waiting, []
            self._emit(waiting)

    def _uart(self):
        if self.r4 is None:
            return
        # Data may beat APPLIED over the two independent USB paths. Keep it
        # queued until the matching reply assigns its first absolute index.
        if self.mode == Mode.SPI and self.pending and self.pending[1] == Mode.UART:
            return
        records = self.r4.drain()
        if self.mode != Mode.UART:
            return
        indexed = []
        index = self.next_index
        for timestamp, a, b in records:
            if self.uart_end is not None and index == self.uart_end:
                raise ProtocolError('R4 entregó muestras después de la frontera SPI')
            indexed.append((timestamp, a, b, index))
            index = (index+1)&MASK
        self._emit(indexed)
        self._finish_uart()

    def _process_decoder_events(self):
        for kind, value in self.decoder.events:
            if kind == 'wav':
                if value.request_id not in self.wav_inflight:
                    continue
                if self.wav_codes is not None and value.session != self.wav_session:
                    raise ProtocolError('ACK WAV para otra sesión')
                if self.wav_codes is not None and value.rate != self.wav_rate:
                    raise ProtocolError("Tasa WAV distinta de la solicitada")
                self.wav_status = value
                self._trace_transport('ack',time.monotonic(),time.monotonic(),value.request_id)
                if hasattr(self.wav_codes,'observe_transport'):
                    self.wav_codes.observe_transport('send_to_ack',time.monotonic()-self.wav_inflight[value.request_id][0])
                del self.wav_inflight[value.request_id]
                self.wav_pending = next(((rid,entry[0]) for rid,entry in self.wav_inflight.items()),None)
                self.on_wav(value)
                if value.reason or value.state in (wav.State.DONE, wav.State.UNDERRUN, wav.State.FAULT):
                    self.wav_codes = None
                    self.wav_inflight.clear();self.wav_pending=None
                # Refill immediately after the ACK, before converting ADC batches.
                self.service_wav()
            elif kind == 'generator':
                if self.generator_pending and value.request_id == self.generator_pending[0]:
                    wanted = self.generator_pending[1]
                    if value.phase == Phase.REJECTED:
                        self.generator_applied = value
                    elif value.phase == Phase.APPLIED:
                        if wanted is not None and value.active != wanted:
                            raise ProtocolError('ACK de otro generador')
                        self.generator_applied = value
                    self.on_generator(value)
                elif value.phase == Phase.APPLIED:
                    self.on_generator(value)
            elif kind == 'configuration':
                if self.config_pending and value.request_id == self.config_pending[0]:
                    if value.requested_bits != self.config_pending[1].bits or value.requested_period != self.config_pending[1].request_period:
                        raise ProtocolError('ACK de otra configuración')
                    if value.phase == Phase.REJECTED: raise RuntimeError(f'Q rechazó adquisición: {value.reason.name}')
                    if value.phase == Phase.APPLIED:
                        self.config = value.active
                        self.next_index = 0; self.timestamp = None
                        self.config_applied = value
                        self.last_samples = time.monotonic()
                        self.on_configuration(value.active)
            elif kind == 'reply':
                self._reply(value)
            elif self.mode is not None:
                if self.uart_end is not None:
                    self.spi_waiting.extend(value)
                elif self.mode == Mode.SPI:
                    self._emit(value,validated_spi=kind=='samples')
                else:
                    raise ProtocolError('Muestras SPI mientras el destino es R4')

        # Reuse confirmed credits between ADC frames, under unchanged tokens
        # and limits. ADC8/88 is an explicitly private qualification candidate.
        private8=(self.config.bits==8 and getattr(self.config,'channels',None)==1
                  and getattr(self.config,'period',None)==88
                  and getattr(self.config,'node_pairs',None)==3488)
        if ((self.config.bits==10 and self.config.rate==1250000 or private8)
                and getattr(self.wav_codes,'radio_audio',False)):
            self.service_wav()

    def pump(self):
        timing = self.child_stage_timing
        if timing is None:
            return self._pump()
        return timing.pump('pump', self._pump)

    def _pump(self):
        if not self.running():
            raise InterruptedError('Recepción detenida')
        self._uart()
        cpu_start=time.thread_time() if self.transport_trace is not None or self.child_stage_timing is not None else None
        process_start=time.process_time() if self.transport_trace is not None else None
        began=time.monotonic();data=self.connection.read()
        self._trace_transport('read',began,time.monotonic(),cpu_seconds=(time.thread_time()-cpu_start) if cpu_start is not None else None,process_cpu_seconds=(time.process_time()-process_start) if process_start is not None else None,bytes_read=len(data))
        # Bound ADC decoding ahead of an audio ACK to one wire frame.
        # Preserve every event in wire order, including configuration boundaries.
        stride=992 if getattr(self.wav_codes,'live',False) or isinstance(self.wav_codes,np.ndarray) else max(1,len(data))
        statuses=[]
        for offset in range(0,max(1,len(data)),stride):
            cpu_start=time.thread_time() if self.transport_trace is not None or self.child_stage_timing is not None else None
            process_start=time.process_time() if self.transport_trace is not None else None
            began=time.monotonic();self.decoder.feed(data[offset:offset+stride],collect_samples=False)
            self._trace_transport('decode',began,time.monotonic(),cpu_seconds=(time.thread_time()-cpu_start) if cpu_start is not None else None,process_cpu_seconds=(time.process_time()-process_start) if process_start is not None else None)
            statuses.extend(self.decoder.statuses)
            if self.child_stage_timing is None:
                self._process_decoder_events()
            else:
                self.child_stage_timing.call('decoder_events', self._process_decoder_events)
        self.decoder.statuses=statuses
        self._uart()
        self.service_wav()
        if self.config_pending is None and self.decoder.config is not None:
            self.config = self.decoder.config
        current = time.monotonic()
        if self.ping is not None:
            if any(status['ack'] == self.ping[0] for status in self.decoder.statuses):
                self.ping = None
                self.last_ping = current
            elif current-self.ping[1] > 2:
                raise TimeoutError('El Q dejó de confirmar el control')
        if self.pending is None and self.config_pending is None and self.generator_pending is None and self.ping is None and current-self.last_ping >= 1:
            rid = self._id()
            self.connection.socket.sendall(status_request(rid))
            self.ping = (rid, current)
        if self.visible and self.pending is None and self.config_pending is None and current-self.last_samples > self.config.sample_timeout:
            raise TimeoutError('El destino dejó de entregar muestras')

    def _switch(self, mode):
        # A priority type-5 reply can replace the frame that would echo PING.
        # Switch acknowledgements prove control during this interval; resume
        # periodic PING with a fresh nonce after the command completes.
        self.ping = None
        self.last_ping = time.monotonic()
        rid = self._id()
        self.pending = (rid, mode)
        self.applied = None
        self.on_status('Esperando confirmación del Q…')
        self.connection.socket.sendall(switch_request(rid, mode))
        deadline = time.monotonic()+3
        try:
            while time.monotonic() < deadline:
                self.pump()
                if self.applied is not None and self.uart_end is None:
                    return self.applied
            raise TimeoutError('Sin APPLIED o faltan muestras de frontera; destino incierto')
        finally:
            self.pending = None

    def select(self, mode, r4_path=None):
        mode = Mode(mode)
        if mode == Mode.UART and self.config.rate > 31250:
            raise ValueError('UART admite hasta 31,25 kHz; reducir la tasa antes de cambiar salida')
        if mode == Mode.UART and not r4_path:
            raise ValueError('Seleccionar el puerto USB del R4')
        # Establish a known SPI boundary even if a previous client left UART
        # active. A fresh connection starts a new capture, not a false merge.
        if self.mode is None:
            self._switch(Mode.SPI)
        if self.mode == mode and (mode == Mode.SPI or self.r4.path == r4_path):
            self.visible = True
            return self.applied
        if self.mode == Mode.UART:
            self._switch(Mode.SPI)
        if self.r4 is not None:
            self.r4.close()
            self.r4 = None
        if mode == Mode.UART:
            self.on_status('Preparando el R4…')
            self.r4 = self.reader_factory(r4_path, self.config)
            # Opening USB can reset R4. Keep receiving SPI during its reboot.
            end = time.monotonic()+R4_BOOT_SECONDS
            while time.monotonic() < end:
                self.pump()
            self.r4.drain()
            self._switch(Mode.UART)
        self.visible = True
        self.last_samples = time.monotonic()
        return self.applied

    def _startup_event(self, event, **details):
        callback=self.startup_trace
        if callback is not None:callback(event,**details)

    def configure(self, config):
        if self.mode is not None and config == self.config:
            self._startup_event('configure_noop')
            return False
        if config._native and config._native.get('integrity_only'):
            connected = self.mode is not None
            settle_seconds = .5 if connected else 2.0
            if self.mode is None: self.select(Mode.SPI)
            self.on_status('Preparando 1,60 MHz…')
            # Acquisition changes must not rewrite DAC levels, frequency or
            # playback state. The preparation only changes the ADC transport.
            samples, confirmed = self.on_samples, self.on_configuration
            try:
                self.on_samples = lambda rows: None
                self.on_configuration = lambda active: None
                # Governor/affinity setup can stall the relay while the old
                # profile is still producing. Drain that high-rate epoch first,
                # using the same low-load entry as physical qualification.
                self._startup_event('preparation_14_40000_begin')
                self._configure_once(Configuration(14, 40000))
                self._startup_event('preparation_14_40000_end')
                self._startup_event('preparation_8_1428571_begin')
                self._configure_once(Configuration(8, 1428571))
                self._startup_event('preparation_8_1428571_end')
                self._startup_event('settle_2s_begin',seconds=settle_seconds,connected=connected)
                end = time.monotonic() + settle_seconds
                while time.monotonic() < end:
                    self.pump()
                self._startup_event('settle_2s_end',seconds=settle_seconds,connected=connected)
                def final_configuration(active):
                    # A read may contain APPLIED followed by target samples.
                    # Publish the boundary first, then admit those samples in
                    # this same pump instead of waiting for configure to return.
                    self._startup_event('target_applied',bits=active.bits,rate=active.rate)
                    confirmed(active)
                    self.on_samples = samples
                    self.on_configuration = confirmed
                self.on_configuration = final_configuration
                self._startup_event('target_request',bits=config.bits,rate=config.rate)
                return self._configure_once(config)
            finally:
                self.on_samples, self.on_configuration = samples, confirmed
        if (self.config.actual_rate>400000 and config.actual_rate>400000
                and self.config!=config
                and ((self.config._native or {}).get('optimized_transport') or (config._native or {}).get('optimized_transport'))):
            samples,confirmed=self.on_samples,self.on_configuration
            try:
                self.on_samples=lambda rows:None
                self.on_configuration=lambda active:None
                self._startup_event('high_rate_bridge_begin')
                self._configure_once(Configuration(14,40000))
                end=time.monotonic()+.15
                while time.monotonic()<end:self.pump()
                self._startup_event('high_rate_bridge_end')
                def applied(active):
                    confirmed(active)
                    self.on_samples=samples
                    self.on_configuration=confirmed
                self.on_configuration=applied
                return self._configure_once(config)
            finally:
                self.on_samples,self.on_configuration=samples,confirmed
        return self._configure_once(config)

    def _configure_once(self, config):
        if self.mode is None: self.select(Mode.SPI)
        if config == self.config: return False
        self.select(Mode.SPI)
        self.ping = None; self.last_ping = time.monotonic()
        rid = self._id()
        self.config_pending = (rid, config)
        self.config_applied = None
        self.connection.socket.sendall(acquisition_request(rid, config))
        deadline = time.monotonic()+max(3, 4096/self.config.rate+1)
        try:
            while time.monotonic() < deadline:
                self.pump()
                if self.config_applied is not None: return True
            raise TimeoutError('El Q no confirmó la configuración aplicada')
        finally:
            self.config_pending = None

    def generator(self, config=None):
        self.ping = None
        self.last_ping = time.monotonic()
        rid = self._id()
        self.generator_pending = (rid, config)
        self.generator_applied = None
        self.connection.socket.sendall(generator_request(rid, config))
        deadline = time.monotonic()+3
        try:
            while time.monotonic() < deadline:
                self.pump()
                if self.generator_applied is not None:
                    return self.generator_applied
            raise TimeoutError('El Q no confirmó el generador; estado incierto')
        finally:
            self.generator_pending = None
            self.last_generator_poll = time.monotonic()

    def reset_wav_output(self):
        self.wav_request()
        deadline = time.monotonic() + 3
        while self.wav_pending and time.monotonic() < deadline:
            self.pump()
        if self.wav_pending:
            raise TimeoutError('El Q no confirmó el estado Wav')
        if self.wav_status and self.wav_status.state != wav.State.IDLE:
            self.wav_session = self.wav_status.session
            self.wav_request(3)
            deadline = time.monotonic() + 3
            while self.wav_pending and time.monotonic() < deadline:
                self.pump()
            if self.wav_pending or self.wav_status.reason:
                raise RuntimeError('El Q no confirmó Stop Wav para liberar A0')

    def wav_request(self, op=0, codes=None, rate=20000):
        if not self.wav_candidate:
            raise ValueError('WAV requiere Scope V18 confirmado; usar Preparar Q')
        if op == 1:
            if rate not in wav.RATES or (rate!=20000 and (self.wav_status is None or not self.wav_status.rates_mask & (1 << wav.RATES.index(rate)))):
                raise ValueError("Tasa WAV no confirmada por el firmware")
            if self.wav_codes is not None:
                raise ValueError('Detener el WAV actual antes de reproducir otro')
            if hasattr(codes,'prepare_audio'):codes.prepare_audio()
            self.wav_previous_levels = self.wav_levels
            self.wav_rate = rate
            self.wav_codes = codes
            self.wav_session = self._id()
            self.wav_started = False
            self.wav_next_offset = 0
            self.wav_chunk_tokens = 1.0
            self.wav_chunk_token_at = time.monotonic()
            self.wav_low_ack = None
            self.wav_low_episode = False
            self.wav_buffer_adjust_at = time.monotonic()
            self.wav_status = None
        elif op == 3:
            self.wav_codes = None
        self._wav_send(wav.command(self._id(), self.wav_session if op else 0, op,
                                   len(codes) if codes is not None else 0, self.wav_rate))

    def _wav_send(self, frame):
        rid = struct.unpack_from('<I', frame, 8)[0]
        kind=struct.unpack_from('<H',frame,6)[0]
        if kind!=13:self.wav_inflight.clear() # STOP supersedes outstanding audio ACKs.
        self.wav_inflight[rid]=(time.monotonic(),kind)
        self.wav_pending=next((key,entry[0]) for key,entry in self.wav_inflight.items())
        self.ping = None
        self.last_ping = time.monotonic()
        cpu_start=time.thread_time() if self.transport_trace is not None or self.child_stage_timing is not None else None
        process_start=time.process_time() if self.transport_trace is not None else None
        began=time.monotonic()
        self.connection.socket.sendall(frame)
        self._trace_transport('send',began,time.monotonic(),rid,cpu_seconds=(time.thread_time()-cpu_start) if cpu_start is not None else None,process_cpu_seconds=(time.process_time()-process_start) if process_start is not None else None,kind=kind)
        if hasattr(self.wav_codes,'observe_transport'):
            self.wav_codes.observe_transport('socket_send',time.monotonic()-began)

    def _trace_transport(self,stage,start,end,rid=None,cpu_seconds=None,process_cpu_seconds=None,bytes_read=None,kind=None):
        if self.child_stage_timing is not None:
            details = {}
            if rid is not None:details['rid'] = rid
            if bytes_read is not None:details['bytes_read'] = bytes_read
            if kind is not None:details['kind'] = kind
            if stage == 'ack' and rid in self.wav_inflight:
                sent_at, sent_kind = self.wav_inflight[rid]
                details.update(kind=sent_kind, send_to_ack_ms=(end-sent_at)*1000)
            self.child_stage_timing._observe(stage,start,end,cpu_seconds,**details)
        # Capture slow receive/decode episodes for live RADIO without retaining
        # ADC data or enabling the expensive full transport trace.
        if stage in ('read','decode') and end-start>=.02:
            observer=getattr(self.wav_codes,'observe_transport',None)
            if observer is not None:observer(stage,end-start)
        if self.transport_trace is not None and (getattr(self.transport_trace,'rolling',False) or len(self.transport_trace)<100000):
            self.transport_trace.append((stage,start,end,rid,cpu_seconds,process_cpu_seconds) if process_cpu_seconds is not None else (stage,start,end,rid) if cpu_seconds is None else (stage,start,end,rid,cpu_seconds))

    def set_wav_levels(self, amplitude, offset):
        if not (0 <= amplitude <= 3.3 and amplitude / 2 <= offset <= 3.3 - amplitude / 2):
            raise ValueError('Amplitud y offset WAV fuera de rango')
        self.wav_levels = (amplitude, offset)

    def _wav_chunk_codes(self, start, end):
        if self.wav_levels is None:
            if hasattr(self.wav_codes,'try_codes'):return self.wav_codes.try_codes(start,end)
            return self.wav_codes[start:end]
        previous = self.wav_previous_levels or self.wav_levels
        # Scalars broadcast identically while controls are stationary. Keep
        # the existing per-sample ramps whenever either level changes.
        amplitude = (self.wav_levels[0] if previous[0]==self.wav_levels[0] else
                     np.linspace(previous[0], self.wav_levels[0], end-start))
        offset = (self.wav_levels[1] if previous[1]==self.wav_levels[1] else
                  np.linspace(previous[1], self.wav_levels[1], end-start))
        if hasattr(self.wav_codes,'render_dac_codes'):
            result=(self.wav_codes.try_codes(start,end,(amplitude,offset)) if hasattr(self.wav_codes,'try_codes') else
                    self.wav_codes.render_dac_codes(start,end,amplitude,offset))
            if result is None:return None
            self.wav_previous_levels=getattr(self.wav_codes,'last_dac_levels',None) or self.wav_levels
            return result
        codes=self.wav_codes[start:end]
        signal = np.asarray(codes, dtype=np.float64) / 4095 - .5
        result = np.rint((signal * amplitude + offset) * 4095 / 3.3).clip(0, 4095).astype('<u2')
        self.wav_previous_levels = self.wav_levels
        return result

    def service_wav(self):
        pcm=isinstance(self.wav_codes,np.ndarray)
        live=getattr(self.wav_codes,'live',False) or pcm
        # The window bounds unconfirmed sends, independently of DAC capacity.
        limit=min(30,getattr(self.wav_status,'queue_slots',16)) if getattr(self.wav_codes,'radio_audio',False) else 16
        window=2 if pcm else max(1,min(limit,int(getattr(self.wav_codes,'credit_window',min(4,self.wav_live_credits)))))
        if self.wav_pending:
            if time.monotonic()-self.wav_pending[1] > 3:
                self.wav_codes=None;self.wav_pending=None;self.wav_inflight.clear()
                self.on_status('WAV: sin confirmación del Q; salida incierta')
                return
            # PCM chunks may fill the same bounded window while priming too.
            # BEGIN/PLAY/QUERY/STOP still serialize against all outstanding ACKs.
            if (not live or len(self.wav_inflight)>=window or
                    any(entry[1]!=13 for entry in self.wav_inflight.values())):
                return
        s = self.wav_status
        if self.wav_codes is None or s is None or s.session != self.wav_session:
            return
        slots=getattr(s,'queue_slots',16)
        capacity=min(slots,getattr(self.wav_codes,'maximum_blocks',30 if pcm else 16))
        target=max(2,min(capacity,getattr(self.wav_codes,'target_blocks',30 if pcm else 16)))
        reserved=len(self.wav_inflight)
        queued=slots-s.free_blocks+reserved
        if self.wav_started and getattr(self.wav_codes,'live',False):
            now=time.monotonic()
            alarm_token=getattr(s,"request_id",(s.accepted,s.free_blocks))
            # One consumed block is the normal refill cycle, not a transport
            # stall. Keep the four-block warning for larger queues, but leave
            # a full block of hysteresis below the ordinary five-block target.
            low_threshold=min(4,target-2)
            if slots-s.free_blocks>=target-1:self.wav_low_episode=False
            if slots-s.free_blocks<=low_threshold and not self.wav_low_episode and alarm_token!=self.wav_low_ack:
                self.wav_low_ack=alarm_token
                self.wav_low_episode=True
                target=min(capacity,target+2)
                self.wav_codes.target_blocks=target
                self.wav_buffer_adjust_at=now
            # Do not shrink a live queue: physical runs cut out after returning
            # to the small target even after a seemingly stable interval.
        if not self.wav_started and not reserved and (queued >= target or s.accepted == len(self.wav_codes)):
            self.wav_started = True
            self._wav_send(wav.command(self._id(), self.wav_session, 2))
        elif max(s.accepted,self.wav_next_offset) < len(self.wav_codes) and s.free_blocks>reserved and queued < target:
            # Fill available credits in this turn, before another blocking read.
            # Startup and control commands retain their serialized contract.
            credits=min((window-reserved if live else 1),s.free_blocks-reserved,target-queued)
            prepare_burst=getattr(self.wav_codes,'prepare_burst',None)
            if prepare_burst is not None:
                authorized=credits
                interval=max(0,float(getattr(self.wav_codes,'chunk_interval',0)))
                if interval:
                    now=time.monotonic()
                    burst=max(1,min(16,int(getattr(self.wav_codes,'chunk_burst',1))))
                    tokens=min(burst,getattr(self,'wav_chunk_tokens',1.0)+
                        max(0,now-getattr(self,'wav_chunk_token_at',now))/interval)
                    authorized=min(authorized,int(tokens))
                if authorized>0:
                    prepare_burst(max(s.accepted,self.wav_next_offset),self.wav_chunk_points,authorized)
            for _ in range(credits):
                interval=max(0,float(getattr(self.wav_codes,'chunk_interval',0)))
                if interval:
                    now=time.monotonic()
                    burst=max(1,min(16,int(getattr(self.wav_codes,'chunk_burst',1))))
                    self.wav_chunk_tokens=min(burst,getattr(self,'wav_chunk_tokens',1.0)+
                        max(0,now-getattr(self,'wav_chunk_token_at',now))/interval)
                    self.wav_chunk_token_at=now
                    if self.wav_chunk_tokens<1:break
                start=max(s.accepted,self.wav_next_offset)
                if start>=len(self.wav_codes):break
                if self.wav_chunk_points not in (240,wav.CHUNK):
                    raise ValueError('Tamaño de bloque WAV no soportado')
                end=min(start+self.wav_chunk_points,len(self.wav_codes))
                cpu_start=time.thread_time() if self.transport_trace is not None or self.child_stage_timing is not None else None
                process_start=time.process_time() if self.transport_trace is not None else None
                began=time.monotonic()
                codes=self._wav_chunk_codes(start,end)
                if codes is None:break # Worker is rendering; keep receiving ADC/ACK.
                self._trace_transport('generate',began,time.monotonic(),cpu_seconds=(time.thread_time()-cpu_start) if cpu_start is not None else None,process_cpu_seconds=(time.process_time()-process_start) if process_start is not None else None)
                if hasattr(self.wav_codes,'observe_transport'):
                    self.wav_codes.observe_transport('chunk_generation',time.monotonic()-began)
                self._wav_send(wav.chunk(self._id(),self.wav_session,start,codes))
                if _flow_trace is not None:_flow_trace("pcm_child_sent",f"pcm:{getattr(self.wav_codes,'session',self.wav_session)}:{start}")
                self.wav_next_offset=end
                if interval:self.wav_chunk_tokens-=1
        elif not self.wav_pending and self.wav_started and time.monotonic() >= self.wav_poll_at:
            interval=getattr(self.wav_codes,'poll_interval',.004 if live else .02)
            self.wav_poll_at = time.monotonic() + max(.004,min(.1,float(interval)))
            self._wav_send(wav.command(self._id(), self.wav_session, 0))

    def shutdown_output(self):
        """Release WAV first, then confirm DAC output disabled at zero volts."""
        was_running = self.running
        try:
            self.running = lambda: True
            if self.wav_candidate:
                self.reset_wav_output()
            reply = self.generator(GeneratorConfig(enabled=0, low=0, high=0))
            if reply.phase != Phase.APPLIED or reply.active.enabled:
                raise RuntimeError('El Q no confirmó salida apagada')
        finally:
            self.running = was_running

    def close(self):
        if self.wav_candidate and (self.wav_codes is not None or (self.wav_status and self.wav_status.state in (wav.State.BUFFERING, wav.State.PLAYING, wav.State.UNDERRUN, wav.State.FAULT))):
            self.wav_codes = None
            if self.connection.socket is not None:
                was_running = self.running
                try:
                    self.running = lambda: True
                    self.wav_request(3)
                    deadline = time.monotonic() + 1
                    while self.wav_pending and time.monotonic() < deadline:
                        self.pump()
                except (OSError, RuntimeError, ValueError):
                    pass  # A lost USB link cannot acknowledge STOP.
                finally:
                    self.running = was_running
        if self.r4 is not None:
            self.r4.close()
            self.r4 = None
