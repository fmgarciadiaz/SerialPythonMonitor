"""V12 fixed-profile compatibility receiver and UART parser; the app uses unoq_config_receiver."""
import queue
import secrets
import struct
import threading
import time

from monitor.historico.v12.receiver.unoq_dual import DualDecoder
from monitor.historico.v12.receiver.unoq_switch import Mode, Phase, switch_request
from monitor.historico.v12.receiver.unoq_control import status_request
from monitor.historico.v12.receiver.unoq_usb import MASK, ProtocolError


class LegacyDecoder:
    """Strict DATA reader. Only the initial incomplete packet may be skipped."""
    def __init__(self):
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
            if any(a > 16383 or b > 16383 for _, a, b in records):
                raise ProtocolError('R4: muestra fuera del rango de 14 bits')
            if any((b[0]-a[0])&MASK != 32 for a, b in zip(records, records[1:])):
                raise ProtocolError('R4: timestamps discontinuos dentro de DATA')
            batches.append(records)
            self.locked = True
            del self.buffer[:4103]
        return batches


class R4Reader:
    def __init__(self, path):
        import serial
        self.path = path
        self.port = serial.Serial(path, 3000000, timeout=0.05)
        self.batches = queue.Queue(maxsize=128)
        self.error = None
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        decoder = LegacyDecoder()
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
        self.decoder = DualDecoder()
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
            if self.timestamp is not None and (timestamp-self.timestamp)&MASK != 32:
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
            if kind == 'reply':
                self._reply(value)
            elif self.mode is not None:
                if self.uart_end is not None:
                    self.spi_waiting.extend(value)
                elif self.mode == Mode.SPI:
                    self._emit(value)
                else:
                    raise ProtocolError('Muestras SPI mientras el destino es R4')
        self._uart()
        current = time.monotonic()
        if self.ping is not None:
            if any(status['ack'] == self.ping[0] for status in self.decoder.statuses):
                self.ping = None
                self.last_ping = current
            elif current-self.ping[1] > 2:
                raise TimeoutError('El Q dejó de confirmar el control')
        if self.pending is None and self.ping is None and current-self.last_ping >= 1:
            rid = self._id()
            self.connection.socket.sendall(status_request(rid))
            self.ping = (rid, current)
        if self.visible and self.pending is None and current-self.last_samples > 2:
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
            self.r4 = self.reader_factory(r4_path)
            # Opening USB can reset R4. Keep receiving SPI during its reboot.
            end = time.monotonic()+R4_BOOT_SECONDS
            while time.monotonic() < end:
                self.pump()
            self.r4.drain()
            self._switch(Mode.UART)
        self.visible = True
        self.last_samples = time.monotonic()
        return self.applied

    def close(self):
        if self.r4 is not None:
            self.r4.close()
            self.r4 = None
