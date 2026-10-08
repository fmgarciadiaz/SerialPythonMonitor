"""V13 receiver: permanent Q control, configurable ADC/DAC and confirmed SPI/UART output."""
import os
import numpy as np
import queue
import secrets
import struct
import threading
import time

from monitor.historico.v13.receiver.unoq_config_decoder import ConfigurationDecoder
from monitor.historico.v13.receiver.unoq_generator import generator_request, GeneratorConfig
from monitor.historico.v13.receiver import unoq_wav as wav
from monitor.historico.v13.receiver.unoq_acquisition import Configuration, acquisition_request
from monitor.historico.v13.receiver.unoq_switch import Mode, Phase, switch_request
from monitor.historico.v13.receiver.unoq_control import status_request
from monitor.historico.v13.receiver.unoq_usb import MASK, ProtocolError


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
        self.wav_levels = None
        self.wav_previous_levels = None
        self.wav_codes = None
        self.wav_session = 0
        self.wav_poll_at = 0
        self.wav_rate = 20000
        self.wav_started = False
        self.wav_candidate = (os.environ.get("MONITOR_V13_WAV_FIRMWARE") == "v12_audio"
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

    def _emit(self, records):
        if not records:
            return
        for timestamp, a, b, index in records:
            if index != self.next_index:
                raise ProtocolError('Índice discontinuo al cambiar el destino')
            if self.timestamp is not None and (timestamp-self.timestamp)&MASK != self.config.period:
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

    def pump(self):
        if not self.running():
            raise InterruptedError('Recepción detenida')
        self._uart()
        self.decoder.feed(self.connection.read())
        for kind, value in self.decoder.events:
            if kind == 'wav':
                if not self.wav_pending or value.request_id != self.wav_pending[0]:
                    continue
                if self.wav_codes is not None and value.session != self.wav_session:
                    raise ProtocolError('ACK WAV para otra sesión')
                if self.wav_codes is not None and value.rate != self.wav_rate:
                    raise ProtocolError("Tasa WAV distinta de la solicitada")
                self.wav_status = value
                self.wav_pending = None
                self.on_wav(value)
                if value.reason or value.state in (wav.State.DONE, wav.State.UNDERRUN, wav.State.FAULT):
                    self.wav_codes = None
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
                    if value.requested_bits != self.config_pending[1].bits or value.requested_period != self.config_pending[1].period:
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
                    self._emit(value)
                else:
                    raise ProtocolError('Muestras SPI mientras el destino es R4')
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

    def configure(self, config):
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
            raise ValueError('WAV requiere firmware v12_audio explícitamente seleccionado')
        if op == 1:
            if rate not in wav.RATES or (rate!=20000 and (self.wav_status is None or not self.wav_status.rates_mask & (1 << wav.RATES.index(rate)))):
                raise ValueError("Tasa WAV no confirmada por el firmware")
            if self.wav_codes is not None:
                raise ValueError('Detener el WAV actual antes de reproducir otro')
            self.wav_previous_levels = self.wav_levels
            self.wav_rate = rate
            self.wav_codes = codes
            self.wav_session = self._id()
            self.wav_started = False
            self.wav_status = None
        elif op == 3:
            self.wav_codes = None
        self._wav_send(wav.command(self._id(), self.wav_session if op else 0, op,
                                   len(codes) if codes is not None else 0, self.wav_rate))

    def _wav_send(self, frame):
        rid = struct.unpack_from('<I', frame, 8)[0]
        self.wav_pending = (rid, time.monotonic())
        self.ping = None
        self.last_ping = time.monotonic()
        self.connection.socket.sendall(frame)

    def set_wav_levels(self, amplitude, offset):
        if not (0 <= amplitude <= 3.3 and amplitude / 2 <= offset <= 3.3 - amplitude / 2):
            raise ValueError('Amplitud y offset WAV fuera de rango')
        self.wav_levels = (amplitude, offset)

    def _wav_chunk_codes(self, start, end):
        codes = self.wav_codes[start:end]
        if self.wav_levels is None:
            return codes
        previous = self.wav_previous_levels or self.wav_levels
        amplitude = np.linspace(previous[0], self.wav_levels[0], len(codes))
        offset = np.linspace(previous[1], self.wav_levels[1], len(codes))
        signal = np.asarray(codes, dtype=np.float64) / 4095 - .5
        result = np.rint((signal * amplitude + offset) * 4095 / 3.3).clip(0, 4095).astype('<u2')
        self.wav_previous_levels = self.wav_levels
        return result

    def service_wav(self):
        if self.wav_pending:
            if time.monotonic()-self.wav_pending[1] > 3:
                self.wav_codes = None
                self.wav_pending = None
                self.on_status('WAV: sin confirmación del Q; salida incierta')
            return
        s = self.wav_status
        if self.wav_codes is None or s is None or s.session != self.wav_session:
            return
        if not self.wav_started and (s.free_blocks == 0 or s.accepted == len(self.wav_codes)):
            self.wav_started = True
            self._wav_send(wav.command(self._id(), self.wav_session, 2))
        elif s.accepted < len(self.wav_codes) and s.free_blocks:
            end = min(s.accepted + wav.CHUNK, len(self.wav_codes))
            self._wav_send(wav.chunk(self._id(), self.wav_session, s.accepted,
                                     self._wav_chunk_codes(s.accepted,end)))
        elif self.wav_started and time.monotonic() >= self.wav_poll_at:
            self.wav_poll_at = time.monotonic() + .02
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
