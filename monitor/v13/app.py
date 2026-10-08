from dataclasses import replace
"""Monitor V13: adquisición configurable y generador DAC controlado desde el Q."""
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
import csv
import re
import wave
import itertools
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TextIO, Tuple

import numpy as np
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from monitor.number_format import number, formats
from monitor.locale_axis import LocaleAxis
from monitor.v13.wav_source import seek_playback
from monitor.v13.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from monitor.v13.wav_source import prepare_wav, inspect_wav
from monitor.v13.audio_dc import DCBlocker
from monitor.v13.history import SampleHistory
from monitor.v13.spectrum import SpectralDisplay
from monitor.v13.receiver.unoq_usb import Connection, usb_devices
from monitor.v13.receiver.unoq_switch import Mode
from monitor.v13.receiver.unoq_config_receiver import OutputReceiver
from monitor.v13.receiver.unoq_autoload import ensure_scope, connect_scope
from monitor.v13.receiver.unoq_generator import GeneratorConfig, WAVES, MODES
from monitor.v13.receiver.unoq_acquisition import Configuration, BITS, RATES as RECEIVER_RATES, UART_RATES
# Perfil P992 validado a 14 bits/125 kHz; no ofrecer tasas superiores.
RATES = tuple(rate for rate in RECEIVER_RATES if rate <= 125000)
import queue
from serial.tools import list_ports

from PyQt6 import QtCore, QtGui, QtWidgets
from monitor.v13.status_widgets import StatusLabel, StatusBox
import pyqtgraph as pg
if pg.Qt.QT_LIB != "PyQt6":
    raise RuntimeError("V13 requiere pyqtgraph con PyQt6; iniciar en un proceso separado de V12.")

class WavPreparation(QtCore.QObject):
    ready = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    def __init__(self, path, channel, amplitude, offset, rate=20000):
        super().__init__()
        self.arguments = (path, channel, amplitude, offset, rate)
    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.ready.emit(prepare_wav(*self.arguments))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class FineAdjustment:
    """Shift-drag changes one unit per horizontal pixel; wheel one per notch."""
    def mousePressEvent(self, event):
        self._fine_drag_x = event.position().x()
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier and event.button() == QtCore.Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        x = event.position().x()
        previous = getattr(self, '_fine_drag_x', x)
        self._fine_drag_x = x
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.setValue(self.value() + round(x - previous))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        self.setValue(self.value() + round(steps))
        event.accept()


class OffsetSlider(FineAdjustment, QtWidgets.QSlider):
    centered = QtCore.pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.centered.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class InstrumentDial(QtWidgets.QDial):
    """Native interaction with a fixed, readable visual graduation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Draw with Fusion directly: inherited frame padding otherwise shifts
        # the native knob while the custom graduation stays in widget space.
        self._dial_style = QtWidgets.QStyleFactory.create('Fusion')
        self._dial_style.setParent(self)

    def paintEvent(self, event):
        option = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(option)
        option.tickPosition = QtWidgets.QSlider.TickPosition.NoTicks
        option.subControls &= ~QtWidgets.QStyle.SubControl.SC_DialTickmarks
        painter = QtWidgets.QStylePainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self._dial_style.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_Dial, option, painter, self)
        if not self.notchesVisible():
            return
        center = QtCore.QPointF(option.rect.x() + option.rect.width() / 2.0,
                               option.rect.y() + option.rect.height() / 2.0)
        radius = min(option.rect.width(), option.rect.height()) // 2 - 3
        color = QtGui.QColor('#a0adbf' if self.isEnabled() else '#485160')
        painter.setPen(QtGui.QPen(color, 1.0))
        for index in range(25):
            angle = math.radians((270 if option.dialWrapping else 240)
                                 - index * (360 if option.dialWrapping else 300) / 24)
            length = 6 if index % 4 == 0 else 3
            def point(r):
                return center + QtCore.QPointF(r * math.cos(angle), -r * math.sin(angle))
            painter.drawLine(point(radius - length), point(radius))


# Configuración de pyqtgraph para alto rendimiento y estética de osciloscopio
pg.setConfigOption("background", "#121418")  # Fondo oscuro elegante de laboratorio
pg.setConfigOption("foreground", "#ffffff")  # Texto y números en blanco puro
pg.setConfigOption("antialias", False)

# =============================================================================
# CONFIGURACIÓN GENERAL Y VALORES POR DEFECTO
# =============================================================================
BAUD_DEFAULT = 0            # Control USB; UART hacia R4 permanece a 3 Mbps.
ADC_BITS_DEFAULT = 14        # Resolución ADC por defecto (12 bits = 4095, 10 bits = 1023, etc.)
V_REF_VOLTS = 3.3            # Tensión de referencia del ADC en voltios
VISIBLE_SAMPLES_DEFAULT = 9000
VISIBLE_SAMPLES_MIN = 50
VISIBLE_SAMPLES_MAX = 250000
MAX_BUFFER_SAMPLES = 510000  # Ventana de 250.000 más historial y margen de roll
RENDER_INTERVAL_MS = 16      # Objetivo ~60 FPS (según carga de CPU/pantalla)
ROLL_SMOOTH_SECONDS = 0.10   # Suavizado visual; no modifica adquisición ni CSV
RECORD_MAX_SECONDS = 30.0
RECORD_FLUSH_SECONDS = 1.0



ARDUINO_KEYWORDS = (
    "arduino",
    "usbmodem",
    "usb serial",
    "ch340",
    "cp210",
    "ftdi",
    "wch",
)

PALETTE = [
    "#00e5ff",  # Cyan neón (CH1: V_IN)
    "#ffd600",  # Amarillo eléctrico (CH2: V_OUT)
    "#00e676",  # Verde neón (ADC_IN)
    "#ff4081",  # Rosa neón (ADC_OUT)
    "#ff9100",  # Naranja (Muestra)
    "#b388ff",  # Púrpura (Tiempo)
]

CHANNEL_COLORS = {
    "V_IN": "#00e5ff",
    "V_OUT": "#ffd600",
    "ADC_IN": "#00e676",
    "ADC_OUT": "#ff4081",
    "Muestra": "#ff9100",
    "Tiempo (us)": "#b388ff",
}



class AmplitudeDial(FineAdjustment, InstrumentDial):
    pass


class GeneratorValueSpinBox(QtWidgets.QDoubleSpinBox):
    """Keep fractional precision without padding editable values with zeros."""
    def textFromValue(self, value):
        text = self.locale().toString(float(value), 'f', self.decimals())
        if self.decimals():
            text = text.rstrip('0').rstrip(self.locale().decimalPoint())
        return text


class VoltageSpinBox(GeneratorValueSpinBox):
    def textFromValue(self, value):
        return self.locale().toString(float(value), 'f', 2)


class GeneratorFrequencySpinBox(GeneratorValueSpinBox):
    """Use Hz below 1 kHz and kHz above, preserving fractional precision."""
    def textFromValue(self, value):
        scaled = float(value) / 1000 if value >= 1000 else float(value)
        precision = 6 if value >= 1000 else 3
        text = self.locale().toString(scaled, 'f', precision)
        text = text.rstrip('0').rstrip(self.locale().decimalPoint())
        return text + (' kHz' if value >= 1000 else ' Hz')

    def valueFromText(self, text):
        text = text.strip()
        multiplier = 1000 if text.endswith('kHz') else 1
        number = text.removesuffix('kHz').removesuffix('Hz').strip()
        value, ok = self.locale().toDouble(number)
        return value * multiplier if ok else self.value()

    def validate(self, text, pos):
        number = text.strip().removesuffix('kHz').removesuffix('Hz').strip()
        validator = QtGui.QDoubleValidator(self)
        validator.setLocale(self.locale())
        state, _, _ = validator.validate(number, pos)
        return state, text, pos


class NeutralMeasurementDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, reference, parent):
        super().__init__(parent)
        self.reference = reference

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignmentFlag.AlignCenter
        option.backgroundBrush = QtGui.QBrush(QtGui.QColor('#1a1d24'))
        for role, color in ((QtGui.QPalette.ColorRole.Base, '#1a1d24'),
                            (QtGui.QPalette.ColorRole.Text, '#ffffff'),
                            (QtGui.QPalette.ColorRole.Highlight, '#323946'),
                            (QtGui.QPalette.ColorRole.HighlightedText, '#ffffff')):
            option.palette.setColor(role, QtGui.QColor(color))

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(24, option.fontMetrics.height() + 6))
        return size


class GeneratorComboBox(QtWidgets.QComboBox):
    """Keep the entire closed control clickable, with centered text."""
    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        text, icon = option.currentText, QtGui.QIcon(option.currentIcon)
        option.currentText = ''
        option.currentIcon = QtGui.QIcon()
        painter.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_ComboBox, option)
        rect = self.style().subControlRect(QtWidgets.QStyle.ComplexControl.CC_ComboBox, option,
                                          QtWidgets.QStyle.SubControl.SC_ComboBoxEditField, self)
        if self.property("centerInWholeBox"):
            rect = self.rect()
        if not icon.isNull():
            small = self.width() < 150
            icon.paint(painter, QtCore.QRect(rect.left() + 2, rect.center().y() - (5 if small else 9),
                                           16 if small else 36, 10 if small else 18))
            rect.adjust(22 if small else 44, 0, 0, 0)
        painter.setPen(QtGui.QColor(self.property("selectedTextColor")) if self.property("selectedTextColor") else self.palette().color(QtGui.QPalette.ColorRole.Text))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)


class InstrumentLogo(QtWidgets.QWidget):
    """Small vector instrument mark, drawn at native display resolution."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 42)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor('#55dfc4'), 1.5))
        painter.drawRoundedRect(QtCore.QRectF(4, 9, 58, 27), 5, 5)
        path = QtGui.QPainterPath()
        for i in range(81):
            t = i * 2 * math.pi / 80
            point = QtCore.QPointF(33 + 19 * math.cos(t), 22 + 8 * math.sin(2 * t))
            if i: path.lineTo(point)
            else: path.moveTo(point)
        painter.drawPath(path)
        painter.drawLine(15, 22, 21, 22)
        painter.drawLine(45, 22, 51, 22)
        painter.drawLine(48, 19, 48, 25)
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor('#aeb8c8'))
        metrics = QtGui.QFontMetricsF(font)
        baseline = 9 + (27 - metrics.height()) / 2 + metrics.ascent()
        prefix = 'fer·'
        painter.drawText(QtCore.QPointF(72, baseline), prefix)
        painter.setPen(QtGui.QColor('#55dfc4'))
        painter.drawText(QtCore.QPointF(72 + metrics.horizontalAdvance(prefix), baseline), 'gd')


def generator_wave_icon(wave):
    pixmap = QtGui.QPixmap(64, 28)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setPen(QtGui.QPen(QtGui.QColor('#55dfc4'), 2))
    path = QtGui.QPainterPath()
    for i in range(61):
        t = i / 60
        if wave == 0: y = 1 if t < .5 else 0
        elif wave == 1: y = (1 + math.sin(2 * math.pi * t)) / 2
        elif wave == 2: y = 1 - abs(2 * t - 1)
        elif wave == 3: y = t if t < 1 else 0
        else: y = 1 if .25 <= t < .65 else 0
        point = QtCore.QPointF(2 + 60*t, 24 - 20*y)
        if i: path.lineTo(point)
        else: path.moveTo(point)
    painter.drawPath(path)
    painter.end()
    return QtGui.QIcon(pixmap)


class TimedBatch(list):
    """Sample batch with a monotonic publication time for GUI-delay diagnostics."""
    def __init__(self, samples):
        super().__init__(samples)
        self.published_at = time.monotonic()


class QPreparationThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(bool, str)

    def __init__(self, serial, parent=None):
        super().__init__(parent)
        self.serial = serial

    def run(self):
        import subprocess
        from datetime import datetime
        folder = ROOT / 'diagnosticos' / 'resultados_autoload'
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / ('preparar_q_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
        try:
            with log.open('w') as output:
                process = subprocess.Popen([sys.executable, str(ROOT / 'tools/prepare_q.py'),
                                            '--serial', self.serial], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True)
                last_error = ''
                for line in process.stdout:
                    output.write(line)
                    output.flush()
                    text = line.strip()
                    if text.endswith('…'):
                        self.progress.emit(text)
                    if text.startswith('Error:'):
                        last_error = text
                code = process.wait()
            self.result.emit(code == 0, 'Q preparado; pulsar Conectar' if code == 0 else
                             (last_error or 'No se pudo preparar el Q') + f' · Log: {log.name}')
        except Exception as exc:
            self.result.emit(False, str(exc))


class OutputWorker(QtCore.QObject):
    # Python object transfer avoids converting every sample dictionary to QVariant.
    batch_ready = QtCore.pyqtSignal(object)
    headers_detected = QtCore.pyqtSignal(list)
    status_changed = QtCore.pyqtSignal(str)
    output_confirmed = QtCore.pyqtSignal(int, str)
    acquisition_confirmed = QtCore.pyqtSignal(int, int)
    generator_confirmed = QtCore.pyqtSignal(object)
    instrument_confirmed = QtCore.pyqtSignal(object)
    wav_confirmed = QtCore.pyqtSignal(object)
    switching = QtCore.pyqtSignal(bool)
    error_occurred = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, port, mode, r4_port=None, config=Configuration(), autoload=False, initial_generator=None):
        super().__init__()
        self.port = port
        self.autoload = autoload
        self.initial_generator = initial_generator
        self.mode = Mode(mode)
        self.r4_port = r4_port
        self.config = config
        self.running = True
        self.requests = queue.Queue(maxsize=1)
        self.generator_requests = queue.Queue(maxsize=1)
        self.wav_requests = queue.Queue(maxsize=4)
        self.wav_levels = queue.Queue(maxsize=1)

    def set_adc_bits(self, bits):
        pass  # Hardware settings are applied together through configure(), not this display hook.

    def stop(self):
        self.running = False

    def request_output(self, mode, r4_port, config):
        self.requests.put_nowait((Mode(mode), r4_port, config))

    def request_generator(self, config):
        self.generator_requests.put_nowait(config)

    def request_wav(self, op, codes=None, rate=20000):
        self.wav_requests.put_nowait((op, codes, rate))

    def request_wav_levels(self, amplitude, offset):
        try:
            self.wav_levels.get_nowait()
        except queue.Empty:
            pass
        self.wav_levels.put_nowait((amplitude, offset))

    @QtCore.pyqtSlot()
    def run(self):
        batch = []
        emitted = time.monotonic()
        receiver = None
        published = False
        def collect(samples):
            if not published: return
            for timestamp, a, b, index in samples:
                batch.append({'V_IN': a*3.3/receiver.config.maximum, 'V_OUT': b*3.3/receiver.config.maximum,
                              'ADC_IN': float(a), 'ADC_OUT': float(b),
                              'Muestra': float(index), 'Tiempo (us)': float(timestamp)})
            flush()
        def flush():
            nonlocal batch, emitted
            if batch and time.monotonic()-emitted >= 0.02:
                self.batch_ready.emit(TimedBatch(batch))
                batch = []
                emitted = time.monotonic()
        def progress(text):
            flush()
            self.status_changed.emit(text)
        def settings_applied(config):
            nonlocal batch, emitted
            if batch:
                self.batch_ready.emit(TimedBatch(batch)); batch = []
            emitted = time.monotonic()
            self.acquisition_confirmed.emit(config.bits, config.rate)
        def apply(mode, r4_port, config):
            if int(mode) == int(Mode.UART) and config.rate not in UART_RATES:
                raise ValueError('UART admite hasta 31,25 kHz')
            self.switching.emit(True)
            receiver.configure(config)
            receiver.select(mode, r4_port)
            flush()
            self.output_confirmed.emit(int(mode), r4_port if mode == Mode.UART else '')
            self.switching.emit(False)
        try:
            if not self.running:
                return
            transport = connect_scope(self.port, progress, lambda: self.running) if self.autoload else Connection(self.port)
            with transport as connection:
                try:
                    from monitor.v13.bode_calibration import instrument_identity
                    self.instrument_confirmed.emit(instrument_identity(self.port))
                    connection.socket.settimeout(0.01)
                    receiver = OutputReceiver(connection, collect, progress, lambda: self.running)
                    receiver.on_configuration = settings_applied
                    receiver.on_generator = self.generator_confirmed.emit
                    wav_source_codes = None
                    wav_origin = 0
                    def publish_wav(status):
                        self.wav_confirmed.emit(replace(status, played=status.played + wav_origin,
                                                       total=status.total + wav_origin))
                    receiver.on_wav = publish_wav
                    apply(self.mode, self.r4_port, self.config)
                    self.acquisition_confirmed.emit(receiver.config.bits, receiver.config.rate)
                    published = True
                    if receiver.wav_candidate:
                        receiver.reset_wav_output()
                    receiver.generator(self.initial_generator)
                    while self.running:
                        try:
                            receiver.set_wav_levels(*self.wav_levels.get_nowait())
                        except queue.Empty:
                            pass
                        try:
                            wav_op, wav_codes, wav_rate = self.wav_requests.get_nowait()
                        except queue.Empty:
                            pass
                        else:
                            if wav_op == 4:
                                if wav_source_codes is not None and receiver.wav_status is not None:
                                    wav_origin = seek_playback(receiver, wav_source_codes, wav_origin, wav_codes)
                                    if wav_origin == len(wav_source_codes):
                                        publish_wav(replace(receiver.wav_status, state=3, played=0, total=0))
                            else:
                                if wav_op == 1:
                                    wav_source_codes = wav_codes
                                    wav_origin = 0
                                receiver.wav_request(wav_op, wav_codes, wav_rate)
                        if receiver.wav_codes is not None or receiver.wav_pending is not None:
                            receiver.pump()
                            flush()
                            continue
                        try:
                            mode, r4_port, config = self.requests.get_nowait()
                        except queue.Empty:
                            try:
                                generator_config = self.generator_requests.get_nowait()
                            except queue.Empty:
                                if time.monotonic()-receiver.last_generator_poll >= 1:
                                    receiver.generator()
                                else:
                                    receiver.pump()
                            else:
                                receiver.generator(generator_config)
                        else:
                            apply(mode, r4_port, config)
                        flush()
                finally:
                    if receiver is not None:
                        try:
                            receiver.shutdown_output()
                        finally:
                            receiver.close()
        except Exception as exc:
            if self.running:
                if batch:
                    self.batch_ready.emit(TimedBatch(batch))
                    batch = []
                self.error_occurred.emit(str(exc))
        finally:
            if batch and self.running:
                self.batch_ready.emit(TimedBatch(batch))
            self.finished.emit()


class SerialMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1320, 820)

        self.channel_colors = CHANNEL_COLORS.copy()
        self.channel_palette = tuple(PALETTE)

        # Buffers circulares
        self.sample_counter = 0
        self.batch_queue_delay_ms = 0.0
        self.batch_queue_delay_max_ms = 0.0
        self.timed_batch_count = 0
        self.sample_numbers: SampleHistory = SampleHistory(MAX_BUFFER_SAMPLES)
        self.series: Dict[str, SampleHistory] = {
            "V_IN": SampleHistory(MAX_BUFFER_SAMPLES),
            "V_OUT": SampleHistory(MAX_BUFFER_SAMPLES),
            "ADC_IN": SampleHistory(MAX_BUFFER_SAMPLES),
            "ADC_OUT": SampleHistory(MAX_BUFFER_SAMPLES),
            "Muestra": SampleHistory(MAX_BUFFER_SAMPLES),
            "Tiempo (us)": SampleHistory(MAX_BUFFER_SAMPLES),
        }

        self.known_columns = list(self.series.keys())
        # Por defecto V_IN (CH1) y V_OUT (CH2) activos simultáneamente
        self.selected_columns: Dict[str, bool] = {
            "V_IN": True,
            "V_OUT": True,
            "ADC_IN": False,
            "ADC_OUT": False,
            "Muestra": False,
            "Tiempo (us)": False,
        }
        self.selection_dirty = True

        # Canal activo seleccionado para la barra de mediciones
        self.active_meas_channel = "V_IN"

        # Estados de adquisición
        self.is_running = True
        self.single_shot_armed = False
        self.trigger_mode = "Auto"

        # Parámetros Horizontales
        self.h_scale = VISIBLE_SAMPLES_DEFAULT
        self.h_pos = 0

        # Parámetros Verticales
        self.v_scale = 3.3
        self.v_pos = 0.0

        # Parámetros y Máquina de Estados del Trigger
        self.trigger_enabled = False
        self.trigger_source = "V_IN"
        self.trigger_level = 1.65
        self.trigger_edge = "Ascendente"
        self.trigger_edge_armed = False
        self.trigger_initialized = False
        self.trigger_sample_index: Optional[int] = None
        self.last_trigger_time = 0.0
        self.frozen_frame: Optional[Tuple[List[int], Dict[str, List[float]]]] = None
        self._updating_trigger_line = False

        # Hilo serial y demo
        self.serial_thread: Optional[QtCore.QThread] = None
        self.serial_worker: Optional[OutputWorker] = None
        self.demo_mode = False
        self.demo_timer: Optional[QtCore.QTimer] = None
        self.start_time = time.perf_counter()
        self.demo_v_out_prev = 0.0

        # Grabación CSV/WAV por lotes para minimizar el coste de E/S.
        self.recording = False
        self.record_start_time = 0.0
        self.record_last_flush_time = 0.0
        self.record_file: Optional[TextIO] = None
        self.record_writer = None
        self.record_wave = None
        self.record_format = "CSV"
        self.record_dc_filter = None
        self.record_previous = None
        self.record_filename = ""
        self.record_rows = 0
        self.record_timer = QtCore.QTimer(self)
        self.record_timer.setInterval(100)
        self.record_timer.timeout.connect(self._update_recording_status)

        self._roll_position = None
        self._roll_time = None
        self._roll_context = None

        # Rendimiento y FPS
        self.render_count = 0
        self.last_fps_calc = time.perf_counter()
        self.current_fps = 0.0

        # Frecuencia de muestreo (Sample Rate)
        self.last_fs_calc_time = time.perf_counter()
        self.last_fs_sample_count = 0
        self.current_fs_hz = 0.0
        self.current_dt_us = 0.0
        self.current_fs_text = "-- S/s"

        # Modo de eje X: False = índice de muestra (defecto), True = tiempo real (µs)
        self.x_axis_time_mode = False

        # Configuración de representación de trazo y corte automático por pausas/gaps
        self.trace_mode = "Escalón"  # "Escalón" o "Línea"
        self.auto_gap_cut = True     # Si True, corta el trazo cuando hay pausas o silencios

        # Resolución ADC configurada por defecto
        self.adc_bits = ADC_BITS_DEFAULT
        self.adc_max = float((1 << ADC_BITS_DEFAULT) - 1)

        # Construir Interfaz
        self._build_ui()
        self._build_status_boxes()
        self._reserve_generator_height()
        self.refresh_ports()

        # Timer de dibujo desacoplado (~60 FPS)
        self.render_timer = QtCore.QTimer(self)
        self.render_timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.render_timer.timeout.connect(self.render_frame)
        self.render_timer.timeout.connect(self.spectral.render)
        self.render_timer.start(RENDER_INTERVAL_MS)

        self.setWindowTitle('Scope V13 · PyQt6 · SPI V3/992 · 125 kHz')
        self.baud_input.setText('—')
        self.baud_input.setReadOnly(True)
        self.baud_input.setToolTip('Destino confirmado por el Q. UART hacia R4: 3.000.000 baudios.')
        for label in self.baud_input.parent().findChildren(QtWidgets.QLabel):
            if label.text() == 'BAUD':
                label.setText('ENLACE')
        self.adc_combo.setCurrentText('14 bits (16383)')
        self.adc_combo.setEnabled(False)
        self.adc_combo.setToolTip('Resolución confirmada por el Q.')
        self.applied_configuration = Configuration(14, 40000)
        self.btn_xaxis_toggle.setChecked(True)

    def _build_status_boxes(self):
        top_layout=self.status_label.parentWidget().layout()
        top_layout.removeWidget(self.status_label)
        self.status_boxes_widget=QtWidgets.QWidget()
        row=QtWidgets.QHBoxLayout(self.status_boxes_widget)
        row.setContentsMargins(0,0,0,0);row.setSpacing(8)
        self.acquisition_status_box=StatusBox('Adquisición')
        self.generator_status_box=StatusBox('Generador')
        self.analysis_status_box=StatusBox('Análisis')
        for box in (self.acquisition_status_box,self.generator_status_box,self.analysis_status_box):
            row.addWidget(box,1)
        top_layout.addWidget(self.status_boxes_widget,5,0,1,4)
        sources=[self.status_label,self.generator_status,self.trigger_status_label,self.spectral.info]
        for panel in self.spectral.bode.panels:sources.extend((panel.status,panel.coverage))
        for source in sources:
            layout=source.parentWidget().layout()
            if layout is not None:layout.removeWidget(source)
            source.hide()
            source.text_changed.connect(self._refresh_status_boxes)
        self._central_status_ready=True
        self._refresh_status_boxes()
        self._generator_availability()

    def _refresh_status_boxes(self,*args):
        if not getattr(self,'_central_status_ready',False):return
        acquisition=self.status_label.text()
        brief=acquisition.split(' · ')[0]
        if 'SINGLE capturado' in acquisition:brief+=' · SINGLE capturado'
        trigger=self.trigger_status_label.text()
        if self.single_shot_armed:brief='SINGLE armado'
        elif self.trigger_enabled and self.is_running and ('Esperando disparo' in trigger or 'buscando disparo' in trigger):
            brief='Esperando trigger'
        self.acquisition_status_box.update_status(brief,acquisition+'\n'+trigger)
        self.generator_status_box.update_status(self.generator_status.text())
        mode=self.spectral.mode
        if mode==3:
            index=self.spectral.bode.tabs.currentIndex()
            panel=self.spectral.bode.panels[index]
            method=('Tonos','Pulso',panel.method.currentText() if index==2 else '')[index]
            status=panel.status.text()
            if status.startswith(('Listo','A2','Seno barrido')):status='Listo'
            detail='Bode '+method+'\n'+panel.status.text()
            if panel.coverage.text():detail+='\n'+panel.coverage.text()
            self.analysis_status_box.update_status('Bode '+method+' · '+status,detail)
        else:
            name=('V/t','FFT','Heatmap')[mode]
            info=self.spectral.info.text() if mode else ''
            state='Activo' if self.is_running else 'Congelado'
            if info and not info.startswith('Fs '):state=info
            if self.single_shot_armed:state='Esperando SINGLE'
            self.analysis_status_box.update_status(name+' · '+state,name+'\n'+(info or state))

    def _build_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121418;
            }
            QWidget {
                background-color: #121418;
                color: #ffffff;
                font-size: 12px;
            }
            QGroupBox {
                border: 1px solid #282d37;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                font-size: 11px;
                color: #8f98a8;
                letter-spacing: 0.5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                top: 3px;
                padding: 0 6px;
                left: 10px;
            }
            QComboBox, QLineEdit, QSpinBox {
                background-color: #1a1d24;
                border: 1px solid #323946;
                border-radius: 5px;
                padding: 4px 8px;
                color: #ffffff;
                font-weight: bold;
            }
            QComboBox:hover, QLineEdit:hover {
                border: 1px solid #00e5ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QPushButton {
                background-color: #21252f;
                border: 1px solid #323946;
                border-radius: 6px;
                padding: 6px 12px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a2f3c;
                border-color: #4f586c;
            }
            QPushButton:pressed {
                background-color: #171920;
            }
            QDial {
                background-color: #1a1d24;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #171920;
                border: 1px solid #323946;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3799ad;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #c5edf3;
                border: 1px solid #57bdcf;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffffff;
                border-color: #00e5ff;
            }
            QSlider::handle:horizontal:disabled {
                background: #697180;
                border-color: #424957;
            }
            QCheckBox {
                spacing: 6px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #3a4252;
                background-color: #171920;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #4f586c;
            }
            QCheckBox::indicator:checked {
                background-color: #00e5ff;
                border: 1px solid #3a4252;
            }
        """)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_h_layout = QtWidgets.QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(10, 10, 10, 10)
        main_h_layout.setSpacing(10)
        self.generator_column = QtWidgets.QGroupBox('GENERADOR · A0')
        self.generator_column.setMinimumWidth(250)
        self.generator_column.setMaximumWidth(285)
        generator_layout = QtWidgets.QVBoxLayout(self.generator_column)
        generator_layout.setContentsMargins(9,6,9,6)
        instrument_column = QtWidgets.QWidget()
        instrument_column.setMinimumWidth(250)
        instrument_column.setMaximumWidth(285)
        instrument_layout = QtWidgets.QVBoxLayout(instrument_column)
        instrument_layout.setContentsMargins(0, 0, 0, 0)
        instrument_layout.setSpacing(8)
        instrument_layout.addWidget(self.generator_column, 0)
        main_h_layout.addWidget(instrument_column)

        # -------------------------------------------------------------
        # COLUMNA IZQUIERDA: PANTALLA, TOP BAR Y MEDICIONES
        # -------------------------------------------------------------
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 1. Barra de Conexión Serial con recuadro sutil
        top_group = QtWidgets.QGroupBox("CONEXIÓN Y VISUALIZACIÓN")
        top_layout = QtWidgets.QGridLayout(top_group)
        top_layout.setSpacing(8)

        port_card = QtWidgets.QFrame()
        port_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        port_card_layout = QtWidgets.QHBoxLayout(port_card)
        port_card_layout.setContentsMargins(4, 2, 4, 2)
        port_card_layout.setSpacing(6)

        lbl_port = QtWidgets.QLabel("CONTROL Q")
        lbl_port.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent;")
        port_card_layout.addWidget(lbl_port)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(160)
        self.port_combo.setStyleSheet("background-color: #171920; border: 1px solid #3a4150;")
        self.port_combo.currentIndexChanged.connect(self._update_port_tooltip)
        port_card_layout.addWidget(self.port_combo, 1)

        refresh_btn = QtWidgets.QPushButton("↻")
        refresh_btn.setToolTip("Actualizar UNO Q de control y puertos del R4")
        self.refresh_button = refresh_btn
        refresh_btn.setFixedWidth(28)
        refresh_btn.setStyleSheet("background-color: #2c3240; border: 1px solid #3e4658; padding: 2px;")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_card_layout.addWidget(refresh_btn)
        top_layout.addWidget(port_card, 0, 0, 1, 2)

        baud_card = QtWidgets.QFrame()
        baud_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        baud_card_layout = QtWidgets.QHBoxLayout(baud_card)
        baud_card_layout.setContentsMargins(4, 2, 4, 2)
        baud_card_layout.setSpacing(6)

        lbl_baud = QtWidgets.QLabel("BAUD")
        lbl_baud.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent;")
        baud_card_layout.addWidget(lbl_baud)

        self.baud_input = QtWidgets.QLineEdit(str(BAUD_DEFAULT))
        self.baud_input.setFixedWidth(75)
        self.baud_input.setStyleSheet("background-color: #171920; border: 1px solid #3a4150;")
        baud_card_layout.addWidget(self.baud_input)
        top_layout.addWidget(baud_card, 0, 2)

        # Tarjeta Resolución ADC
        adc_card = QtWidgets.QFrame()
        adc_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        adc_card_layout = QtWidgets.QHBoxLayout(adc_card)
        adc_card_layout.setContentsMargins(4, 2, 4, 2)
        adc_card_layout.setSpacing(6)

        lbl_adc = QtWidgets.QLabel("ADC")
        lbl_adc.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent;")
        adc_card_layout.addWidget(lbl_adc)

        self.adc_combo = QtWidgets.QComboBox()
        self.adc_combo.addItems([
            "12 bits (4095)",
            "10 bits (1023)",
            "8 bits (255)",
            "14 bits (16383)",
            "16 bits (65535)",
        ])
        default_adc_text = f"{ADC_BITS_DEFAULT} bits ({int((1 << ADC_BITS_DEFAULT) - 1)})"
        self.adc_combo.setCurrentText(default_adc_text)
        self.adc_combo.setToolTip("Resolución del Convertidor Analógico-Digital (ADC)\nEscala el valor raw de 0 a 3.3V")
        self.adc_combo.setStyleSheet("""
            QComboBox {
                background-color: #171920;
                border: 1px solid #3a4150;
                color: #00e5ff;
                font-weight: bold;
                font-size: 11px;
                padding: 2px 4px;
            }
        """)
        self.adc_combo.currentTextChanged.connect(self._on_adc_bits_changed)
        adc_card_layout.addWidget(self.adc_combo)
        top_layout.addWidget(adc_card, 0, 3)

        self.connect_button = QtWidgets.QPushButton("Conectar")
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #00838f;
                border: 1px solid #00acc1;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #00acc1;
            }
        """)
        self.connect_button.clicked.connect(self.connect_serial)
        top_layout.addWidget(self.connect_button, 1, 0)

        self.demo_button = QtWidgets.QPushButton("Demo (2 CH)")
        self.demo_button.setToolTip("Generador de prueba 2 Canales (V_IN y V_OUT)")
        self.demo_button.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                border: 1px solid #1e88e5;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
        """)
        self.demo_button.clicked.connect(self.start_demo)
        top_layout.addWidget(self.demo_button, 1, 1)


        self.status_label = StatusLabel("Listo")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 4px 10px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)
        top_layout.addWidget(self.status_label, 4, 0, 1, 4)

        destination_card = QtWidgets.QFrame()
        destination_card.setStyleSheet("background:#21252f;border:1px solid #2e3543;border-radius:6px;")
        destination_layout = QtWidgets.QGridLayout(destination_card)
        destination_layout.setContentsMargins(6, 4, 6, 4)
        destination_layout.addWidget(QtWidgets.QLabel('DESTINO'), 0, 0)
        self.destination_combo = QtWidgets.QComboBox()
        self.destination_combo.addItem('SPI · UNO Q', int(Mode.SPI))
        self.destination_combo.addItem('UART · R4', int(Mode.UART))
        self.destination_combo.setToolTip('Elegir por dónde salen las muestras. El Q conserva el control por USB.')
        self.destination_combo.currentIndexChanged.connect(self._destination_changed)
        destination_layout.addWidget(self.destination_combo, 0, 1)
        destination_layout.addWidget(QtWidgets.QLabel('PUERTO R4'), 1, 0)
        self.r4_combo = QtWidgets.QComboBox()
        self.r4_combo.setMinimumWidth(0)
        self.r4_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.r4_combo.setToolTip('Puerto USB del R4 con puente V5 y cableado UART al Q.')
        self.r4_combo.setEnabled(False)
        destination_layout.addWidget(self.r4_combo, 1, 1, 1, 2)
        self.confirmed_output_label = QtWidgets.QLabel('Destino confirmado: sin conexión')
        self.confirmed_output_label.setWordWrap(True)
        self.confirmed_output_label.hide()
        self.configuration_panel = destination_card
        top_layout.addWidget(destination_card, 4, 0, 1, 4)
        top_layout.addWidget(self.status_label, 5, 0, 1, 4)
        self.output_pending = False
        # The only editable hardware selections live inside this panel.
        port_card_layout.removeWidget(self.port_combo)
        port_card_layout.removeWidget(self.refresh_button)
        self.control_summary_label = QtWidgets.QLabel('Sin conexión')
        port_card_layout.addWidget(self.control_summary_label, 1)
        destination_layout.addWidget(QtWidgets.QLabel('CONTROL Q'), 2, 0)
        destination_layout.addWidget(self.port_combo, 2, 1)
        destination_layout.addWidget(self.refresh_button, 2, 2)
        destination_layout.addWidget(QtWidgets.QLabel('BITS ADC'), 3, 0)
        self.config_bits_combo = QtWidgets.QComboBox()
        for bits in BITS: self.config_bits_combo.addItem('16 bits · (OS)' if bits == 16 else f'{bits} bits', bits)
        self.config_bits_combo.setToolTip('16 bits: oversampling por hardware de 16 conversiones de 14 bits.\nMáximo 62,5 kHz SPI / 31,25 kHz UART; promedia ruido y señales rápidas.\nNo garantiza 16 bits de precisión analógica.')
        self.config_bits_combo.setCurrentIndex(self.config_bits_combo.findData(14))
        destination_layout.addWidget(self.config_bits_combo, 3, 1, 1, 2)
        destination_layout.addWidget(QtWidgets.QLabel('TASA'), 4, 0)
        self.config_rate_combo = QtWidgets.QComboBox()
        self.config_rate_combo.setToolTip('T: período entre pares de muestras.\nAdq: tiempo de carga del capacitor por canal y subconversión.\nUna ventana más corta exige menor impedancia de fuente para conservar el asentamiento.\nEn 16 bits se realizan 16 subconversiones por canal.')
        for rate in RATES:
            label = f'{number(rate/1000, formats.ng)}' + f' kHz · {1000000//rate} µs'
            config = Configuration(14, rate)
            if rate > 31250: label += f' · SPI · ADC {number(config.sampling_us, formats.ng)} µs'
            self.config_rate_combo.addItem(label, rate)
        self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(40000))
        destination_layout.addWidget(self.config_rate_combo, 4, 1, 1, 2)
        self.configuration_note = QtWidgets.QLabel('Bits o tasa: nueva captura y cierre de la grabación. Sólo salida: captura continua.')
        self.configuration_note.setText(self.configuration_note.text() + '\n16 bits: la ventana ADC se acorta al subir la tasa; precisión dependiente de la impedancia.')
        self.configuration_note.setWordWrap(True)
        destination_layout.addWidget(QtWidgets.QLabel('DETALLE / FPS'), 5, 0)
        detail_row = QtWidgets.QHBoxLayout()
        detail_row.addWidget(QtWidgets.QLabel('Más FPS'))
        self.detail_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.detail_slider.setRange(0, 100)
        self.detail_slider.setValue(50)
        self.detail_slider.setToolTip('Ajuste visual en vivo. A la derecha conserva más puntos; al máximo dibuja todas las muestras. No cambia adquisición, mediciones ni CSV.')
        detail_row.addWidget(self.detail_slider, 1)
        detail_row.addWidget(QtWidgets.QLabel('Más detalle'))
        self.detail_value_label = QtWidgets.QLabel('50 %')
        detail_row.addWidget(self.detail_value_label)
        destination_layout.addLayout(detail_row, 5, 1, 1, 2)
        self.detail_slider.valueChanged.connect(self._detail_changed)
        destination_layout.addWidget(self.configuration_note, 6, 0, 1, 3)
        adc_card_layout.removeWidget(self.adc_combo)
        self.adc_combo.hide()
        self.adc_summary_label = QtWidgets.QLabel('—')
        adc_card_layout.addWidget(self.adc_summary_label)
        # Main-screen selectors: compact rows, no folding configuration panel.
        port_card_layout.removeWidget(self.control_summary_label)
        self.control_summary_label.hide()
        port_card_layout.addWidget(self.port_combo, 1)
        port_card_layout.addWidget(self.refresh_button)
        adc_card_layout.removeWidget(self.adc_summary_label)
        self.adc_summary_label.hide()
        self.config_bits_combo.setMinimumWidth(0)
        self.config_bits_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        lbl_adc.setFixedWidth(38)
        adc_card_layout.addWidget(self.config_bits_combo, 1)
        # Reserve only the arrow width, leaving the rest for the selected text.
        compact_selector_style = """
            QComboBox {
                background-color: #171920;
                border: 1px solid #3a4150;
                border-radius: 5px;
                padding: 2px 16px 2px 4px;
            }
            QComboBox::drop-down {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 14px;
                border: none;
            }
        """
        self.config_bits_combo.setStyleSheet(compact_selector_style)
        self.port_combo.setStyleSheet(compact_selector_style)

        while destination_layout.count():
            item = destination_layout.takeAt(0)
            if item.widget() is not None: item.widget().hide()
        destination_layout.addWidget(QtWidgets.QLabel('SALIDA'), 0, 0)
        destination_layout.addWidget(self.destination_combo, 0, 1)
        destination_layout.addWidget(QtWidgets.QLabel('TASA'), 0, 2)
        destination_layout.addWidget(self.config_rate_combo, 0, 3)
        destination_layout.addWidget(QtWidgets.QLabel('R4'), 1, 0)
        destination_layout.addWidget(self.r4_combo, 1, 1)
        destination_layout.addWidget(QtWidgets.QLabel('DETALLE / FPS'), 1, 2)
        destination_layout.addLayout(detail_row, 1, 3, 1, 2)
        for widget in (self.port_combo, self.refresh_button, self.config_bits_combo,
                       self.destination_combo, self.config_rate_combo,
                       self.r4_combo): widget.show()
        self.config_rate_combo.setMinimumWidth(0)
        self.config_rate_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.configuration_panel.show()

        # Tarjeta Fs Muestreo (Ancho fijo rígido)
        fs_card = QtWidgets.QFrame()
        fs_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        fs_card_layout = QtWidgets.QHBoxLayout(fs_card)
        fs_card_layout.setContentsMargins(6, 2, 6, 2)
        fs_card_layout.setSpacing(6)

        lbl_fs = QtWidgets.QLabel("MUESTREO")
        lbl_fs.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl_fs.setFixedWidth(58)
        lbl_fs.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent; border: none; padding: 0;")
        fs_card_layout.addWidget(lbl_fs)

        self.lbl_top_fs = QtWidgets.QLabel("-- S/s")
        self.lbl_top_fs.setFixedWidth(90)
        self.lbl_top_fs.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_top_fs.setToolTip("Frecuencia de muestreo en tiempo real")
        self.lbl_top_fs.setStyleSheet("""
            background-color: #171920;
            border: 1px solid #00e5ff;
            border-radius: 4px;
            padding: 2px 4px;
            font-weight: bold;
            font-size: 11px;
            color: #00e5ff;
        """)
        fs_card_layout.addWidget(self.lbl_top_fs)
        top_layout.addWidget(fs_card, 2, 0, 1, 2)

        # Use each existing status card as its own configuration control.
        baud_card_layout.removeWidget(self.baud_input)
        self.baud_input.hide()
        baud_card_layout.addWidget(self.destination_combo, 1)
        baud_card_layout.addWidget(self.r4_combo, 1)
        self.destination_combo.setMinimumWidth(0)
        fs_card_layout.removeWidget(self.lbl_top_fs)
        self.lbl_top_fs.hide()
        fs_card_layout.addWidget(self.config_rate_combo, 1)
        while destination_layout.count():
            item = destination_layout.takeAt(0)
            if item.widget() is not None: item.widget().hide()
        destination_layout.addWidget(QtWidgets.QLabel('DETALLE / FPS'), 0, 0)
        destination_layout.addLayout(detail_row, 0, 1, 1, 3)
        self.prepare_q_button = QtWidgets.QPushButton('Preparar Q')
        self.prepare_q_button.setToolTip('Instala o actualiza V12 Audio: app, firmware MCU y relay en el Q seleccionado. Guarda respaldo de la app existente.')
        self.prepare_q_button.clicked.connect(self.prepare_q)
        destination_layout.addWidget(self.prepare_q_button, 1, 3)
        self._q_preparation = None
        self.destination_combo.show()
        self.config_rate_combo.show()
        self._destination_changed()
        self.config_bits_combo.currentIndexChanged.connect(self._destination_changed)
        self._auto_apply_timer = QtCore.QTimer(self)
        self._auto_apply_timer.setSingleShot(True)
        self._auto_apply_timer.setInterval(50)
        self._auto_apply_timer.timeout.connect(self._auto_apply_configuration)
        for combo in (self.destination_combo, self.r4_combo, self.config_bits_combo, self.config_rate_combo):
            combo.currentIndexChanged.connect(self._schedule_configuration)

        # Botón toggle Eje X: Muestras ↔ Tiempo µs (ancho fijo para no desplazar layout)
        self.btn_xaxis_toggle = QtWidgets.QPushButton("Muestras")
        self.btn_xaxis_toggle.setCheckable(True)
        self.btn_xaxis_toggle.setChecked(False)
        self.btn_xaxis_toggle.setToolTip(
            "Alterna el eje X entre índice de muestra y tiempo real (µs)\n"
            "Requiere datos en la columna 'Tiempo (us)'"
        )
        self.btn_xaxis_toggle.setStyleSheet("""
            QPushButton {
                background-color: #21252f;
                border: 1px solid #323946;
                border-radius: 6px;
                padding: 5px 8px;
                color: #8f98a8;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:checked {
                background-color: rgba(0, 229, 255, 0.12);
                border: 1px solid #00e5ff;
                color: #00e5ff;
            }
            QPushButton:hover { background-color: #2a2f3c; }
        """)
        self.btn_xaxis_toggle.toggled.connect(self._on_xaxis_toggle)
        top_layout.addWidget(self.btn_xaxis_toggle, 1, 3)

        # Tarjeta Trazo (Línea / Escalón) y Corte Automático de Silencios
        trace_card = QtWidgets.QFrame()
        trace_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        trace_card_layout = QtWidgets.QHBoxLayout(trace_card)
        trace_card_layout.setContentsMargins(6, 2, 6, 2)
        trace_card_layout.setSpacing(6)

        lbl_trace = QtWidgets.QLabel("TRAZO")
        lbl_trace.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent;")
        trace_card_layout.addWidget(lbl_trace)

        self.trace_mode_combo = QtWidgets.QComboBox()
        self.trace_mode_combo.addItems(["Escalón (Step)", "Línea (Linear)"])
        self.trace_mode_combo.setCurrentText("Escalón (Step)")
        self.trace_mode_combo.setToolTip(
            "Tipo de representación del trazo:\n"
            "• Escalón (Step / ZOH): Mantiene el nivel y evita diagonales falsas\n"
            "• Línea (Linear): Conexión directa punto a punto"
        )
        self.trace_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #171920;
                border: 1px solid #3a4150;
                color: #00e5ff;
                font-weight: bold;
                font-size: 11px;
                padding: 2px 4px;
            }
        """)
        self.trace_mode_combo.currentTextChanged.connect(self._on_trace_mode_changed)
        trace_card_layout.addWidget(self.trace_mode_combo)

        self.trace_style_combo = QtWidgets.QComboBox()
        self.trace_style_combo.addItems(["Rápido", "Intenso", "Suave"])
        self.trace_style_combo.setStyleSheet(self.trace_mode_combo.styleSheet())
        self.trace_style_combo.setToolTip(
            "Rápido: trazo fino sin suavizado, menor costo de dibujo.\n"
            "Intenso: trazo de 2 píxeles para mayor visibilidad; puede reducir FPS.\n"
            "Suave: trazo fino con suavizado, como en la versión anterior."
        )
        self.trace_style_combo.currentTextChanged.connect(self._on_trace_style_changed)
        trace_card_layout.addWidget(self.trace_style_combo)

        self.chk_auto_gap = QtWidgets.QCheckBox("Corte Auto")
        self.chk_auto_gap.setChecked(True)
        self.chk_auto_gap.setToolTip(
            "Corte automático de silencios:\n"
            "Interrumpe la traza si se detecta un salto o pausa en el tiempo\n"
            "para no unir eventos desconectados con diagonales o líneas continuas."
        )
        self.chk_auto_gap.setStyleSheet("""
            QCheckBox {
                font-size: 10px;
                font-weight: bold;
                color: #ffd600;
                background: transparent;
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border-radius: 3px;
                border: 1px solid #3a4252;
                background-color: #171920;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #4f586c;
            }
            QCheckBox::indicator:checked {
                background-color: #ffd600;
                border: 1px solid #3a4252;
            }
        """)
        self.chk_auto_gap.stateChanged.connect(self._on_auto_gap_changed)
        trace_card_layout.addWidget(self.chk_auto_gap)

        top_layout.addWidget(trace_card, 2, 2, 1, 2)

        # Compact control/connect/demo columns; equal wider link/ADC columns.
        for column, stretch in enumerate((2, 2, 3, 3)):
            top_layout.setColumnStretch(column, stretch)
            top_layout.setColumnMinimumWidth(column, 100 if column < 2 else 180)
        for button in (self.connect_button, self.demo_button,
                       self.prepare_q_button, self.btn_xaxis_toggle):
            button.setFixedHeight(34)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        for card in (port_card, baud_card, adc_card, fs_card, trace_card):
            card.setFixedHeight(34)
        # Match the acquisition panel's two 34 px rows and 8 px gap.
        top_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        top_layout.setRowMinimumHeight(0, 34)
        top_layout.setRowMinimumHeight(1, 34)
        self.status_label.setMinimumWidth(0)
        self.status_label.setWordWrap(False)
        self.status_label.setFixedHeight(34)
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        self.port_combo.setMinimumWidth(0)
        self.port_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        refresh_btn.setFixedSize(28, 28)
        # Temporal display controls belong to the V/t mode panel.
        top_layout.removeWidget(self.btn_xaxis_toggle)
        top_layout.addWidget(fs_card, 1, 3)
        top_layout.removeWidget(trace_card)
        trace_card.hide()
        top_layout.removeWidget(destination_card)
        destination_card.hide()
        destination_layout.removeWidget(self.prepare_q_button)
        top_layout.addWidget(self.prepare_q_button, 1, 2)
        self.prepare_q_button.setFixedHeight(34)
        self.prepare_q_button.show()
        self._set_connect_state('disconnected')
        destination_layout.removeItem(detail_row)
        self.temporal_settings = QtWidgets.QWidget()
        temporal_form = QtWidgets.QFormLayout(self.temporal_settings)
        temporal_form.setContentsMargins(0,0,0,0)
        temporal_form.setVerticalSpacing(4)
        temporal_form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        for control in (self.btn_xaxis_toggle,self.trace_mode_combo,self.trace_style_combo):
            control.setFixedHeight(24)
        self.btn_xaxis_toggle.setStyleSheet(self.btn_xaxis_toggle.styleSheet().replace('padding: 5px 8px;', 'padding: 2px 6px;'))
        temporal_form.addRow('Eje horizontal', self.btn_xaxis_toggle)
        temporal_form.addRow('Trazo', self.trace_mode_combo)
        temporal_form.addRow('Estilo', self.trace_style_combo)
        temporal_form.addRow(self.chk_auto_gap)
        temporal_form.addRow('Detalle / FPS', self.detail_value_label)
        temporal_form.addRow(self.detail_slider)
        for widget in (self.btn_xaxis_toggle,self.trace_mode_combo,self.trace_style_combo,
                       self.chk_auto_gap,self.detail_value_label,self.detail_slider): widget.show()

        left_layout.addWidget(top_group)
        self._build_generator_panel(generator_layout)

        # 2. Pantalla de Osciloscopio (PyQtGraph)
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': LocaleAxis('bottom'), 'left': LocaleAxis('left')})
        self.temporal_single_marker = pg.TextItem('SINGLE', color='#ff9f43', anchor=(1,0), fill=pg.mkBrush('#24201b'))
        self.temporal_single_marker.setZValue(100)
        self.plot_widget.addItem(self.temporal_single_marker, ignoreBounds=True)
        self.temporal_single_marker.hide()
        def position_single(view, ranges, *args):
            self.temporal_single_marker.setPos(ranges[0][1], ranges[1][1])
        self.plot_widget.getViewBox().sigRangeChanged.connect(position_single)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
        self.plot_widget.setTitle("SCOPE V13 - V_IN [A2] / V_OUT [A3]")
        self.plot_widget.getAxis("bottom").setTextPen("#ffffff")
        self.plot_widget.getAxis("left").setTextPen("#ffffff")
        self.plot_widget.setLabel("bottom", "Muestras en ventana", color="#ffffff")
        self.plot_widget.setLabel("left", "Amplitud (V)", color="#ffffff")
        self.plot_widget.setYRange(0, self.v_scale, padding=0.02)
        self.plot_widget.setXRange(0, self.h_scale, padding=0.0)

        # Línea horizontal interactiva de Trigger Level
        self.trigger_line = pg.InfiniteLine(
            pos=self.trigger_level,
            angle=0,
            movable=True,
            pen=pg.mkPen(color="#ff9100", width=1.8, style=QtCore.Qt.PenStyle.DashLine),
            label="Trig: {value:.2f}V",
            labelOpts={"position": 0.95, "color": "#ffffff", "fill": (255, 145, 0, 200)},
        )
        self.trigger_line.sigPositionChanged.connect(self._on_trigger_line_dragged)
        self.trigger_line.setVisible(False)
        self.plot_widget.addItem(self.trigger_line)

        # Línea vertical fija de punto de disparo T (en X = 0 en modo Trigger)
        self.trigger_t_marker = pg.InfiniteLine(
            pos=0,
            angle=90,
            movable=False,
            pen=pg.mkPen(color="#ff9100", width=1.2, style=QtCore.Qt.PenStyle.DotLine),
            label="T",
            labelOpts={"position": 0.05, "color": "#ff9100", "fill": (20, 22, 26, 180)},
        )
        self.trigger_t_marker.setVisible(False)
        self.plot_widget.addItem(self.trigger_t_marker)

        self.legend = self.plot_widget.addLegend(offset=(15, 15))
        self.line_items: Dict[str, pg.PlotDataItem] = {}
        self.display_stack = QtWidgets.QStackedWidget()
        self.display_stack.addWidget(self.plot_widget)
        left_layout.addWidget(self.display_stack, 1)
        self.spectral = SpectralDisplay(self, instrument_layout, self.display_stack)
        instrument_layout.addWidget(InstrumentLogo(instrument_column), alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        # 3. Barra de Mediciones en Vivo con Selector de Canal
        self.measurements_box = QtWidgets.QFrame()
        self.measurements_box.setStyleSheet("""
            QFrame {
                background-color: #181b22;
                border: 1px solid #282d37;
                border-radius: 8px;
                padding: 4px 6px;
            }
        """)
        meas_layout = QtWidgets.QHBoxLayout(self.measurements_box)
        meas_layout.setContentsMargins(6, 4, 6, 4)
        meas_layout.setSpacing(8)

        # Selector de canal para medición
        meas_title_frame = QtWidgets.QFrame()
        meas_title_frame.setStyleSheet("border: none; background: transparent;")
        mtf_layout = QtWidgets.QVBoxLayout(meas_title_frame)
        mtf_layout.setContentsMargins(2, 2, 2, 2)
        mtf_layout.setSpacing(2)
        lbl_m1 = QtWidgets.QLabel("Medición")
        lbl_m1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        meas_title_frame.setFixedWidth(94)
        lbl_m1.setStyleSheet("font-size: 12px; font-weight: 800; color: #00e5ff; letter-spacing: 0.5px;")
        
        self.meas_channel_combo = GeneratorComboBox()
        self.meas_channel_combo.setProperty("centerInWholeBox", True)
        self.meas_channel_combo.setProperty("selectedTextColor", self.channel_colors.get("V_IN", "#00e5ff"))
        popup = QtWidgets.QListView(self.meas_channel_combo)
        popup.setItemDelegate(NeutralMeasurementDelegate(self.config_bits_combo.view(), popup))
        popup.setUniformItemSizes(True)
        popup.setSpacing(0)

        popup.setStyleSheet("QListView {background-color:#1a1d24; color:#ffffff; border:1px solid #323946;} QListView::item {background-color:#1a1d24; color:#ffffff; padding:4px 8px;} QListView::item:selected {background-color:#323946; color:#ffffff;}")
        self.meas_channel_combo.setView(popup)
        self.meas_channel_combo.addItems(["V_OUT", "V_IN", "ADC_OUT", "ADC_IN"])
        self.meas_channel_combo.setCurrentText("V_IN")
        for index in range(self.meas_channel_combo.count()):
            self.meas_channel_combo.setItemData(index, QtCore.Qt.AlignmentFlag.AlignCenter,
                                               QtCore.Qt.ItemDataRole.TextAlignmentRole)
        self.meas_channel_combo.setStyleSheet("""
            QComboBox {
                background-color: #21252f;
                border: 1px solid #3a4150;
                font-weight: bold;
                font-size: 11px;
                padding: 2px 6px;
            }
        """)
        self.meas_channel_combo.currentTextChanged.connect(self._on_meas_channel_changed)
        mtf_layout.addWidget(lbl_m1)
        mtf_layout.addWidget(self.meas_channel_combo)
        meas_layout.addWidget(meas_title_frame)

        # Tarjetas de datos de medición
        card_vmax, self.val_vmax = self._create_meas_card("V MAX", "#00e676")
        card_vmin, self.val_vmin = self._create_meas_card("V MIN", "#ff5252")
        card_vpp, self.val_vpp = self._create_meas_card("V P-P", "#ffd600")
        card_vrms, self.val_vrms = self._create_meas_card("V RMS", "#00e5ff")
        card_vavg, self.val_vavg = self._create_meas_card("V MEDIA", "#b388ff")
        card_freq, self.val_freq = self._create_meas_card("F SEÑAL", "#ff9100")

        meas_layout.addWidget(card_vmax, 1)
        meas_layout.addWidget(card_vmin, 1)
        meas_layout.addWidget(card_vpp, 1)
        meas_layout.addWidget(card_vrms, 1)
        meas_layout.addWidget(card_vavg, 1)
        meas_layout.addWidget(card_freq, 1)

        left_layout.addWidget(self.measurements_box)

        # 4. Panel de Canales con tarjetas modulares por canal
        self.columns_panel = QtWidgets.QGroupBox("CANALES Y SEÑALES ACTIVAS")
        self.columns_layout = QtWidgets.QHBoxLayout(self.columns_panel)
        self.columns_layout.setSpacing(10)
        self._rebuild_column_controls(self.known_columns)
        left_layout.addWidget(self.columns_panel)

        main_h_layout.addWidget(left_widget, 4)

        # -------------------------------------------------------------
        # COLUMNA DERECHA: PANEL FRONTAL OSCILOSCOPIO
        # -------------------------------------------------------------
        panel_widget = QtWidgets.QWidget()
        panel_widget.setFixedWidth(310)
        panel_layout = QtWidgets.QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(8)

        # 1. ADQUISICIÓN
        acq_group = QtWidgets.QGroupBox("ADQUISICIÓN")
        acq_layout = QtWidgets.QVBoxLayout(acq_group)
        acq_layout.setSpacing(8)

        btn_row = QtWidgets.QHBoxLayout()
        self.run_stop_btn = QtWidgets.QPushButton("▶ RUN")
        self.run_stop_btn.setCheckable(True)
        self.run_stop_btn.setChecked(True)
        self.run_stop_btn.setFixedHeight(34)
        self.run_stop_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #1b5e20;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #00e676;
            }
            QPushButton:!checked {
                background-color: #b71c1c;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ff5252;
            }
        """)
        self.run_stop_btn.clicked.connect(self.toggle_run_stop)
        btn_row.addWidget(self.run_stop_btn)

        self.single_btn = QtWidgets.QPushButton("⚡ SINGLE")
        self.single_btn.setFixedHeight(34)
        self.single_btn.setCheckable(True)
        self._set_single_state('idle')
        self.single_btn.clicked.connect(self.arm_single_shot)
        btn_row.addWidget(self.single_btn)
        acq_layout.addLayout(btn_row)

        format_row = QtWidgets.QHBoxLayout()
        self.record_format_combo = GeneratorComboBox()
        self.record_format_combo.setProperty("centerInWholeBox", True)
        self.record_format_combo.addItems(["CSV", "WAV"])
        self.record_format_combo.setFixedSize(56, 34)
        self.record_format_combo.setStyleSheet("QComboBox {padding:2px 13px 2px 4px;} QComboBox::drop-down {width:12px; border:none;}")
        self.record_format_combo.currentTextChanged.connect(self._record_format_changed)
        self.record_format_combo.setToolTip("WAV estéreo PCM16: A2 izquierda, A3 derecha. Centro fijo en mitad del rango ADC; eliminación DC opcional, sin normalización. Tasa confirmada del Q.")
        format_row.addWidget(self.record_format_combo)
        record_row = QtWidgets.QHBoxLayout()
        self.record_btn = QtWidgets.QPushButton("RECORD")
        self.record_btn.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v13/assets/record.svg')))
        self.record_btn.setIconSize(QtCore.QSize(16, 16))
        self.record_btn.setFixedHeight(self.run_stop_btn.height())
        self.record_btn.setToolTip("Iniciar grabación en el formato elegido, máximo 30 segundos")
        self.record_btn.setStyleSheet("QPushButton {background:#7f0000;border:1px solid #ff5252;color:white;font-weight:bold;font-size:14px;} QPushButton:hover {background:#b71c1c;} QPushButton:disabled {background:#1e222b;color:#555e6d;}")
        self.record_btn.clicked.connect(self.start_recording)
        record_row.addWidget(self.record_btn)
        self.stop_record_btn = QtWidgets.QPushButton("■ STOP REC")
        self.stop_record_btn.setFixedHeight(self.run_stop_btn.height())
        self.stop_record_btn.setEnabled(False)
        self.stop_record_btn.setToolTip("Detener y cerrar el archivo de grabación")
        self.stop_record_btn.setStyleSheet("QPushButton {font-size:14px;font-weight:bold;} QPushButton:enabled {background:#b71c1c;border:1px solid #ff5252;color:white;font-weight:bold;} QPushButton:disabled {background:#1e222b;color:#555e6d;}")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        record_row.addWidget(self.stop_record_btn)
        acq_layout.addLayout(record_row)
        self.record_status_label = QtWidgets.QLabel("CSV: listo | máximo 30.0 s")
        self.record_status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.record_status_label.setStyleSheet("background:#171920;border:1px solid #323946;padding:4px;color:#aeb8c8;font-weight:normal;")
        self.record_status_label.setFixedHeight(34)
        self.record_status_label.setMinimumWidth(0)
        self.record_status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        format_row.addWidget(self.record_status_label, 1)
        acq_layout.addLayout(format_row)
        self.record_dc_checkbox = QtWidgets.QCheckBox('Eliminar DC · WAV')
        check_icon = (ROOT / 'monitor/v13/assets/check_neutral.svg').as_posix()
        self.record_dc_checkbox.setStyleSheet(f"""
            QCheckBox {{ background:transparent; border:none; spacing:6px; }}
            QCheckBox::indicator {{ width:14px; height:14px; border:1px solid #737d8d;
                border-radius:3px; background:#171920; }}
            QCheckBox::indicator:checked {{ image:url("{check_icon}"); background:#171920; }}
            QCheckBox::indicator:unchecked {{ image:none; background:#171920; }}
            QCheckBox:disabled {{ color:#697180; }}
            QCheckBox::indicator:disabled {{ border-color:#424957; }}
        """)
        self.record_dc_checkbox.setChecked(True)
        self.record_dc_checkbox.setEnabled(False)
        self.record_dc_checkbox.setToolTip('Pasaaltos continuo de 5 Hz por canal. Atenúa DC y señales muy lentas; mantiene estado entre lotes. CSV conserva las muestras originales.')
        acq_layout.addWidget(self.record_dc_checkbox)

        mode_row = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("Modo:")
        mode_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        mode_row.addWidget(mode_label)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Auto", "Normal"])
        self.mode_combo.currentTextChanged.connect(self.on_trigger_mode_changed)
        mode_row.addWidget(self.mode_combo)

        reset_view_btn = QtWidgets.QPushButton("Auto-Set")
        reset_view_btn.setToolTip("Restablecer escalas por defecto")
        reset_view_btn.setStyleSheet("background-color: #2d3342; color: #00e5ff; font-weight: bold; border: 1px solid #3d465a;")
        reset_view_btn.clicked.connect(self.reset_all_controls)
        mode_row.addWidget(reset_view_btn)
        acq_layout.addLayout(mode_row)

        panel_layout.addWidget(acq_group)

        # 2. HORIZONTAL
        horiz_group = QtWidgets.QGroupBox("HORIZONTAL")
        horiz_layout = QtWidgets.QGridLayout(horiz_group)

        lbl_h_s = QtWidgets.QLabel("ESCALA")
        lbl_h_s.setStyleSheet("font-weight: bold; color: #ffffff;")
        horiz_layout.addWidget(lbl_h_s, 0, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_h_scale = InstrumentDial()
        self.dial_h_scale.setRange(VISIBLE_SAMPLES_MIN, VISIBLE_SAMPLES_MAX)
        self.dial_h_scale.setValue(VISIBLE_SAMPLES_DEFAULT)
        self.dial_h_scale.setNotchesVisible(True)
        self.dial_h_scale.setNotchTarget(7.0)
        self.dial_h_scale.valueChanged.connect(self.on_h_scale_changed)
        horiz_layout.addWidget(self.dial_h_scale, 1, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.lbl_h_scale = QtWidgets.QDoubleSpinBox()
        self.lbl_h_scale.setDecimals(0)
        self.lbl_h_scale.setRange(VISIBLE_SAMPLES_MIN, VISIBLE_SAMPLES_MAX)
        self.lbl_h_scale.setValue(VISIBLE_SAMPLES_DEFAULT)
        self.lbl_h_scale.setSuffix(" smp")
        self.lbl_h_scale.setGroupSeparatorShown(True)
        self.lbl_h_scale.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.lbl_h_scale.setKeyboardTracking(False)
        self.lbl_h_scale.valueChanged.connect(self._on_h_scale_input)
        self.lbl_h_scale.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_h_scale.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #282d37;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
            font-size: 12px;
            color: #00e5ff;
        """)
        horiz_layout.addWidget(self.lbl_h_scale, 2, 0)

        lbl_h_p = QtWidgets.QLabel("POSICIÓN")
        lbl_h_p.setStyleSheet("font-weight: bold; color: #ffffff;")
        horiz_layout.addWidget(lbl_h_p, 0, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_h_pos = InstrumentDial()
        self.dial_h_pos.setRange(-VISIBLE_SAMPLES_MAX, 0)
        self.dial_h_pos.setValue(0)
        self.dial_h_pos.setNotchesVisible(True)
        self.dial_h_pos.setNotchTarget(7.0)
        self.dial_h_pos.valueChanged.connect(self.on_h_pos_changed)
        horiz_layout.addWidget(self.dial_h_pos, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.lbl_h_pos = QtWidgets.QLabel("0 smp (Live)")
        self.lbl_h_pos.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_h_pos.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #282d37;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
            font-size: 12px;
            color: #00e5ff;
        """)
        horiz_layout.addWidget(self.lbl_h_pos, 2, 1)

        panel_layout.addWidget(horiz_group)

        # 3. VERTICAL
        vert_group = QtWidgets.QGroupBox("VERTICAL")
        vert_layout = QtWidgets.QGridLayout(vert_group)

        lbl_v_s = QtWidgets.QLabel("ESCALA (V)")
        lbl_v_s.setStyleSheet("font-weight: bold; color: #ffffff;")
        vert_layout.addWidget(lbl_v_s, 0, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_v_scale = InstrumentDial()
        self.dial_v_scale.setRange(50, 1000)
        self.dial_v_scale.setValue(330)
        self.dial_v_scale.setNotchesVisible(True)
        self.dial_v_scale.setNotchTarget(7.0)
        self.dial_v_scale.valueChanged.connect(self.on_v_scale_changed)
        vert_layout.addWidget(self.dial_v_scale, 1, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.lbl_v_scale = QtWidgets.QDoubleSpinBox()
        self.lbl_v_scale.setRange(0.5, 10)
        self.lbl_v_scale.setDecimals(2)
        self.lbl_v_scale.setValue(3.3)
        self.lbl_v_scale.setSuffix(" V")
        self.lbl_v_scale.setGroupSeparatorShown(True)
        self.lbl_v_scale.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.lbl_v_scale.setKeyboardTracking(False)
        self.lbl_v_scale.valueChanged.connect(lambda value: self.dial_v_scale.setValue(round(value * 100)))
        self.lbl_v_scale.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_v_scale.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #282d37;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
            font-size: 12px;
            color: #ffd600;
        """)
        vert_layout.addWidget(self.lbl_v_scale, 2, 0)

        lbl_v_p = QtWidgets.QLabel("POSICIÓN (V)")
        lbl_v_p.setStyleSheet("font-weight: bold; color: #ffffff;")
        vert_layout.addWidget(lbl_v_p, 0, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_v_pos = InstrumentDial()
        self.dial_v_pos.setRange(-500, 500)
        self.dial_v_pos.setValue(0)
        self.dial_v_pos.setNotchesVisible(True)
        self.dial_v_pos.setNotchTarget(7.0)
        self.dial_v_pos.valueChanged.connect(self.on_v_pos_changed)
        vert_layout.addWidget(self.dial_v_pos, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.lbl_v_pos = QtWidgets.QLabel("0.00 V")
        self.lbl_v_pos.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_v_pos.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #282d37;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
            font-size: 12px;
            color: #ffd600;
        """)
        vert_layout.addWidget(self.lbl_v_pos, 2, 1)

        panel_layout.addWidget(vert_group)

        # 4. TRIGGER
        trig_group = QtWidgets.QGroupBox("TRIGGER")
        trig_layout = QtWidgets.QVBoxLayout(trig_group)
        trig_layout.setSpacing(6)

        # Fila 1: Checkbox de Activación y Botón Auto 50%
        act_card = QtWidgets.QFrame()
        act_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        act_layout = QtWidgets.QHBoxLayout(act_card)
        act_layout.setContentsMargins(6, 4, 6, 4)
        act_layout.setSpacing(8)

        self.trigger_checkbox = QtWidgets.QCheckBox("ACTIVAR TRIGGER")
        self.trigger_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: 800;
                font-size: 11px;
                color: #ff9100;
                background: transparent;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #3a4252;
                background-color: #171920;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #4f586c;
            }
            QCheckBox::indicator:checked {
                background-color: #ff9100;
                border: 1px solid #3a4252;
            }
        """)
        self.trigger_checkbox.stateChanged.connect(self.configure_trigger)
        act_layout.addWidget(self.trigger_checkbox)

        self.btn_auto_level = QtWidgets.QPushButton("50% (Auto)")
        self.btn_auto_level.setToolTip("Ajustar nivel de disparo al 50% de la fuente seleccionada")
        self.btn_auto_level.setStyleSheet("""
            QPushButton {
                background-color: #2c3240;
                border: 1px solid #ff9100;
                color: #ff9100;
                font-weight: bold;
                font-size: 10px;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 145, 0, 0.2);
            }
        """)
        self.btn_auto_level.clicked.connect(self.auto_center_trigger_level)
        act_layout.addWidget(self.btn_auto_level)
        trig_layout.addWidget(act_card)

        # Fila 2: Tarjeta FUENTE y Tarjeta FLANCO lado a lado
        config_row = QtWidgets.QHBoxLayout()
        config_row.setSpacing(6)

        # Tarjeta Fuente
        src_card = QtWidgets.QFrame()
        src_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        src_layout = QtWidgets.QVBoxLayout(src_card)
        src_layout.setContentsMargins(4, 3, 4, 3)
        src_layout.setSpacing(2)

        lbl_src_tag = QtWidgets.QLabel("FUENTE")
        lbl_src_tag.setStyleSheet("font-weight: 700; font-size: 9px; color: #8f98a8; background: transparent;")
        src_layout.addWidget(lbl_src_tag)

        self.trigger_source_combo = QtWidgets.QComboBox()
        self.trigger_source_combo.addItems(["V_IN", "V_OUT", "ADC_IN", "ADC_OUT"])
        self.trigger_source_combo.setCurrentText("V_IN")
        self.trigger_source_combo.setStyleSheet("background-color: #171920; border: 1px solid #3a4150; font-size: 11px;")
        self.trigger_source_combo.currentTextChanged.connect(self.on_trigger_source_changed)
        src_layout.addWidget(self.trigger_source_combo)
        config_row.addWidget(src_card, 1)

        # Tarjeta Flanco
        edge_card = QtWidgets.QFrame()
        edge_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        edge_layout = QtWidgets.QVBoxLayout(edge_card)
        edge_layout.setContentsMargins(4, 3, 4, 3)
        edge_layout.setSpacing(2)

        lbl_edge_tag = QtWidgets.QLabel("FLANCO")
        lbl_edge_tag.setStyleSheet("font-weight: 700; font-size: 9px; color: #8f98a8; background: transparent;")
        edge_layout.addWidget(lbl_edge_tag)

        self.trigger_edge_combo = QtWidgets.QComboBox()
        self.trigger_edge_combo.addItems(["Ascendente", "Descendente"])
        self.trigger_edge_combo.setCurrentText("Ascendente")
        self.trigger_edge_combo.setStyleSheet("background-color: #171920; border: 1px solid #3a4150; font-size: 11px;")
        self.trigger_edge_combo.currentTextChanged.connect(self.configure_trigger)
        edge_layout.addWidget(self.trigger_edge_combo)
        config_row.addWidget(edge_card, 1)

        trig_layout.addLayout(config_row)

        # Fila 3: Tarjeta NIVEL
        level_card = QtWidgets.QFrame()
        level_card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 4px 6px;
            }
        """)
        level_card_layout = QtWidgets.QVBoxLayout(level_card)
        level_card_layout.setContentsMargins(6, 4, 6, 4)
        level_card_layout.setSpacing(4)

        level_header_row = QtWidgets.QHBoxLayout()
        lbl_lvl_tag = QtWidgets.QLabel("NIVEL DE DISPARO")
        lbl_lvl_tag.setStyleSheet("font-weight: 700; font-size: 9px; color: #8f98a8; background: transparent;")
        level_header_row.addWidget(lbl_lvl_tag)

        self.lbl_trigger_level = QtWidgets.QLabel("1.65 V")
        self.lbl_trigger_level.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #ff9100;
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: bold;
            font-size: 12px;
            color: #ff9100;
        """)
        level_header_row.addWidget(self.lbl_trigger_level, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        level_card_layout.addLayout(level_header_row)

        self.dial_trigger_level = InstrumentDial()
        self.dial_trigger_level.setRange(0, 330)
        self.dial_trigger_level.setValue(165)
        self.dial_trigger_level.setNotchesVisible(True)
        self.dial_trigger_level.setNotchTarget(7.0)
        self.dial_trigger_level.valueChanged.connect(self.on_trigger_level_dial_changed)
        level_card_layout.addWidget(self.dial_trigger_level, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        trig_layout.addWidget(level_card)

        # Fila 4: Status label
        self.trigger_status_label = StatusLabel("● Modo continuo")
        self.trigger_status_label.setWordWrap(True)
        self.trigger_status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 6px;
                font-weight:normal;
                font-size: 11px;
                color:#aeb8c8;
            }
        """)
        trig_layout.addWidget(self.trigger_status_label)

        panel_layout.addWidget(trig_group)
        panel_layout.addStretch()

        main_h_layout.addWidget(panel_widget, 1)

    def _create_meas_card(self, title: str, color: str) -> Tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
        """Crea una tarjeta modular estilizada para una medición de osciloscopio."""
        card = QtWidgets.QFrame()
        card.setMinimumWidth(0)
        card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        card.setStyleSheet("""
            QFrame {
                background-color: #21252f;
                border: 1px solid #2e3543;
                border-radius: 6px;
                padding: 2px 8px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        lbl_t = QtWidgets.QLabel(title)
        lbl_t.setStyleSheet("font-size: 9px; font-weight: 800; color: #8f98a8; background: transparent;")
        lbl_t.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        lbl_v = QtWidgets.QLabel("--")
        lbl_v.setMinimumWidth(0)
        lbl_v.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        lbl_v.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}; background: transparent;")
        lbl_v.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return card, lbl_v

    def _on_meas_channel_changed(self, ch: str):
        self.active_meas_channel = ch
        color = self.channel_colors.get(ch, "#ffffff")
        self.meas_channel_combo.setProperty("selectedTextColor", color)
        self.meas_channel_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #21252f;
                border: 1px solid {color};
                font-weight: bold;
                font-size: 11px;
                padding: 2px 6px;
            }}
        """)

    def _channel_checkbox_style(self, name):
        color = self.channel_colors.get(name, PALETTE[self.known_columns.index(name) % len(PALETTE)])
        if not self.selected_columns.get(name, False): color = '#8f98a8'
        check_icon = (ROOT / "monitor/v13/assets/check_neutral.svg").as_posix()
        return f"""QCheckBox {{background: transparent; border: none; padding: 4px;
            color: {color}; font-weight: bold; font-size: 12px;}}
            QCheckBox::indicator {{width: 14px; height: 14px; border: 1px solid #737d8d;
                border-radius: 3px; background: #171920;}}
            QCheckBox::indicator:checked {{image: url("{check_icon}");}}
            QCheckBox::indicator:unchecked {{image: none;}}
            QCheckBox::indicator:hover {{border-color: #e6e9ef;}}"""

    @staticmethod
    def _color_icon(color):
        pixmap = QtGui.QPixmap(14, 14)
        pixmap.fill(QtGui.QColor(color))
        return QtGui.QIcon(pixmap)

    def _set_channel_color(self, name, color):
        self.channel_colors[name] = color
        self.channel_color_buttons[name].setIcon(self._color_icon(color))
        self.channel_checkboxes[name].setStyleSheet(self._channel_checkbox_style(name))
        for action in self.channel_color_buttons[name].menu().actions():
            action.setChecked(action.data() == color)
        line = self.line_items.get(name)
        if line is not None:
            pen = pg.mkPen(line.opts['pen'])
            pen.setColor(QtGui.QColor(color))
            line.setPen(pen)
        if self.active_meas_channel == name:
            self._on_meas_channel_changed(name)

    def _rebuild_column_controls(self, names: List[str]):
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget() is not None: item.widget().deleteLater()
        self.channel_color_buttons = {}
        self.channel_checkboxes = {}
        for idx, name in enumerate(names):
            color = self.channel_colors.setdefault(name, PALETTE[idx % len(PALETTE)])
            row = QtWidgets.QFrame()
            row.setStyleSheet('QFrame {background: #21252f; border: 1px solid #323946; border-radius: 6px;}')
            layout = QtWidgets.QHBoxLayout(row)
            layout.setContentsMargins(6, 2, 6, 2)
            layout.setSpacing(2)
            picker = QtWidgets.QToolButton()
            picker.setIcon(self._color_icon(color))
            picker.setIconSize(QtCore.QSize(14, 14))
            picker.setFixedSize(26, 24)
            picker.setStyleSheet('QToolButton {border: none; background: transparent;} QToolButton:hover {background: #3a4252;} QToolButton::menu-indicator {image: none; width: 0px; height: 0px;}')
            picker.setToolTip(f'Elegir color de {name}. Usar la casilla para mostrar u ocultar el canal.')
            picker.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QtWidgets.QMenu(picker)
            group = QtGui.QActionGroup(menu)
            for label, choice in zip(('Cian', 'Amarillo', 'Verde', 'Rosa', 'Naranja', 'Púrpura'), PALETTE):
                action = menu.addAction(self._color_icon(choice), label)
                action.setData(choice)
                action.setCheckable(True)
                action.setChecked(choice == color)
                group.addAction(action)
                action.triggered.connect(lambda checked, channel=name, selected=choice: self._set_channel_color(channel, selected))
            picker.setMenu(menu)
            checkbox = QtWidgets.QCheckBox(name)
            is_checked = self.selected_columns.get(name, name in ('V_IN', 'V_OUT'))
            self.selected_columns[name] = is_checked
            checkbox.setChecked(is_checked)
            checkbox.setStyleSheet(self._channel_checkbox_style(name))
            checkbox.setToolTip({'V_IN': 'Entrada A2 (ADC1_IN11). Mostrar u ocultar este canal.',
                                 'ADC_IN': 'Valor ADC de A2 (ADC1_IN11).',
                                 'V_OUT': 'Entrada A3 (ADC1_IN12). Mostrar u ocultar este canal.',
                                 'ADC_OUT': 'Valor ADC de A3 (ADC1_IN12).'}.get(name, 'Mostrar u ocultar este canal'))
            checkbox.stateChanged.connect(self._on_column_toggled)
            self.channel_color_buttons[name] = picker
            self.channel_checkboxes[name] = checkbox
            layout.addWidget(checkbox, 1)
            layout.addWidget(picker)
            self.columns_layout.addWidget(row)

    def _build_generator_panel(self, layout):
        self.generator_column.setStyleSheet("""
            QLabel { background:transparent; border:0; color:#aeb8c8; }
            QComboBox, QDoubleSpinBox { background:#10151d; border:1px solid #3a4659;
                border-radius:7px; padding:3px; color:#eef5ff; min-height:18px; }
            QComboBox:hover, QDoubleSpinBox:focus { border-color:#55dfc4; }
            QPushButton { background:#253f40; border:1px solid #3b7c72; border-radius:8px;
                color:#d6fff6; padding:9px; font-weight:bold; }
            QPushButton:hover { background:#315551; }
            QPushButton:disabled { background:#202630; border-color:#303a48; color:#627083; }
            QDial { background:transparent; }
            QCheckBox { color:#d6fff6; padding:6px 0; }
        """)
        self.generator_panel = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.generator_panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(3)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.generator_wave = GeneratorComboBox()
        for i, name in enumerate(WAVES[:4]):
            self.generator_wave.addItem(generator_wave_icon(i), name)
        self.generator_wave.setIconSize(QtCore.QSize(36,18))
        self.generator_wave.setFixedHeight(28)
        self.generator_mode = GeneratorComboBox()
        for name, icon in zip((*MODES, "Pulso", "Wav"),
                              ('continuous', 'sweep', 'chirp', 'pulse', 'wav')):
            self.generator_mode.addItem(QtGui.QIcon(str(ROOT / f'monitor/v13/assets/mode_{icon}.svg')), name)
        self.generator_mode.setIconSize(QtCore.QSize(18, 18))
        self.generator_frequency = GeneratorFrequencySpinBox()
        self.generator_final_frequency = GeneratorFrequencySpinBox()
        for spin in (self.generator_frequency, self.generator_final_frequency):
            spin.setRange(0.1, 20000); spin.setDecimals(3); spin.setValue(2.5)
        self.generator_frequency.setToolTip('0,1 Hz a 20 kHz. Lectura en Hz y kHz (1000 Hz = 1 kHz).\nEscribir en Hz o incluir kHz; confirmar con Enter o al salir.\nPara observar 20 kHz, elegir Fs de 50 o 62,5 kHz.')
        self.generator_frequency.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_frequency.setStyleSheet('font-size:12px; font-weight:bold; color:#8df3dc;')
        self.generator_amplitude = VoltageSpinBox()
        self.generator_amplitude.setRange(0, 3.3); self.generator_amplitude.setDecimals(2)
        self.generator_amplitude.setSingleStep(.01)
        self.generator_amplitude.setSuffix(' Vpp'); self.generator_amplitude.setValue(2.0)
        self.wav_amplitude_dial = AmplitudeDial()
        self.wav_amplitude_dial.setRange(0, 330)
        self.wav_amplitude_dial.setValue(200)
        self.wav_amplitude_dial.setFixedSize(64, 64)
        self.wav_amplitude_dial.setNotchesVisible(True)
        self.wav_amplitude_dial.setNotchTarget(7)
        self.wav_amplitude_dial.setTracking(True)
        self.wav_amplitude_dial.setSingleStep(1)
        self.wav_amplitude_dial.setPageStep(10)
        self.wav_amplitude_dial.setToolTip("Amplitud: 0,01 V por paso. Shift + arrastrar: ajuste fino.")
        self.wav_amplitude_dial.valueChanged.connect(lambda value: self.generator_amplitude.setValue(value / 100))
        self.generator_amplitude.valueChanged.connect(self._sync_wav_amplitude_dial)
        self.generator_offset = VoltageSpinBox()
        self.generator_offset.setRange(0, 3.3); self.generator_offset.setDecimals(2)
        self.generator_offset.setSingleStep(.01)
        self.generator_offset.setSuffix(' V'); self.generator_offset.setValue(1.65)
        self.generator_offset_slider = OffsetSlider(QtCore.Qt.Orientation.Horizontal)
        self.generator_offset_slider.centered.connect(lambda: self.generator_offset.setValue(1.65))
        self.generator_offset_slider.setSingleStep(1)
        self.generator_offset_slider.setPageStep(10)
        self.generator_offset_slider.setToolTip("Offset: 0,01 V por paso. Shift + arrastrar: ajuste fino; doble clic: centrar.")
        self.generator_offset_slider.setFixedHeight(24)
        self.generator_headroom = QtWidgets.QLabel()
        self.generator_headroom.setWordWrap(True)
        self.generator_headroom.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_headroom.setStyleSheet('color:#ffbf69; font-size:10px;')
        self.generator_duration = GeneratorValueSpinBox()
        self.generator_duration.setRange(0.001,600); self.generator_duration.setDecimals(3)
        self.generator_duration.setSuffix(' s'); self.generator_duration.setValue(1)
        self._generator_duration_ms = False
        self._generator_duration_us = False
        self._pulse_us_capable = False
        self.generator_frequency_dial = InstrumentDial()
        self.generator_frequency_dial.setRange(0,1000)
        self.generator_frequency_dial.setNotchesVisible(True)
        self.generator_frequency_dial.setNotchTarget(7.0)
        self.generator_frequency_dial.setTracking(True)
        self.generator_frequency_dial.setFixedSize(88,88)
        palette=self.generator_frequency_dial.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Button,QtGui.QColor('#55a99e'))
        self.generator_frequency_dial.setPalette(palette)
        self.generator_frequency_dial.setToolTip('Dial logarítmico · 0,1 Hz → 20 kHz. El número permite ajuste preciso.')
        self.generator_frequency_dial.valueChanged.connect(
            lambda value:self.generator_frequency.setValue(round(.1*200000**(value/1000), 3 if .1*200000**(value/1000) < 1 else 0)))
        def sync_dial(value):
            blocker=QtCore.QSignalBlocker(self.generator_frequency_dial)
            self.generator_frequency_dial.setValue(round(1000*math.log(value/.1)/math.log(200000)))
            del blocker
        self.generator_frequency.valueChanged.connect(sync_dial)
        sync_dial(2.5)
        self.generator_enabled = QtWidgets.QCheckBox('Salida encendida')
        self.generator_enabled.setChecked(False)
        check_icon = (ROOT / "monitor/v13/assets/check_neutral.svg").as_posix()
        self.generator_enabled.setStyleSheet(f"""
            QCheckBox {{color:#d6fff6; background:transparent; border:none;}}
            QCheckBox::indicator {{width:14px; height:14px; border:1px solid #737d8d;
                border-radius:3px; background:#171920;}}
            QCheckBox::indicator:checked {{image:url("{check_icon}");}}
            QCheckBox::indicator:unchecked {{image:none;}}
        """)
        self.generator_restart = QtWidgets.QPushButton('Disparar de nuevo')
        self.generator_restart.clicked.connect(self._apply_generator)
        controls = [('Modo',self.generator_mode),('Forma de onda',self.generator_wave),
                    ('Frecuencia',self.generator_frequency),('Frecuencia final',self.generator_final_frequency),
                    ('Amplitud pico pico',self.generator_amplitude),('Offset',self.generator_offset),
                    ('Duración',self.generator_duration)]
        self._generator_labels = {}
        positions = [(0,0,1),(0,1,1),(2,1,1),(5,0,1),(7,0,1),(7,1,1),(5,1,1)]
        for (label,control),(row,col,span) in zip(controls,positions):
            self._generator_labels[control] = QtWidgets.QLabel(label)
            self._generator_labels[control].setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._generator_labels[control].setWordWrap(True)
            if isinstance(control, QtWidgets.QDoubleSpinBox):
                control.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            control.setFixedHeight(28)
            control.setMinimumWidth(0)
            control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
            grid.addWidget(self._generator_labels[control],row,col,1,span)
            grid.addWidget(control,row+1,col,1,span)
            if control is self.generator_frequency:
                grid.addWidget(self.generator_frequency_dial,2,0,3,1,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(self.wav_amplitude_dial,8,0,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        self.generator_enabled.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        self.generator_restart.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        grid.addWidget(self.generator_offset_slider,9,1)
        grid.addWidget(self.generator_headroom,10,0,1,2)
        grid.addWidget(self.generator_enabled,11,0,1,2,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.generator_restart.setFixedHeight(34)
        self.generator_restart.setText('Disparar')
        grid.addWidget(self.generator_restart,12,0,1,2)
        self.generator_status = StatusLabel('Conectar el Q')
        self.generator_status.setStyleSheet('color:#aeb8c8; background:transparent; border:none;')
        self.generator_status.setWordWrap(True)
        self.generator_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.generator_status,13,0,1,2)
        self.generator_scroll = QtWidgets.QScrollArea()
        self.generator_scroll.setWidgetResizable(True)
        self.generator_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.generator_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.generator_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.generator_scroll.setWidget(self.generator_panel)
        layout.addWidget(self.generator_scroll,1)
        self._generator_timer = QtCore.QTimer(self)
        self._generator_timer.setSingleShot(True)
        self._generator_timer.setInterval(250)
        self._generator_timer.timeout.connect(self._apply_generator)
        self.generator_frequency_dial.sliderReleased.connect(self._schedule_generator)
        for _,control in controls:
            if isinstance(control, QtWidgets.QDoubleSpinBox):
                control.setKeyboardTracking(False)
            signal=control.currentIndexChanged if isinstance(control,QtWidgets.QComboBox) else control.valueChanged
            signal.connect(self._generator_mode_changed if control is self.generator_mode else self._schedule_generator)
        self.generator_enabled.toggled.connect(self._schedule_generator)
        self._generator_dirty=False
        self._generator_syncing=False
        self._generator_requested=None
        self._generator_active=GeneratorConfig()
        self._generator_state_known=False
        self._generator_controls=[c for _,c in controls]+[self.generator_enabled,self.generator_restart,self.generator_offset_slider]
        self.generator_amplitude.valueChanged.connect(self._update_generator_offset_bounds)
        self.generator_offset.valueChanged.connect(self._update_generator_offset_bounds)
        self.generator_offset_slider.valueChanged.connect(
            lambda value: self.generator_offset.setValue(value / 100))
        self.generator_offset_slider.sliderReleased.connect(self._schedule_generator)
        self._update_generator_offset_bounds()
        self.wav_path = ''
        self._wav_metadata = None
        self._wav_capable = False
        self._wav_preparing = False
        self._wav_active = False
        self._wav_cancelled = False
        self.wav_file = QtWidgets.QPushButton('Elegir WAV…')
        self.wav_file.setStyleSheet('QPushButton {padding:0 8px; margin:0; min-height:26px; max-height:26px;}')
        self.wav_file.clicked.connect(self._choose_wav)
        self.wav_channels = QtWidgets.QWidget()
        channel_layout = QtWidgets.QHBoxLayout(self.wav_channels)
        channel_layout.setContentsMargins(0,0,0,0)
        channel_layout.setSpacing(3)
        channel_layout.addStretch()
        self.wav_channel_group = QtWidgets.QButtonGroup(self)
        for index, name in enumerate(('L','R','Mix')):
            button = QtWidgets.QPushButton(name)
            button.setCheckable(True)
            button.setChecked(name == 'Mix')
            button.setFixedSize(40 if name == 'Mix' else 30, 28)
            button.setStyleSheet('QPushButton {padding:0; margin:0; background:#20242b; border:1px solid #39434b; border-radius:5px; color:#aeb8c8;} QPushButton:checked {background:#245348; border-color:#55dfc4; color:#55dfc4;}')
            self.wav_channel_group.addButton(button,index)
            channel_layout.addWidget(button)
        channel_layout.addStretch()
        self.wav_channels.setFixedHeight(34)
        self.wav_back = QtWidgets.QToolButton()
        self.wav_forward = QtWidgets.QToolButton()
        for button, delta, icon in ((self.wav_back, -10, 'wav_back.svg'), (self.wav_forward, 10, 'wav_forward.svg')):
            button.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v13/assets' / icon)))
            button.setToolTip(('Retroceder' if delta < 0 else 'Avanzar') + ' 10 segundos')
            button.setAccessibleName(button.toolTip())
            button.setEnabled(False)
            button.clicked.connect(lambda checked=False, seconds=delta: self._seek_wav(seconds))
        self.wav_play = QtWidgets.QToolButton()
        self.wav_play.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v13/assets/wav_play.svg')))
        self.wav_play.setToolTip('Reproducir WAV')
        self.wav_play.setAccessibleName('Reproducir WAV')
        self.wav_play.clicked.connect(self._toggle_wav)
        self.wav_file.setFixedHeight(self.generator_mode.height())
        self.wav_file.setMinimumWidth(0)
        self.wav_file.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.wav_rate = GeneratorComboBox()
        for rate in (20000,40000,50000):
            self.wav_rate.addItem(f'{rate//1000} kHz', rate)
            if rate!=20000: self.wav_rate.model().item(self.wav_rate.count()-1).setEnabled(False)
        self.wav_rate.setCurrentIndex(self.wav_rate.findData(50000))
        self.wav_rate.setFixedHeight(28)
        self.wav_rate.setToolTip("Tasa del DAC; el WAV se remuestrea con filtro antialias a esta tasa.")
        self.wav_rate.currentIndexChanged.connect(self._wav_rate_changed)
        self.wav_info = QtWidgets.QLabel('Mono · 50.000 muestras/s · 12 bits')
        self.wav_info.setWordWrap(True)
        self.wav_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.wav_info.setContentsMargins(0,6,0,0)
        self.wav_transport = QtWidgets.QWidget()
        self.wav_transport.setFixedHeight(38)
        transport_layout = QtWidgets.QHBoxLayout(self.wav_transport)
        transport_layout.setContentsMargins(0, 0, 0, 0)
        transport_layout.setSpacing(8)
        transport_layout.addStretch()
        for button in (self.wav_back, self.wav_play, self.wav_forward):
            button.setFixedSize(34, 34)
            button.setIconSize(QtCore.QSize(16, 16))
            button.setStyleSheet('QToolButton {padding:0; margin:0; background:#245348; color:#55dfc4; border:1px solid #55dfc4; border-radius:7px;} QToolButton:hover {background:#2d6558; border-color:#83ead5;} QToolButton:pressed {background:#153e35; border-color:#acf9e9;} QToolButton:disabled {background:#171920; border-color:#30343b;}')
            transport_layout.addWidget(button)
        transport_layout.addStretch()
        self._wav_widgets = [self.wav_file,self.wav_channels,self.wav_rate,self.wav_transport,self.wav_info]
        for row, widget in enumerate(self._wav_widgets,14):
            grid.addWidget(widget,row,0,1,2)
        self._wav_labels = [QtWidgets.QLabel(text) for text in ('Archivo', 'Canal', 'Salida')]
        for label in self._wav_labels:
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet('color:#8f98a8; background:transparent; border:none; font-size:10px;')
        self._wav_widgets.extend(self._wav_labels)
        self.wav_info.setStyleSheet('color:#8f98a8; background:transparent; border:none; font-size:10px;')
        self._generator_layout_wav = None
        self._generator_availability()

    def _seek_wav(self, seconds):
        if self.serial_worker and self._wav_active and not self._wav_preparing:
            try:
                self.serial_worker.request_wav(4, seconds)
            except queue.Full:
                self.generator_status.setText('Wav ocupado; intentar el salto otra vez.')

    def _toggle_wav(self):
        if self._wav_active or self._wav_preparing:
            self._stop_wav()
        else:
            self._play_wav()

    def _sync_wav_transport(self):
        busy = self._wav_active or self._wav_preparing
        name = 'Detener WAV' if busy else 'Reproducir WAV'
        icon = 'wav_stop.svg' if busy else 'wav_play.svg'
        self.wav_play.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v13/assets' / icon)))
        self.wav_play.setToolTip(name)
        self.wav_play.setAccessibleName(name)
        self.wav_play.setEnabled(busy or bool(self.wav_path))
        self.wav_rate.setEnabled(not busy)
        locked = busy or self.output_pending
        self.config_bits_combo.setEnabled(not locked)
        self.config_rate_combo.setEnabled(not locked)
        self.destination_combo.setEnabled(not locked)
        self.r4_combo.setEnabled(not locked and self.destination_combo.currentData() == int(Mode.UART))

    def _wav_rate_changed(self):
        metadata = self._wav_metadata
        source = (f"{number(metadata['rate']/1000, formats.ng)} kHz · {metadata['bits']} bits · {metadata['channels']} canales · {number(metadata['duration'], formats.n_1f)} s\n" if metadata else '')
        self.wav_info.setText(source + f'Salida: {number(self.wav_rate.currentData()/1000, formats.ng)} kHz · 12 bits · mono')

    def _choose_wav(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self,'Elegir archivo WAV','','WAV (*.wav *.WAV)')
        if path:
            try:
                metadata = inspect_wav(path)
            except (ValueError, OSError) as exc:
                self.wav_path = ''
                self._wav_metadata = None
                self.wav_info.setText(f'WAV inválido: {exc}')
                self.generator_status.setText(f'WAV inválido: {exc}')
                self._sync_wav_transport()
                return
            self.wav_path = path
            self._wav_metadata = metadata
            description = f"{number(metadata['rate']/1000, formats.ng)} kHz · {metadata['bits']} bits · {metadata['channels']} canales · {number(metadata['duration'], formats.n_1f)} s"
            self.wav_info.setText(description + f'\nSalida: {number(self.wav_rate.currentData()/1000, formats.ng)} kHz · 12 bits · mono')
            self.generator_status.setText('WAV válido · ' + description)
            self._sync_wav_transport()
            self.wav_file.setText(self.wav_file.fontMetrics().elidedText(Path(path).name, QtCore.Qt.TextElideMode.ElideMiddle, 210))
            self.wav_file.setToolTip(path)

    def _play_wav(self):
        if self._wav_preparing or self._wav_active or not self.wav_path or not self.serial_worker or not self._wav_capable:
            self.generator_status.setText('Elegir un WAV válido.' if not self.wav_path else 'Conectar el Q con V12 Audio para reproducir WAV.' if not self.serial_worker else 'WAV: esperando confirmación de V12 Audio; reconectar el Q.')
            return
        if self.spectral.bode.active:
            self.generator_status.setText('Detener Bode antes de reproducir WAV.')
            return
        if self.output_pending or self._auto_apply_timer.isActive():
            self.generator_status.setText('Esperar la confirmación de adquisición antes de reproducir WAV.')
            return
        if self.applied_configuration.rate > 100000:
            self.generator_status.setText('Wav: usar muestreo de adquisición hasta 100 kHz; 125 kHz no pasó la prueba conjunta.')
            return
        self._auto_apply_timer.stop()
        self._wav_preparing = True
        self._wav_cancelled = False
        self._sync_wav_transport()
        self.generator_status.setText(f'Preparando mono y remuestreo a {number(self.wav_rate.currentData()/1000, formats.ng)} kHz…')
        self._wav_target_worker = self.serial_worker
        self._wav_thread = QtCore.QThread(self)
        self._wav_preparation = WavPreparation(self.wav_path,
            ('L','R','Mix')[self.wav_channel_group.checkedId()],
            3.3,1.65,self.wav_rate.currentData())
        self._wav_preparation.moveToThread(self._wav_thread)
        self._wav_thread.started.connect(self._wav_preparation.run)
        self._wav_preparation.ready.connect(self._wav_ready)
        self._wav_preparation.failed.connect(self.generator_status.setText)
        self._wav_preparation.finished.connect(self._wav_thread.quit, QtCore.Qt.ConnectionType.DirectConnection)
        self._wav_preparation.finished.connect(self._wav_preparation.deleteLater)
        self._wav_thread.finished.connect(self._wav_prepared)
        self._wav_thread.start()

    def _wav_prepared(self):
        self._wav_preparing = False
        self._sync_wav_transport()

    def _wav_ready(self, source):
        if self._wav_cancelled or self.serial_worker is not self._wav_target_worker or self.generator_mode.currentIndex() != 4:
            return
        metadata = self._wav_metadata
        source_bits = f" · {metadata['bits']} bits" if metadata else ''
        self.wav_info.setText(f'{number(source.original_rate/1000, formats.ng)} kHz{source_bits} · {source.channels} canales · {number(source.duration, formats.n_1f)} s\nSalida: {number(getattr(source,"output_rate",20000)/1000, formats.ng)} kHz · 12 bits · mono')
        try:
            self._update_wav_levels()
            self.serial_worker.request_wav(1,source.codes,getattr(source,"output_rate",20000))
            self.single_shot_armed = False
            self.run_stop_btn.setChecked(True)
            self.toggle_run_stop()
            self._wav_active = True
            self._sync_wav_transport()
        except queue.Full:
            self.generator_status.setText('WAV ocupado; intentar otra vez.')

    def _stop_wav(self):
        self._wav_cancelled = True
        if self.serial_worker and self._wav_capable and self._wav_active:
            try:
                self.serial_worker.request_wav(3)
            except queue.Full:
                self.generator_status.setText('WAV ocupado; intentar detener otra vez.')
        self._sync_wav_transport()

    def _wav_confirmed(self, status):
        self._wav_capable = True
        for i in range(self.wav_rate.count()):
            self.wav_rate.model().item(i).setEnabled(bool(status.rates_mask & (1 << i)))
        if not status.rates_mask & (1 << self.wav_rate.currentIndex()):
            with QtCore.QSignalBlocker(self.wav_rate): self.wav_rate.setCurrentIndex(0)
            self._wav_rate_changed()
        self._wav_active = int(status.state) in (1,2,4,5)
        for button in (self.wav_back, self.wav_forward):
            button.setEnabled(int(status.state) == 2 and not self._wav_preparing)
        self._sync_wav_transport()
        if self.generator_mode.currentIndex() == 4:
            names = ('Listo','Cargando','Reproduciendo','Finalizado','Interrumpido: faltaron muestras','Error')
            metadata = self._wav_metadata
            detail = f" · {number(metadata['rate']/1000, formats.ng)} kHz · {metadata['bits']} bits · {metadata['channels']} canales" if metadata else ''
            self.generator_status.setText(f'{names[int(status.state)]} · {number(status.played/status.rate, formats.n_2f)} / {number(status.total/status.rate, formats.n_2f)} s' + (f' · motivo {status.reason}' if status.reason else ''))

    def _update_generator_offset_bounds(self, *args):
        # Round inward to the 0.01 V resolution so every selectable offset is valid.
        half = self.generator_amplitude.value() / 2
        minimum = math.ceil(half * 100 - 1e-8)
        maximum = math.floor((3.3 - half) * 100 + 1e-8)
        offset = min(max(self.generator_offset.value(), minimum / 100), maximum / 100)
        with QtCore.QSignalBlocker(self.generator_offset):
            self.generator_offset.setRange(minimum / 100, maximum / 100)
            self.generator_offset.setValue(offset)
        with QtCore.QSignalBlocker(self.generator_offset_slider):
            self.generator_offset_slider.setRange(minimum, maximum)
            self.generator_offset_slider.setValue(round(self.generator_offset.value() * 100))
        self.generator_offset_slider.setToolTip(
            f'Offset permitido: {number(minimum / 100, formats.n_2f)} a {number(maximum / 100, formats.n_2f)} V\nDoble clic: centrar en 1,65 V')
        offset = self.generator_offset.value()
        near_rail = offset - half < 0.2 - 1e-9 or offset + half > 3.1 + 1e-9
        self.generator_headroom.setText(
            'Cerca de los extremos: el DAC puede recortar la señal.' if near_rail else '')
        self.generator_headroom.setVisible(near_rail)

    def _generator_availability(self):
        wav_mode=self.generator_mode.currentIndex()==4
        pulse=self.generator_mode.currentIndex()==3
        mode=self.generator_mode.currentIndex()
        pulse_us = pulse and self._pulse_us_capable
        if pulse != self._generator_duration_ms or pulse_us != self._generator_duration_us:
            seconds = self.generator_duration.value() / (1000000 if self._generator_duration_us else 1000 if self._generator_duration_ms else 1)
            with QtCore.QSignalBlocker(self.generator_duration):
                self.generator_duration.setRange(100 if pulse_us else 1 if pulse else 0.001,
                                                 65535 if pulse_us else 600000 if pulse else 600)
                self.generator_duration.setDecimals(0 if pulse else 3)
                self.generator_duration.setSuffix(' µs' if pulse_us else ' ms' if pulse else ' s')
                self.generator_duration.setValue(seconds * (1000000 if pulse_us else 1000 if pulse else 1))
            self._generator_duration_ms = pulse
            self._generator_duration_us = pulse_us

        self._generator_labels[self.generator_duration].setText('Ancho del pulso' if pulse else 'Duración del barrido')
        for control, visible in ((self.generator_wave, not pulse),
                                 (self.generator_frequency, not pulse),
                                 (self.generator_final_frequency, not pulse and mode != 0),
                                 (self.generator_duration, pulse or mode != 0)):
            control.setVisible(visible)
            self._generator_labels[control].setVisible(visible)
        self.generator_wave.setEnabled(not pulse)
        self.generator_frequency.setEnabled(not pulse)
        self.generator_final_frequency.setEnabled(not pulse and mode!=0)
        self.generator_duration.setEnabled(pulse or mode!=0)
        self.generator_restart.setEnabled(pulse or mode!=0)
        self.generator_restart.setVisible(pulse or mode!=0)
        self.generator_frequency_dial.setVisible(not pulse and not wav_mode)
        self.wav_amplitude_dial.setVisible(wav_mode)
        self.generator_amplitude.setVisible(not wav_mode)
        self._generator_labels[self.generator_amplitude].setText(
            f'Amplitud · {number(self.generator_amplitude.value(), formats.n_2f)} Vpp' if wav_mode else 'Amplitud pico pico')
        if hasattr(self, "_wav_widgets"):
            for widget in self._wav_widgets: widget.setVisible(wav_mode)
            self._sync_wav_transport()
        if wav_mode:
            for control in (self.generator_wave,self.generator_frequency,self.generator_final_frequency,self.generator_duration):
                control.hide()
                self._generator_labels[control].hide()
            self.generator_enabled.hide()
            self.generator_restart.hide()
        else:
            self.generator_enabled.show()
        if hasattr(self, '_wav_labels') and self._generator_layout_wav != wav_mode:
            self._arrange_generator_mode(wav_mode)
        self.generator_panel.layout().activate()
        self.generator_scroll.setMinimumHeight(getattr(self, '_generator_reserved_height',
                                                       self.generator_panel.sizeHint().height()))

    def _reserve_generator_height(self):
        """Measure every local layout once, without emitting generator commands."""
        mode = self.generator_mode.currentIndex()
        duration = self.generator_duration.value()
        syncing = self._generator_syncing
        warning_visible = not self.generator_headroom.isHidden()
        self._generator_syncing = True
        height = 0
        try:
            with QtCore.QSignalBlocker(self.generator_mode), QtCore.QSignalBlocker(self.generator_duration):
                for index in range(self.generator_mode.count()):
                    self.generator_mode.setCurrentIndex(index)
                    self._generator_availability()
                    self.generator_headroom.show()
                    self.generator_panel.layout().activate()
                    height = max(height, self.generator_panel.sizeHint().height())
                self.generator_mode.setCurrentIndex(mode)
                self._generator_availability()
                self.generator_duration.setValue(duration)
        finally:
            self.generator_headroom.setVisible(warning_visible)
            self._generator_syncing = syncing
        self._generator_reserved_height = height
        self.generator_scroll.setMinimumHeight(height)

    def _arrange_generator_mode(self, wav_mode):
        grid = self.generator_panel.layout()
        self._generator_layout_wav = wav_mode
        shared = [self.generator_offset, self.generator_offset_slider,
                  self._generator_labels[self.generator_amplitude], self._generator_labels[self.generator_offset],
                  self.wav_amplitude_dial, self.generator_headroom]
        for widget in shared + self._wav_widgets:
            grid.removeWidget(widget)
        if wav_mode:
            placements = [(self._wav_labels[0],0,1,1,1),(self.wav_file,1,1,1,1),
                          (self._wav_labels[1],2,0,1,1),(self._wav_labels[2],2,1,1,1),
                          (self.wav_channels,3,0,1,1),(self.wav_rate,3,1,1,1),
                          (self._generator_labels[self.generator_amplitude],4,0,1,1),
                          (self._generator_labels[self.generator_offset],4,1,1,1),
                          (self.generator_offset,5,1,1,1),(self.generator_offset_slider,6,1,1,1),
                          (self.generator_headroom,7,0,1,2),(self.wav_transport,8,0,1,2),
                          (self.wav_info,9,0,1,2)]
            grid.addWidget(self.wav_amplitude_dial,5,0,2,1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        else:
            placements = [(self._generator_labels[self.generator_amplitude],7,0,1,1),
                          (self._generator_labels[self.generator_offset],7,1,1,1),
                          (self.generator_offset,8,1,1,1),(self.generator_offset_slider,9,1,1,1),
                          (self.generator_headroom,10,0,1,2)]
            grid.addWidget(self.wav_amplitude_dial,8,0,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        for widget,row,col,rows,cols in placements:
            grid.addWidget(widget,row,col,rows,cols)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)

    def _generator_mode_changed(self, mode):
        if self._generator_syncing:
            return
        self._generator_availability()
        if mode == 3:
            with QtCore.QSignalBlocker(self.generator_duration):
                self.generator_duration.setValue(1000 if self._generator_duration_us else 1)
        if mode in (1, 2):
            # User selections start from these presets; hardware confirmations
            # keep their reported settings through _generator_syncing.
            controls = (self.generator_frequency, self.generator_final_frequency,
                        self.generator_duration, self.generator_frequency_dial)
            blockers = [QtCore.QSignalBlocker(control) for control in controls]
            self.generator_frequency.setValue(20)
            self.generator_frequency_dial.setValue(round(1000*math.log(20/.1)/math.log(200000)))
            self.generator_final_frequency.setValue(2000)
            self.generator_duration.setValue(2)
            del blockers
        self._schedule_generator()

    def _schedule_generator(self, *args):
        if self._generator_syncing: return
        self._generator_availability()
        if self.generator_mode.currentIndex() == 4:
            self._generator_timer.stop()
            self._update_wav_levels()
            return
        self._stop_wav()
        self._generator_dirty=True
        self._generator_timer.stop()
        if self.generator_mode.currentIndex() in (1, 2, 3):
            self.generator_status.setText('Preparado · pulsar Disparar')
            return
        if not self.generator_frequency_dial.isSliderDown() and not self.generator_offset_slider.isSliderDown():
            self._generator_timer.start()

    def _sync_wav_amplitude_dial(self, value):
        with QtCore.QSignalBlocker(self.wav_amplitude_dial):
            self.wav_amplitude_dial.setValue(round(value * 100))

    def _update_wav_levels(self):
        if self.serial_worker is not None:
            amplitude = self.generator_amplitude.value()
            offset = min(3.3 - amplitude / 2, max(amplitude / 2, self.generator_offset.value()))
            self.serial_worker.request_wav_levels(amplitude, offset)

    def _generator_config(self):
        amp=self.generator_amplitude.value(); offset=self.generator_offset.value()
        low,high=offset-amp/2,offset+amp/2
        if low < -1e-9 or high > 3.3+1e-9:
            if self.generator_enabled.isChecked():
                raise ValueError('Amplitud y offset deben dejar ambos niveles entre 0 y 3,3 V')
            low=self._generator_active.low*3.3/4095
            high=self._generator_active.high*3.3/4095
        return GeneratorConfig(4 if self.generator_mode.currentIndex() == 3 else self.generator_wave.currentIndex(),int(self.generator_enabled.isChecked()),
            0 if self.generator_mode.currentIndex() in (3,4) else self.generator_mode.currentIndex(),round(self.generator_frequency.value()*1000),
            round(self.generator_final_frequency.value()*1000),round(max(0,low)*4095/3.3),
            round(min(3.3,high)*4095/3.3),round(self.generator_duration.value()*(1 if self._generator_duration_ms else 1000)), int(self._generator_duration_us))

    def _apply_generator(self):
        self._generator_timer.stop()
        if self.generator_mode.currentIndex() == 4: return
        if self.sender() is self._generator_timer and self.generator_mode.currentIndex() in (1, 2, 3): return
        try:
            config=self._generator_config()
            if self.serial_worker is None:
                self.generator_status.setText('Configuración preparada; conectar el Q para aplicarla.')
                return
            self.serial_worker.request_generator(config)
            self._generator_requested=config
            self._generator_dirty=False
            self.generator_status.setText('Esperando confirmación del Q…')
        except (ValueError,queue.Full) as exc:
            self.generator_status.setText(str(exc) or 'Generador ocupado; volver a seleccionar o reiniciar.')

    def _generator_confirmed(self, reply):
        capability = getattr(reply, 'pulse_us_capable', False)
        if capability != self._pulse_us_capable:
            self._pulse_us_capable = capability
            self._generator_availability()
        from monitor.v13.receiver.unoq_switch import Phase
        if reply.phase == Phase.APPLIED and (self._generator_requested is None or reply.active == self._generator_requested):
            self._generator_active = reply.active
            self._generator_state_known = True
        self.spectral.bode.confirmed(reply)
        if self.spectral.bode.active:
            state='Activo' if reply.running else ('Finalizado' if reply.active.enabled else 'Apagado')
            self.generator_status.setText(f'{state} · Bode')
            return
        if self.generator_mode.currentIndex() == 4: return
        if reply.phase==Phase.REJECTED:
            self.generator_status.setText(f'Q rechazó el generador: {reply.reason.name}')
            self._generator_requested=None
            return
        if reply.phase!=Phase.APPLIED: return
        if self._generator_requested is not None and reply.active!=self._generator_requested: return
        self._generator_requested=None
        if self._generator_dirty and self.generator_mode.currentIndex() in (1, 2, 3):
            self.generator_status.setText('Preparado · pulsar Disparar')
            return
        c=reply.active
        self._generator_active=c
        editing = any(isinstance(control, QtWidgets.QDoubleSpinBox) and control.hasFocus()
                      for control in self._generator_controls)
        editing = editing or self.generator_frequency_dial.isSliderDown() or self.generator_offset_slider.isSliderDown()
        if not self._generator_dirty and not editing and getattr(self, "_generator_display_config", None) != c:
            self._generator_syncing=True
            try:
                if c.wave != 4:
                    self.generator_wave.setCurrentIndex(c.wave)
                self.generator_mode.setCurrentIndex(3 if c.wave == 4 else c.mode)
                self.generator_frequency.setValue(c.frequency/1000)
                self.generator_final_frequency.setValue(c.final_frequency/1000)
                self.generator_amplitude.setValue((c.high-c.low)*3.3/4095)
                self.generator_offset.setValue((c.high+c.low)*3.3/8190)
                self._update_generator_offset_bounds()
                self._generator_availability()
                self.generator_duration.setValue(c.duration * (1000 if self._generator_duration_us and not c.duration_us else .001 if c.duration_us and not self._generator_duration_us else 1) if self._generator_duration_ms else c.duration/1000)
                self.generator_enabled.setChecked(bool(c.enabled))
            finally:
                self._generator_syncing=False
            self._generator_availability()
            self._generator_display_config = c
        state='Activo' if reply.running else ('Finalizado' if c.enabled else 'Apagado')
        self.generator_status.setText(f'{state} · {WAVES[c.wave]} · {number(c.frequency/1000, formats.ng)} Hz')
        if self._generator_dirty and self.generator_mode.currentIndex() == 0 and not self._generator_timer.isActive(): self._generator_timer.start()

    def _on_column_toggled(self):
        checkbox = self.sender()
        if checkbox is None: return
        name = checkbox.text()
        self.selected_columns[name] = checkbox.isChecked()
        self.selection_dirty = True
        checkbox.setStyleSheet(self._channel_checkbox_style(name))
        if name in self.line_items:
            self.line_items[name].setVisible(checkbox.isChecked())

    def _on_adc_bits_changed(self, text: str):
        """Ajusta la resolución de bits del ADC y actualiza los factores de escala dinámicamente."""
        try:
            bits = int(text.split()[0])
        except (ValueError, IndexError):
            bits = 10

        self.adc_bits = bits
        self.adc_max = float((1 << bits) - 1)

        if self.serial_worker is not None:
            self.serial_worker.set_adc_bits(bits)

        # Si el trigger está configurado en un canal ADC, actualizar el rango del dial
        is_adc = "ADC" in self.trigger_source
        if is_adc:
            self._updating_trigger_line = True
            self.dial_trigger_level.setRange(0, int(self.adc_max))
            self.trigger_level = min(self.trigger_level, self.adc_max)
            self.lbl_trigger_level.setText(f"{int(self.trigger_level)}")
            self.dial_trigger_level.setValue(int(round(self.trigger_level)))
            self.trigger_line.setValue(self.trigger_level)
            self._updating_trigger_line = False

    def _on_xaxis_toggle(self, checked: bool):
        """Alterna el eje X entre índice de muestra y tiempo real (µs)."""
        self.x_axis_time_mode = checked
        self._h_time_ms = self.h_scale * self._horizontal_dt_us() / 1000
        self._sync_horizontal_controls()
        if checked:
            self.btn_xaxis_toggle.setText("Tiempo")
        else:
            self.btn_xaxis_toggle.setText("Muestras")

    def _on_trace_mode_changed(self, text: str):
        """Cambia el modo de trazo entre Escalón (Step) y Línea (Linear)."""
        if "Línea" in text:
            self.trace_mode = "Línea"
        else:
            self.trace_mode = "Escalón"

    def _on_trace_style_changed(self, text: str):
        # También actualiza las curvas congeladas en STOP sin mover la captura.
        for idx, col in enumerate(self.known_columns):
            curve = self.line_items.get(col)
            if curve is not None:
                color = self.channel_colors.get(col, PALETTE[idx % len(PALETTE)])
                curve.setPen(pg.mkPen(color, width=2 if text == "Intenso" else 1))
                x, y = curve.getData()
                if x is not None:
                    curve.setData(x, y, connect="finite", antialias=text == "Suave")
                else:
                    curve.setData([], [], antialias=text == "Suave")

    def _on_auto_gap_changed(self, state: int):
        """Activa o desactiva el corte automático por silencios/gaps temporales."""
        self.auto_gap_cut = bool(state == QtCore.Qt.CheckState.Checked.value)

    def _prepare_trace_data(self, x_data, y_data, detect_gaps=True):
        """Escalones y cortes vectorizados; conserva todas las muestras del trazo."""
        n = len(x_data)
        if n < 2 or len(y_data) != n:
            return x_data, y_data
        is_step = self.trace_mode == "Escalón"
        if not is_step and not self.auto_gap_cut:
            return x_data, y_data
        if self.x_axis_time_mode and self.current_dt_us > 0:
            threshold = max(3.0 * self.current_dt_us, 1500.0)
            nominal_dt = self.current_dt_us
        elif self.x_axis_time_mode:
            threshold, nominal_dt = 2000.0, 0.0
        else:
            threshold, nominal_dt = 2.0, 1.0

        x = np.asarray(x_data, dtype=float)
        y = np.asarray(y_data, dtype=float)
        gaps = (np.diff(x) > threshold) if self.auto_gap_cut and detect_gaps else np.zeros(n - 1, dtype=bool)
        if is_step and not np.any(gaps):
            # Ruta habitual: dos vértices por escalón, sin listas intermedias.
            xo = np.empty(2 * n - 1)
            yo = np.empty(2 * n - 1)
            xo[0], yo[0] = x[0], y[0]
            xo[1::2] = xo[2::2] = x[1:]
            yo[1::2], yo[2::2] = y[:-1], y[1:]
            return xo, yo
        if not is_step and not np.any(gaps):
            return x, y

        hold = x[:-1] + nominal_dt
        extra = gaps & (hold < x[1:]) if is_step else gaps
        sizes = (2 if is_step else 1) + extra.astype(np.intp)
        ends = np.cumsum(sizes)
        starts = ends - sizes + 1
        xo, yo = np.empty(int(ends[-1]) + 1), np.empty(int(ends[-1]) + 1)
        xo[0], yo[0] = x[0], y[0]
        xo[ends], yo[ends] = x[1:], y[1:]
        if is_step:
            xo[starts] = np.where(gaps, hold, x[1:])
            yo[starts] = np.where(gaps & ~extra, np.nan, y[:-1])
            xo[starts[extra] + 1] = hold[extra]
            yo[starts[extra] + 1] = np.nan
        else:
            xo[starts[gaps]], yo[starts[gaps]] = x[:-1][gaps], np.nan
        return xo, yo

    @staticmethod
    def _reduce_trace_for_display(x_data, y_data, xmin, xmax, pixels):
        """Reduce sólo el dibujo: primero, último y extremos de cada píxel.

        Mantiene el orden original (también los escalones con X repetida) y
        cada NaN que separa trazos. Las mediciones y el CSV usan datos completos.
        Al ampliar hasta pocos puntos por píxel se devuelve el trazo original.
        """
        if len(x_data) <= pixels * 4 or xmax <= xmin:
            return x_data, y_data
        x = np.asarray(x_data, dtype=float)
        y = np.asarray(y_data, dtype=float)
        finite = np.isfinite(x) & np.isfinite(y)
        delta = np.diff(x)
        if finite.all() and len(delta) and delta[0] > 0 and np.allclose(delta, delta[0], rtol=1e-9, atol=1e-9):
            # Uniform hardware samples: block extrema avoid per-point bucket
            # arrays and repeats. Each block is at most one display pixel wide.
            stride = max(1, math.ceil((xmax-xmin)/(pixels*delta[0])))
            stride = min(stride, len(x))
            blocks = len(x)//stride
            matrix = y[:blocks*stride].reshape(blocks, stride)
            starts = np.arange(blocks)*stride
            selected = np.concatenate((starts, starts+stride-1,
                starts+matrix.argmin(axis=1), starts+matrix.argmax(axis=1)))
            tail = blocks*stride
            if tail < len(x):
                selected = np.r_[selected, tail, len(x)-1, tail+y[tail:].argmin(), tail+y[tail:].argmax()]
            selected = np.unique(selected)
            return x[selected], y[selected]
        buckets = np.floor((np.where(finite, x, xmin) - xmin) * (pixels / (xmax - xmin)))
        # Cada valor no finito forma su propio grupo y conserva el corte.
        starts = np.r_[0, np.flatnonzero(
            (buckets[1:] != buckets[:-1]) | ~finite[1:] | ~finite[:-1]) + 1]
        ends = np.r_[starts[1:], len(x)]
        counts = ends - starts
        safe_y = np.where(finite, y, 0.0)
        lows = np.minimum.reduceat(safe_y, starts)
        highs = np.maximum.reduceat(safe_y, starts)
        indices = np.arange(len(x))
        low_indices = np.minimum.reduceat(
            np.where(safe_y == np.repeat(lows, counts), indices, len(x)), starts)
        high_indices = np.minimum.reduceat(
            np.where(safe_y == np.repeat(highs, counts), indices, len(x)), starts)
        selected = np.unique(np.concatenate((starts, ends - 1, low_indices, high_indices)))
        return x[selected], y[selected]

    @staticmethod
    def _window_values(values, start, end):
        # Read a recent window from the nearest end, without walking all history.
        if isinstance(values, SampleHistory): return values.window(start, end)
        n = len(values)
        if start > n - end:
            return np.fromiter(itertools.islice(reversed(values), n-end, n-start), dtype=float)[::-1]
        return np.fromiter(itertools.islice(values, start, end), dtype=float)

    def _detail_changed(self, value):
        self.detail_value_label.setText('Completo' if value == 100 else f'{value} %')
        if getattr(self, '_last_display_frame', None) is not None:
            self._draw_display_frame(*self._last_display_frame)

    def _display_pixels(self, width):
        # Logarithmic range: 0.25 to 8 groups per logical pixel.
        return max(1, int(width * (0.25 * 32 ** (self.detail_slider.value()/99))))

    def _draw_display_frame(self, x_plot, y_slices, active_columns):
        view = self.plot_widget.getViewBox()
        xmin, xmax = view.viewRange()[0]
        pixels = self._display_pixels(view.width())
        for col, line in self.line_items.items():
            y_vals = y_slices.get(col, [])
            visible = col in active_columns and len(y_vals) == len(x_plot) and len(x_plot) > 0
            if visible:
                xp, yp = self._display_trace(x_plot, y_vals, xmin, xmax, pixels)
                line.setData(xp, yp, connect='finite')
            line.setVisible(visible)

    def _display_trace(self, x, y, xmin, xmax, pixels):
        if self.detail_slider.value() == 100:
            return self._prepare_trace_data(x, y)
        threshold = (max(3*self.current_dt_us, 1500.0) if self.current_dt_us > 0 else 2000.0) if self.x_axis_time_mode else 2.0
        has_gaps = self.auto_gap_cut and np.any(np.diff(x) > threshold)
        if has_gaps:
            # Keep explicit separators before reducing a discontinuous trace.
            xp, yp = self._prepare_trace_data(x, y)
            return self._reduce_trace_for_display(xp, yp, xmin, xmax, pixels)
        # Reduce real samples before constructing twice as many step vertices.
        xp, yp = self._reduce_trace_for_display(x, y, xmin, xmax, pixels)
        return self._prepare_trace_data(xp, yp, detect_gaps=False)

    def on_headers_detected(self, headers: List[str]):
        new_cols = [h for h in headers if h not in self.known_columns]
        if not new_cols:
            return

        for col in new_cols:
            self.known_columns.append(col)
            if col not in self.series:
                self.series[col] = SampleHistory(MAX_BUFFER_SAMPLES)
            if col not in self.selected_columns:
                self.selected_columns[col] = col in ("V_IN", "V_OUT")

        self._rebuild_column_controls(self.known_columns)

    def _set_single_state(self, state):
        armed = state == 'armed'
        captured = state == 'captured'
        self.single_btn.setChecked(armed or captured)
        if hasattr(self, 'temporal_single_marker'):
            ranges = self.plot_widget.getViewBox().viewRange()
            self.temporal_single_marker.setPos(ranges[0][1], ranges[1][1])
            self.temporal_single_marker.setVisible(captured)
        self.single_btn.setText('✓ SINGLE' if captured else '⚡ SINGLE')
        self.single_btn.setToolTip('SINGLE armado: esperando el trigger' if armed else
                                   'SINGLE capturado: pulsar para rearmar' if captured else 'Armar una captura SINGLE')
        background = '#f57c00' if armed else '#bf5000' if captured else '#e65100'
        color = '#ffffff'
        border = '#ffe0b2' if armed else '#ffbf69' if captured else '#ffa726'
        self.single_btn.setStyleSheet(f"QPushButton {{background:{background};color:{color};font-weight:bold;font-size:14px;border:2px solid {border};border-radius:6px;}} QPushButton:hover {{border-color:#ffd08a;}}")

    def toggle_run_stop(self):
        if hasattr(self, '_trigger_before_single'):
            previous = self._trigger_before_single
            del self._trigger_before_single
            self.trigger_checkbox.setChecked(previous)
        self.single_shot_armed = False
        self._set_single_state('idle')
        self._roll_position = None
        self.is_running = self.run_stop_btn.isChecked()
        if self.is_running:
            self.spectral.clear_single_marker()
            self.run_stop_btn.setText("▶ RUN")
            self._set_connection_status("Adquisición en vivo")
            self.status_label.setStyleSheet("""
                QLabel {
                    background:#171920;
                    border:1px solid #323946;
                    border-radius: 6px;
                    padding: 4px 10px;
                    color:#aeb8c8;
                    font-weight:normal;
                    font-size: 11px;
                }
            """)
        else:
            self.run_stop_btn.setText("⏹ STOP")
            self._set_connection_status("Pantalla congelada (STOP)")
            self.status_label.setStyleSheet("""
                QLabel {
                    background:#171920;
                    border:1px solid #323946;
                    border-radius: 6px;
                    padding: 4px 10px;
                    color:#aeb8c8;
                    font-weight:normal;
                    font-size: 11px;
                }
            """)

    def arm_single_shot(self):
        if not hasattr(self, '_trigger_before_single'):
            self._trigger_before_single = self.trigger_checkbox.isChecked()
        self.spectral.clear_single_marker()
        self.single_shot_armed = True
        self._set_single_state('armed')
        self.trigger_checkbox.setChecked(True)
        self.trigger_enabled = True
        self.trigger_edge_armed = False
        self.trigger_initialized = False
        self.trigger_sample_index = None
        self.is_running = True
        self.run_stop_btn.setChecked(True)
        self.run_stop_btn.setText("▶ RUN")
        self.trigger_status_label.setText("⚡ SINGLE armado: esperando cruce…")
        self.trigger_status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 6px;
                font-weight:normal;
                font-size: 11px;
                color:#aeb8c8;
            }
        """)

    def on_trigger_mode_changed(self, mode: str):
        self.trigger_mode = mode

    def reset_all_controls(self):
        self.dial_h_scale.setValue(VISIBLE_SAMPLES_DEFAULT)
        self.dial_h_pos.setValue(0)
        self.dial_v_scale.setValue(330)
        self.dial_v_pos.setValue(0)
        self.trigger_source_combo.setCurrentText("V_IN")
        self.dial_trigger_level.setValue(165)
        self.run_stop_btn.setChecked(True)
        self.toggle_run_stop()

    def _horizontal_dt_us(self):
        # Prefer sample timestamps; use the confirmed hardware period before DATA.
        return self.current_dt_us if self.current_dt_us > 0 else self.applied_configuration.period

    def _sync_horizontal_controls(self):
        dt = self._horizontal_dt_us()
        time_mode = self.x_axis_time_mode
        factor = dt / 1000 if time_mode else 1
        with QtCore.QSignalBlocker(self.lbl_h_scale):
            self.lbl_h_scale.setDecimals(1 if time_mode else 0)
            self.lbl_h_scale.setRange(VISIBLE_SAMPLES_MIN * factor, VISIBLE_SAMPLES_MAX * factor)
            self.lbl_h_scale.setSingleStep(factor)
            self.lbl_h_scale.setSuffix(" ms" if time_mode else " smp")
            self.lbl_h_scale.setValue(self.h_scale * factor)
        with QtCore.QSignalBlocker(self.dial_h_scale):
            self.dial_h_scale.setValue(self.h_scale)
        self.on_h_pos_changed(self.h_pos)

    def _on_h_scale_input(self, value):
        samples = round(value * 1000 / self._horizontal_dt_us()) if self.x_axis_time_mode else round(value)
        self.on_h_scale_changed(samples)

    def on_h_scale_changed(self, value: int):
        self.h_scale = max(VISIBLE_SAMPLES_MIN, min(VISIBLE_SAMPLES_MAX, int(value)))
        if self.x_axis_time_mode:
            self._h_time_ms = self.h_scale * self._horizontal_dt_us() / 1000
        self._sync_horizontal_controls()

    def on_h_pos_changed(self, value: int):
        self.h_pos = int(value)
        if self.x_axis_time_mode:
            text = f"{number(self.h_pos * self._horizontal_dt_us() / 1000, formats.n_1f)} ms"
        else:
            text = f"{self.h_pos} smp"
        self.lbl_h_pos.setText(text + (" (En vivo)" if self.h_pos == 0 else ""))

    def on_v_scale_changed(self, value: int):
        self.v_scale = max(0.2, value / 100.0)
        self.lbl_v_scale.setValue(self.v_scale)
        self._apply_vertical_range()

    def on_v_pos_changed(self, value: int):
        self.v_pos = value / 100.0
        self.lbl_v_pos.setText(f"{number(self.v_pos, formats.n_2f)} V")
        self._apply_vertical_range()

    def _apply_vertical_range(self):
        self.plot_widget.setYRange(self.v_pos, self.v_pos + self.v_scale, padding=0.02)

    def on_trigger_source_changed(self, source: str):
        self.trigger_source = source
        self._updating_trigger_line = True
        is_adc = "ADC" in source
        if is_adc:
            self.dial_trigger_level.setRange(0, int(self.adc_max))
            mid_val = self.adc_max / 2.0
            self.dial_trigger_level.setValue(int(mid_val))
            self.trigger_level = float(int(mid_val))
            self.lbl_trigger_level.setText(f"{int(self.trigger_level)}")
            self.trigger_line.setValue(self.trigger_level)
        else:
            self.dial_trigger_level.setRange(0, 330)
            self.dial_trigger_level.setValue(165)
            self.trigger_level = 1.65
            self.lbl_trigger_level.setText("1.65 V")
            self.trigger_line.setValue(self.trigger_level)
        self._updating_trigger_line = False
        self.configure_trigger()

    def on_trigger_level_dial_changed(self, value: int):
        if self._updating_trigger_line:
            return
        is_adc = "ADC" in self.trigger_source
        if is_adc:
            self.trigger_level = float(value)
            self.lbl_trigger_level.setText(f"{int(self.trigger_level)}")
        else:
            self.trigger_level = value / 100.0
            self.lbl_trigger_level.setText(f"{number(self.trigger_level, formats.n_2f)} V")

        self._updating_trigger_line = True
        self.trigger_line.setValue(self.trigger_level)
        self._updating_trigger_line = False

    def _on_trigger_line_dragged(self):
        if self._updating_trigger_line:
            return
        new_val = self.trigger_line.value()
        self._updating_trigger_line = True
        is_adc = "ADC" in self.trigger_source
        if is_adc:
            self.trigger_level = max(0.0, min(self.adc_max, new_val))
            self.lbl_trigger_level.setText(f"{int(self.trigger_level)}")
            self.dial_trigger_level.setValue(int(round(self.trigger_level)))
        else:
            self.trigger_level = max(0.0, min(3.3, new_val))
            self.lbl_trigger_level.setText(f"{number(self.trigger_level, formats.n_2f)} V")
            self.dial_trigger_level.setValue(int(round(self.trigger_level * 100)))
        self._updating_trigger_line = False

    def auto_center_trigger_level(self):
        """Calcula el punto medio (50%) de la señal activa y centra el nivel de disparo automáticamente."""
        source = self.trigger_source
        src_deque = self.series.get(source)
        if not src_deque or len(src_deque) < 10:
            return

        recent = self._window_values(src_deque, max(0, len(src_deque) - 1500), len(src_deque))
        v_min = min(recent)
        v_max = max(recent)
        v_mid = (v_min + v_max) / 2.0

        self._updating_trigger_line = True
        is_adc = "ADC" in source
        if is_adc:
            self.trigger_level = max(0.0, min(self.adc_max, v_mid))
            self.lbl_trigger_level.setText(f"{int(self.trigger_level)}")
            self.dial_trigger_level.setValue(int(round(self.trigger_level)))
            self.trigger_line.setValue(self.trigger_level)
        else:
            self.trigger_level = max(0.0, min(3.3, v_mid))
            self.lbl_trigger_level.setText(f"{number(self.trigger_level, formats.n_2f)} V")
            self.dial_trigger_level.setValue(int(round(self.trigger_level * 100)))
            self.trigger_line.setValue(self.trigger_level)
        self._updating_trigger_line = False

        if not self.trigger_checkbox.isChecked():
            self.trigger_checkbox.setChecked(True)
        else:
            self.configure_trigger()

    def configure_trigger(self):
        self.trigger_enabled = self.trigger_checkbox.isChecked()
        self.trigger_source = self.trigger_source_combo.currentText()
        self.trigger_edge = self.trigger_edge_combo.currentText()
        self.trigger_edge_armed = False
        self.trigger_initialized = False
        self.trigger_sample_index = None
        self.frozen_frame = None

        self.trigger_line.setVisible(self.trigger_enabled)
        self.trigger_t_marker.setVisible(self.trigger_enabled)

        if self.trigger_enabled:
            is_adc = "ADC" in self.trigger_source
            unit = "" if is_adc else "V"
            val_str = f"{int(self.trigger_level)}" if is_adc else f"{number(self.trigger_level, formats.n_2f)}"
            self.trigger_status_label.setText(
                f"● Armado: {self.trigger_source} {self.trigger_edge} a {val_str}{unit}"
            )
            self.trigger_status_label.setStyleSheet("""
                QLabel {
                    background:#171920;
                    border:1px solid #323946;
                    border-radius: 6px;
                    padding: 6px;
                    font-weight:normal;
                    font-size: 11px;
                    color:#aeb8c8;
                }
            """)
        else:
            self.trigger_status_label.setText("● Modo continuo")
            self.trigger_status_label.setStyleSheet("""
                QLabel {
                    background:#171920;
                    border:1px solid #323946;
                    border-radius: 6px;
                    padding: 6px;
                    font-weight:normal;
                    font-size: 11px;
                    color:#aeb8c8;
                }
            """)

    def _create_log_filename(self):
        folder = ROOT/'capturas/v13'
        folder.mkdir(parents=True, exist_ok=True)
        rate = f'{self.applied_configuration.rate / 1000:g}kHz'
        stem = datetime.now().strftime('log_%Y%m%d_%H%M%S') + f'_{self.applied_configuration.bits}bit_{rate}'
        candidate = stem
        number = 2
        while any((folder/f'{candidate}.{ext}').exists() for ext in ('csv', 'wav')):
            candidate = f'{stem}_{number}'
            number += 1
        return folder/f'{candidate}.{self.record_format.lower()}'

    def _record_format_changed(self, selected):
        if hasattr(self, "record_dc_checkbox"):
            self.record_dc_checkbox.setEnabled(selected == "WAV" and not self.recording)
        if not self.recording:
            self.record_status_label.setText(f"{selected}: listo | máximo 30.0 s")

    def start_recording(self):
        if self.recording:
            return
        if self.demo_mode and self.record_format_combo.currentText() == "WAV":
            QtWidgets.QMessageBox.warning(self, "Grabación WAV", "WAV graba las entradas A2/A3 del Q. Demo usa una tasa simulada; elegí CSV para grabarla.")
            return
        if self.serial_worker is None and not self.demo_mode:
            QtWidgets.QMessageBox.warning(self, "Grabación", "Conectá el Q de control o iniciá Demo antes de grabar.")
            return
        try:
            self.record_format = self.record_format_combo.currentText()
            self.record_previous = None
            self.record_dc_filter = DCBlocker(self.applied_configuration.rate) if self.record_format == "WAV" and self.record_dc_checkbox.isChecked() else None
            path = self._create_log_filename()
            if self.record_format == "WAV":
                self.record_file = path.open("wb", buffering=1024 * 1024)
                self.record_wave = wave.open(self.record_file, "wb")
                self.record_wave.setparams((2, 2, self.applied_configuration.rate, 0, "NONE", "not compressed"))
            else:
                self.record_file = path.open("w", encoding="utf-8", newline="", buffering=1024 * 1024)
                self.record_writer = csv.writer(self.record_file, delimiter=",")
                self.record_writer.writerow(["Muestra", "Tiempo_us", "ADC_IN", "V_IN", "ADC_OUT", "V_OUT"])
            self.record_filename = str(path)
            self.record_rows = 0
            self.record_start_time = time.perf_counter()
            self.record_last_flush_time = self.record_start_time
            self.recording = True
            self.record_format_combo.setEnabled(False)
            self.record_dc_checkbox.setEnabled(False)
            self.record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(True)
            self.record_timer.start()
            self._update_recording_status()
        except Exception as exc:
            self._close_record_file()
            QtWidgets.QMessageBox.critical(self, "Error de grabación", f"No se pudo crear el archivo:\n{exc}")

    def _write_record_batch(self, batch: List[Dict[str, float]]):
        if not self.recording:
            return
        if time.perf_counter() - self.record_start_time >= RECORD_MAX_SECONDS:
            self.stop_recording(auto=True)
            return
        try:
            if self.record_format == "WAV":
                self._write_wave_batch(batch)
                return
            rows = [[s.get("Muestra", ""), s.get("Tiempo (us)", ""), s.get("ADC_IN", ""),
                     s.get("V_IN", ""), s.get("ADC_OUT", ""), s.get("V_OUT", "")] for s in batch]
            self.record_writer.writerows(rows)
            self.record_rows += len(rows)
            now = time.perf_counter()
            if now - self.record_last_flush_time >= RECORD_FLUSH_SECONDS:
                self.record_file.flush()
                self.record_last_flush_time = now
        except Exception as exc:
            self.stop_recording(error_message=str(exc))

    def _write_wave_batch(self, batch):
        if not batch:
            return
        # Validate full input, including the boundary with the last written batch.
        data = np.array([[s["Muestra"], s["Tiempo (us)"], s["ADC_IN"], s["ADC_OUT"]] for s in batch], dtype=np.float64)
        if not np.isfinite(data).all() or not np.equal(data, np.floor(data)).all():
            raise ValueError("WAV: muestras o timestamps inválidos")
        maximum = self.applied_configuration.maximum
        if np.any(data[:, 2:] < 0) or np.any(data[:, 2:] > maximum):
            raise ValueError("WAV: ADC fuera del rango confirmado")
        positions = data[:, :2].astype(np.int64)
        if self.record_previous is not None:
            positions = np.vstack((self.record_previous, positions))
        differences = np.diff(positions, axis=0) & 0xffffffff
        if np.any(differences[:, 0] != 1) or np.any(differences[:, 1] != self.applied_configuration.period):
            raise ValueError("WAV: discontinuidad de muestras o timestamps; archivo detenido sin rellenar huecos")
        audio = data[:, 2:] * (65535.0 / maximum) - 32768.0
        if self.record_dc_filter is not None:
            audio = self.record_dc_filter.process(audio)
        pcm = np.clip(np.rint(audio), -32768, 32767).astype('<i2')
        self.record_wave.writeframesraw(pcm.tobytes())
        self.record_previous = positions[-1].copy()
        self.record_rows += len(batch)
        now = time.perf_counter()
        if now - self.record_last_flush_time >= RECORD_FLUSH_SECONDS:
            self.record_file.flush()
            self.record_last_flush_time = now

    def _update_recording_status(self):
        if not self.recording:
            return
        elapsed = min(time.perf_counter() - self.record_start_time, RECORD_MAX_SECONDS)
        self.record_status_label.setText(f"● {self.record_format} {number(elapsed, formats.n04_1f)}/30.0 s | {number(self.record_rows, formats.n_)} muestras")
        self.record_status_label.setStyleSheet("background:#171920;border:1px solid #323946;padding:4px;color:#aeb8c8;font-weight:normal;")
        if elapsed >= RECORD_MAX_SECONDS:
            self.stop_recording(auto=True)

    def _close_record_file(self):
        close_error = None
        try:
            if self.record_wave is not None:
                self.record_wave.close()  # Finalize RIFF sizes before closing its stream.
        except Exception as exc:
            close_error = str(exc)
        finally:
            self.record_wave = None
            if self.record_file is not None:
                try:
                    self.record_file.close()
                except Exception as exc:
                    close_error = close_error or str(exc)
            self.record_file = None
            self.record_writer = None
        return close_error

    def stop_recording(self, checked=False, auto=False, error_message=None):
        was_recording = self.recording
        self.recording = False
        self.record_timer.stop()
        close_error = self._close_record_file()
        error_message = error_message or close_error
        self.record_format_combo.setEnabled(True)
        self.record_dc_checkbox.setEnabled(self.record_format_combo.currentText() == "WAV")
        self.record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        filename = Path(self.record_filename).name if self.record_filename else ""
        if error_message:
            self.record_status_label.setText(f"Error {self.record_format}: {error_message}")
            self.record_status_label.setStyleSheet("color:#aeb8c8;font-weight:normal;")
            if was_recording:
                QtWidgets.QMessageBox.critical(self, "Error de grabación", f"La grabación se detuvo:\n{error_message}")
        elif was_recording:
            reason = "límite de 30 s" if auto else "detenida por usuario"
            display_name = re.sub(r'_\d+bit_[0-9.]+(?:kHz|Hz)', '', filename)
            self.record_status_label.setText(f"Guardado: {display_name}")
            self.record_status_label.setToolTip(f"{self.record_filename}\n{number(self.record_rows, formats.n_)} muestras · {reason}")
            self.record_status_label.setStyleSheet("color:#aeb8c8;font-weight:normal;")

    def _update_port_tooltip(self, index):
        self.port_combo.setToolTip(
            self.port_combo.itemData(index, QtCore.Qt.ItemDataRole.ToolTipRole) or "Seleccionar puerto serial")

    def refresh_ports(self):
        selected = self.port_combo.currentData()
        selected_r4 = self.r4_combo.currentData()
        self.port_combo.clear()
        self.r4_combo.clear()
        self.r4_combo.addItem('Seleccionar R4…', None)
        try:
            devices = usb_devices()
            for serial in devices:
                self.port_combo.addItem(f'UNO Q USB — {serial}', serial)
            if selected in devices:
                self.port_combo.setCurrentIndex(devices.index(selected))
            # Exclude Q's router serial interface: it is not an R4 data port.
            for port in list_ports.comports():
                if port.vid is None or port.serial_number in devices or (port.vid, port.pid) == (0x2341, 0x0078):
                    continue
                label = f'{port.description} — {port.device}'
                self.r4_combo.addItem(label, port.device)
                if port.device == selected_r4:
                    self.r4_combo.setCurrentIndex(self.r4_combo.count()-1)
            if self.serial_worker is None:
                self._set_connection_status('Elegir el Q de control y el destino de muestras' if devices
                                          else 'No se encontró un UNO Q conectado por USB')
        except Exception as exc:
            self._set_connection_status(str(exc))
        self.port_combo.setToolTip('UNO Q de control por USB. Requiere la aplicación dual iniciada.')

    def _acquisition_confirmed(self, bits, rate):
        config = Configuration(bits, rate)
        if config != self.applied_configuration:
            if self.recording: self.stop_recording()
            self.clear_data()
            for curve in self.line_items.values(): curve.setData([], [])
            for label in (self.val_vmax,self.val_vmin,self.val_vpp,self.val_vrms,self.val_vavg,self.val_freq): label.setText('--')
        self.applied_configuration = config
        if self.x_axis_time_mode:
            duration = getattr(self, '_h_time_ms', self.h_scale * config.period / 1000)
            self.h_scale = max(VISIBLE_SAMPLES_MIN, min(VISIBLE_SAMPLES_MAX, round(duration * 1000 / config.period)))
        self._sync_horizontal_controls()
        self.spectral.bode.update_estimate()
        self.spectral.bode.refresh_reference()
        self.adc_combo.setCurrentText(f'{bits} bits ({(1 << bits)-1})')
        self.adc_summary_label.setText(f'{bits} bits')
        self._refresh_applied_summary()

    def _set_connection_status(self, text):
        aliases = {'Adquisición en vivo': 'Activo',
                   'Pantalla congelada (STOP)': 'Congelado (STOP)',
                   'Pantalla congelada (SINGLE capturado)': 'Congelado · SINGLE capturado',
                   'Adquisición aplicada · control Q conectado': 'Conectado',
                   'Esperando confirmación del Q…': 'Conectando Q…'}
        message = aliases.get(text, text)
        if text in aliases and self.serial_worker is not None and not self.output_pending:
            mode = getattr(self, 'confirmed_mode', None)
            if mode is not None:
                config = self.applied_configuration
                link = 'SPI' if mode == int(Mode.SPI) else 'UART · R4'
                bits = f'{config.bits} bits' + (' (OS)' if config.bits == 16 else '')
                rate = f'{number(config.rate/1000)}' + ' kHz'
                message += f' · {link} · {bits} · {rate}'
        self.status_label.setText(message)
        self.status_label.setToolTip(message)

    def _refresh_applied_summary(self):
        config = self.applied_configuration
        mode = getattr(self, 'confirmed_mode', None)
        port = getattr(self, 'confirmed_r4', '')
        name = 'SPI · UNO Q' if mode == int(Mode.SPI) else f'UART · R4 {port}'
        self.confirmed_output_label.setText(f'{name} · {config.bits} bits' + (' OS ×16' if config.bits == 16 else '') + ' · ' + f'{number(config.rate/1000, formats.ng)}' + ' kHz')
        self._set_connection_status('Adquisición en vivo' if self.is_running else 'Pantalla congelada (STOP)')

    def _destination_changed(self):
        if hasattr(self, 'config_rate_combo'):
            uart = self.destination_combo.currentData() == int(Mode.UART)
            for i in range(self.config_rate_combo.count()):
                rate = self.config_rate_combo.itemData(i)
                allowed = (not uart or rate in UART_RATES) and (self.config_bits_combo.currentData() != 16 or rate <= 62500)
                self.config_rate_combo.model().item(i).setEnabled(allowed)
                bits = self.config_bits_combo.currentData()
                label = f'{number(rate/1000, formats.ng)}' + f' kHz · {1000000//rate} µs'
                if bits != 16 or rate <= 62500:
                    profile = Configuration(bits, rate)
                    acquisition = f'{number(profile.sampling_us, formats.ng)}'
                    tooltip = (f'Período entre pares: {profile.period} µs.\n'
                               f'Adquisición por canal y subconversión: {acquisition} µs '
                               f'({profile.sampling_cycles} ciclos ADC).\n'
                               + ('16 subconversiones por canal.\n' if bits == 16 else '')
                               + 'Menor tiempo de adquisición exige menor impedancia de fuente.\n'
                               + 'El límite en ohmios depende del circuito y la precisión buscada.')
                else:
                    tooltip = 'Esta tasa no admite el oversampling ×16 de ambos canales.'
                self.config_rate_combo.setItemText(i, label)
                self.config_rate_combo.setItemData(i, tooltip, QtCore.Qt.ItemDataRole.ToolTipRole)
            if self.config_bits_combo.currentData() == 16 and self.config_rate_combo.currentData() > 62500:
                self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(62500))
            if uart and self.config_rate_combo.currentData() not in UART_RATES:
                self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(31250))
        if hasattr(self, 'r4_combo'):
            self.r4_combo.setVisible(self.destination_combo.currentData() == int(Mode.UART))
            self.r4_combo.setEnabled(self.destination_combo.currentData() == int(Mode.UART)
                                     and not self.output_pending)

    def _set_output_pending(self, pending):
        self.output_pending = pending
        if pending:
            self._set_connection_status('Aplicando adquisición…')
            self.baud_input.setText('…')
        self._destination_changed()
        self._sync_wav_transport()
        if not pending and self.serial_worker is not None and getattr(self, "confirmed_mode", None) is not None:
            self._refresh_applied_summary()

    def _output_confirmed(self, mode, r4_port):
        self._set_connect_state('connected')
        self.confirmed_mode, self.confirmed_r4 = mode, r4_port
        self.control_summary_label.setText(str(self.port_combo.currentData()))
        self.baud_input.setText('SPI' if mode == int(Mode.SPI) else 'UART 3M')
        self._refresh_applied_summary()

    def _schedule_configuration(self):
        if self._wav_preparing or self._wav_active: return
        if self.serial_worker is not None and not self.output_pending:
            self._auto_apply_timer.start()

    def _auto_apply_configuration(self):
        if self.serial_worker is None or self.output_pending or self._wav_preparing or self._wav_active: return
        if self.destination_combo.currentData() == int(Mode.UART) and not self.r4_combo.currentData():
            self._set_connection_status('Seleccionar el R4 para aplicar la salida UART')
            return
        self.apply_output()

    def apply_output(self):
        if self._wav_preparing or self._wav_active: return
        mode = self.destination_combo.currentData()
        port = self.r4_combo.currentData()
        if mode == int(Mode.UART) and not port:
            QtWidgets.QMessageBox.warning(self, 'R4', 'Seleccionar el puerto USB del R4.')
            return
        if self.serial_worker is not None and not self.output_pending:
            config = Configuration(self.config_bits_combo.currentData(), self.config_rate_combo.currentData())
            if config != self.applied_configuration and self.recording:
                self.stop_recording()
            self._set_output_pending(True)
            self.serial_worker.request_output(mode, port, config)

    def _set_connect_state(self, state):
        self.connection_state = state
        self.connect_button.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v13/assets' / f'plug_{state}.svg')))
        self.connect_button.setIconSize(QtCore.QSize(18, 18))
        labels = {'disconnected': 'Conectar', 'connecting': 'Conectando…', 'connected': 'Desconectar'}
        self.connect_button.setText('  ' + labels[state])
        self.connect_button.setToolTip('Cancelar conexión' if state == 'connecting' else labels[state])

    def prepare_q(self):
        if self._q_preparation is not None and self._q_preparation.isRunning():
            return
        serial = self.port_combo.currentData()
        if not serial:
            QtWidgets.QMessageBox.warning(self, 'UNO Q', 'Conectar el Q por USB y actualizar la lista.')
            return
        self.stop_input()
        self._q_preparation = QPreparationThread(serial, self)
        for widget in (self.prepare_q_button, self.connect_button, self.demo_button,
                       self.port_combo, self.refresh_button):
            widget.setEnabled(False)
        self._q_preparation.progress.connect(self._set_connection_status)
        self._q_preparation.result.connect(self._q_prepared)
        self._q_preparation.finished.connect(self._q_preparation_finished)
        self._set_connection_status('Preparando Q…')
        self._q_preparation.start()

    def _q_prepared(self, success, text):
        self._set_connection_status(text)

    def _q_preparation_finished(self):
        for widget in (self.prepare_q_button, self.connect_button, self.demo_button,
                       self.port_combo, self.refresh_button):
            widget.setEnabled(True)

    def connect_serial(self):
        if self._q_preparation is not None and self._q_preparation.isRunning():
            return
        if self.serial_worker is not None or self.demo_mode:
            self.stop_input()
            return
        self.stop_input()
        port = self.port_combo.currentData()
        if not port:
            QtWidgets.QMessageBox.warning(self, 'UNO Q', 'Conectar el UNO Q por USB y actualizar la lista.')
            return
        mode = self.destination_combo.currentData()
        r4_port = self.r4_combo.currentData()
        if mode == int(Mode.UART) and not r4_port:
            QtWidgets.QMessageBox.warning(self, 'R4', 'Seleccionar el puerto USB del R4.')
            return
        self.clear_data()
        self.serial_thread = QtCore.QThread()
        self.serial_worker = OutputWorker(port, mode, r4_port, Configuration(
            self.config_bits_combo.currentData(), self.config_rate_combo.currentData()),
            autoload=True,
            initial_generator=self._generator_config() if self.generator_mode.currentIndex() == 0 else None)
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        worker = self.serial_worker
        self.serial_worker.batch_ready.connect(lambda batch: self._from_worker(worker, self.handle_batch, batch))
        self.serial_worker.headers_detected.connect(lambda headers: self._from_worker(worker, self.on_headers_detected, headers))
        self.serial_worker.status_changed.connect(lambda text: self._from_worker(worker, self._set_connection_status, text))
        self.serial_worker.output_confirmed.connect(lambda mode, r4: self._from_worker(worker, self._output_confirmed, mode, r4))
        self.serial_worker.acquisition_confirmed.connect(lambda bits, rate: self._from_worker(worker, self._acquisition_confirmed, bits, rate))
        self.serial_worker.generator_confirmed.connect(lambda reply: self._from_worker(worker, self._generator_confirmed, reply))
        self.serial_worker.instrument_confirmed.connect(lambda identity: self._from_worker(worker, self.spectral.bode.set_instrument, identity))
        self.serial_worker.wav_confirmed.connect(lambda reply: self._from_worker(worker, self._wav_confirmed, reply))
        self.serial_worker.switching.connect(lambda pending: self._from_worker(worker, self._set_output_pending, pending))
        self.serial_worker.error_occurred.connect(lambda text: self._from_worker(worker, self._on_worker_error, text))
        self.serial_worker.finished.connect(self.serial_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        # Keep the QThread alive until stop_input() finishes inspecting/joining it.
        self.port_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self._set_output_pending(True)
        self._set_connect_state('connecting')
        self.serial_thread.start()
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(False)

    def _from_worker(self, worker, callback, *args):
        # Qt may deliver queued signals after stop_input() joined the old thread.
        if worker is self.serial_worker:
            callback(*args)

    def _on_worker_error(self, message: str):
        self.stop_input()
        self._set_connection_status(f"Error: {message}")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 4px 10px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)
        QtWidgets.QMessageBox.critical(self, "Error de conexión", message)

    def start_demo(self):
        self.stop_input()
        self.clear_data()
        self.demo_mode = True
        self.start_time = time.perf_counter()
        self.demo_v_out_prev = 0.0
        self._set_connection_status("Demo activo · V_IN cuadrada / V_OUT filtro RC")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 4px 10px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)

        if self.demo_timer is None:
            self.demo_timer = QtCore.QTimer(self)
            self.demo_timer.timeout.connect(self._generate_demo_samples)

        self._set_connect_state('connected')
        self.demo_timer.start(20)
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(False)

    def _generate_demo_samples(self):
        """Genera simulación de 2 canales: V_IN (Generador) y V_OUT (Respuesta de circuito RC)."""
        batch = []
        dt = 0.0004  # 2.5 kHz
        t_base = self.sample_counter * dt
        tau = 0.035  # Constante de tiempo RC (35 ms)

        for i in range(50):
            t = t_base + i * dt
            period = 0.4  # 2.5 Hz onda cuadrada
            phase = (t % period) / period

            # V_IN: Señal cuadrada limpia entre 0.1V y 3.2V
            v_in = 3.2 if phase < 0.5 else 0.1

            # V_OUT: Respuesta analógica exponencial del condensador RC
            alpha = dt / (tau + dt)
            self.demo_v_out_prev += alpha * (v_in - self.demo_v_out_prev)
            v_out = max(0.0, min(3.3, self.demo_v_out_prev))

            adc_in = int(v_in * self.adc_max / 3.3)
            adc_out = int(v_out * self.adc_max / 3.3)

            sample = {
                "Muestra": float(self.sample_counter + i + 1),
                "Tiempo (us)": float(int(t * 1_000_000)),
                "ADC_IN": float(adc_in),
                "V_IN": v_in,
                "ADC_OUT": float(adc_out),
                "V_OUT": v_out,
            }
            batch.append(sample)

        self.handle_batch(batch)

    def stop_input(self):
        self.spectral.bode.cancel('Control desconectado: no se pudo restaurar el generador', restore=False)
        self._generator_state_known=False
        self._wav_capable=False
        self._wav_active=False
        self._wav_cancelled=True
        self._sync_wav_transport()
        self._auto_apply_timer.stop()
        self._generator_timer.stop()
        self._generator_requested=None
        self.generator_status.setText("Control Q desconectado")
        # ADB setup/cleanup has bounded subprocess timeouts. Never destroy a
        # QThread while its worker is still opening/closing the USB tunnel.
        if self.serial_worker is not None:
            self.serial_worker.stop()
        if self.serial_thread is not None and self.serial_thread.isRunning():
            self.serial_thread.quit()
            self.serial_thread.wait(12000)
        if self.recording:
            self.stop_recording()
        self.demo_mode = False
        if self.demo_timer is not None and self.demo_timer.isActive():
            self.demo_timer.stop()

        if self.serial_worker is not None:
            self.serial_worker.stop()

        if self.serial_thread is not None:
            if self.serial_thread.isRunning():
                self.serial_thread.quit()
                self.serial_thread.wait(1000)
            self.serial_thread.deleteLater()
            self.serial_thread = None

        self.serial_worker = None
        self.spectral.bode.set_instrument(None)
        self._set_connect_state('disconnected')
        self.port_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self._set_output_pending(False)
        self.confirmed_output_label.setText('Destino confirmado: sin conexión')
        self.baud_input.setText('—')
        self.control_summary_label.setText('Sin conexión')
        self.adc_summary_label.setText('—')
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self._set_connection_status("Detenido")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 4px 10px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)

    def clear_data(self):
        self.spectral.bode.cancel('Adquisición reiniciada')
        self.spectral.reset()
        self._last_display_frame = None
        self._roll_position = None
        self.sample_counter = 0
        self.batch_queue_delay_ms = 0.0
        self.batch_queue_delay_max_ms = 0.0
        self.timed_batch_count = 0
        self.sample_numbers.clear()
        for d in self.series.values():
            d.clear()
        self.trigger_sample_index = None
        self.trigger_edge_armed = False
        self.trigger_initialized = False
        self.frozen_frame = None
        self.last_fs_calc_time = time.perf_counter()
        self.last_fs_sample_count = 0
        self.current_fs_hz = 0.0
        self.current_dt_us = 0.0
        self.lbl_top_fs.setText("-- S/s")

    @staticmethod
    def _apply_step_hold(
        x_arr: List[float],
        y_arr: List[float],
        gap_factor: float = 3.0,
    ) -> Tuple[List[float], List[float]]:
        """
        Zero-Order Hold: ante un hueco de tiempo > gap_factor * dt_mediano,
        inserta un punto 'hold' con el último valor Y justo antes del siguiente
        punto para que la línea se mantenga horizontal en vez de trazar diagonal.
        """
        n = len(x_arr)
        if n < 2:
            return list(x_arr), list(y_arr)

        # Calcular dt mediano (robusto contra outliers)
        dts = [x_arr[i + 1] - x_arr[i] for i in range(n - 1)]
        sorted_dts = sorted(dts)
        median_dt = sorted_dts[len(sorted_dts) // 2]
        threshold = median_dt * gap_factor

        if threshold <= 0:
            return list(x_arr), list(y_arr)

        new_x: List[float] = [x_arr[0]]
        new_y: List[float] = [y_arr[0]]

        for i in range(1, n):
            gap = x_arr[i] - x_arr[i - 1]
            if gap > threshold:
                # Insertar punto hold: tiempo justo antes del siguiente sample
                eps = min(gap * 0.001, median_dt * 0.1)
                new_x.append(x_arr[i] - eps)
                new_y.append(y_arr[i - 1])   # sostener el último valor
            new_x.append(x_arr[i])
            new_y.append(y_arr[i])

        return new_x, new_y

    def _calculate_sample_rate(self) -> Tuple[float, float, str]:
        """Calcula la frecuencia de muestreo Fs y el periodo medio entre muestras (dt_us)."""
        tiempo_deque = self.series.get("Tiempo (us)")
        n = len(tiempo_deque) if tiempo_deque else 0

        now = time.perf_counter()
        fs_hz = 0.0
        dt_us = 0.0

        # Método 1: A partir de los timestamps físicos de microsegundos enviados por hardware
        if tiempo_deque and n >= 10:
            N = min(500, n)
            t_start = tiempo_deque[-N]
            t_end = tiempo_deque[-1]
            delta_t = t_end - t_start
            if delta_t > 0:
                dt_us = delta_t / (N - 1)
                if dt_us > 0:
                    fs_hz = 1_000_000.0 / dt_us
                    self.current_fs_hz = fs_hz
                    self.current_dt_us = dt_us

        # Método 2: Fallback por tasa de llegada de muestras en el PC
        if fs_hz <= 0.0:
            dt_pc = now - self.last_fs_calc_time
            if dt_pc >= 0.5:
                delta_samples = self.sample_counter - self.last_fs_sample_count
                if delta_samples > 0:
                    fs_hz = delta_samples / dt_pc
                    dt_us = (1_000_000.0 / fs_hz) if fs_hz > 0 else 0.0
                    self.current_fs_hz = fs_hz
                    self.current_dt_us = dt_us
                self.last_fs_calc_time = now
                self.last_fs_sample_count = self.sample_counter
            else:
                fs_hz = self.current_fs_hz
                dt_us = self.current_dt_us

        if fs_hz > 0.0:
            if fs_hz >= 1_000_000.0:
                text = f"{number(fs_hz / 1_000_000.0, formats.n_2f)} MS/s"
            elif fs_hz >= 1000.0:
                text = f"{number(fs_hz / 1000.0, formats.n_2f)} kS/s"
            else:
                text = f"{number(fs_hz, formats.n_1f)} S/s"
        else:
            text = "-- S/s"

        if getattr(self, '_horizontal_display_dt', None) != round(self._horizontal_dt_us(), 6):
            self._horizontal_display_dt = round(self._horizontal_dt_us(), 6)
            if self.x_axis_time_mode:
                duration = getattr(self, '_h_time_ms', self.h_scale * self._horizontal_dt_us() / 1000)
                self.h_scale = max(VISIBLE_SAMPLES_MIN, min(VISIBLE_SAMPLES_MAX, round(duration * 1000 / self._horizontal_dt_us())))
            self._sync_horizontal_controls()
        return fs_hz, dt_us, text

    @QtCore.pyqtSlot(list)
    def handle_batch(self, batch: List[Dict[str, float]]):
        if not batch:
            return

        published_at = getattr(batch, 'published_at', None)
        if published_at is not None:
            self.batch_queue_delay_ms = max(0.0, (time.monotonic()-published_at)*1000)
            self.batch_queue_delay_max_ms = max(self.batch_queue_delay_max_ms, self.batch_queue_delay_ms)
            self.timed_batch_count += 1
        self._write_record_batch(batch)
        size = len(batch)
        self.sample_numbers.extend(range(self.sample_counter+1, self.sample_counter+size+1))
        self.sample_counter += size
        columns = set().union(*(sample.keys() for sample in batch))
        for col in columns:
            if col not in self.series:
                self.series[col] = SampleHistory(MAX_BUFFER_SAMPLES)
        for col, history in self.series.items():
            history.extend(np.fromiter((sample.get(col, 0.0) for sample in batch), dtype=float, count=size))
        self.spectral.bode.batch(batch)

    def _roll_end_position(self, total_samples, now):
        """Cabezal visual absoluto: sigue los lotes sin alterar sus muestras.

        Usa índices absolutos para seguir avanzando cuando el buffer está lleno.
        Al cambiar controles o volver de una pausa, reposiciona inmediatamente.
        Nunca extrapola más allá de los datos realmente recibidos.
        """
        context = (self.h_scale, self.h_pos, self.x_axis_time_mode)
        target = float(self.sample_counter)
        if (self._roll_position is None or context != self._roll_context
                or self._roll_time is None or now - self._roll_time > 0.25):
            self._roll_position = target
        else:
            elapsed = max(0.0, now - self._roll_time)
            alpha = -math.expm1(-elapsed / ROLL_SMOOTH_SECONDS)
            self._roll_position += (target - self._roll_position) * alpha
            if target - self._roll_position < 0.01:
                self._roll_position = target
        self._roll_time = now
        self._roll_context = context
        # Mantener una ventana completa dentro del buffer disponible.
        oldest = self.sample_counter - total_samples
        self._roll_position = min(target, max(oldest + self.h_scale, self._roll_position))
        return self._roll_position - oldest

    def render_frame(self):
        if not self.is_running:
            return

        total_samples = len(self.sample_numbers)
        if total_samples < 2:
            return

        active_columns = [col for col, checked in self.selected_columns.items() if checked]
        if not active_columns:
            active_columns = ["V_IN", "V_OUT"]

        # Spectral modes display their own curves. Keep shared measurements/Fs
        # current, but do not prepare and draw a hidden temporal trace at 60 Hz.
        # SINGLE still uses the existing trigger/freeze path in any mode.
        if self.spectral.mode != 0 and not self.single_shot_armed:
            self._roll_position = None
            fs_hz, dt_us, fs_text = self._calculate_sample_rate()
            self.lbl_top_fs.setText(fs_text)
            if time.perf_counter()-getattr(self, '_last_measurement_update', 0) >= .1:
                end = total_samples
                start = max(0, end-self.h_scale)
                meas_col = self.active_meas_channel if self.active_meas_channel in active_columns else active_columns[0]
                slices = {name:self._window_values(self.series[name], start, end)
                          for name in (meas_col, 'Tiempo (us)') if name in self.series}
                self._update_live_measurements(slices, active_columns)
            return

        if self.selection_dirty or not self.line_items:
            self._update_curve_items(active_columns)

        w = self.h_scale

        # MODO CONTINUO (Roll) vs MODO TRIGGER (Estabilizado con fase fija)
        if not self.trigger_enabled:
            # 1. Modo Continuo: El osciloscopio hace barrido de izquierda a derecha (Roll)
            end_pos = max(w, total_samples + self.h_pos)
            end_pos = min(end_pos, total_samples)
            fraction = 0.0
            if self.h_pos == 0 and total_samples >= w:
                visual_end = self._roll_end_position(total_samples, time.perf_counter())
                end_pos = int(visual_end)
                fraction = visual_end - end_pos
            else:
                self._roll_position = None
            start_pos = max(0, end_pos - w)

            count = end_pos - start_pos

            # ---- EJE X: MUESTRAS o TIEMPO REAL (µs) ----
            if self.x_axis_time_mode:
                t_deque = self.series.get("Tiempo (us)")
                if t_deque and len(t_deque) >= end_pos and count > 0:
                    t_slice = self._window_values(t_deque, start_pos, end_pos)
                    t0 = t_slice[0]
                    x_plot = np.asarray(t_slice, dtype=float) - t0
                    x_end = x_plot[-1] if len(x_plot) else w
                    # Trasladar también fracciones de muestra, sin interpolar Y.
                    dt_visual = (t_slice[1] - t0) if count > 1 else 0.0
                    x_plot -= fraction * dt_visual
                    self.plot_widget.setXRange(0, x_end, padding=0.02)
                    self.plot_widget.setLabel("bottom", "Tiempo relativo en ventana (µs)", color="#ffffff")
                else:
                    # Sin timestamps: fallback a muestras silenciosamente
                    x_plot = np.arange(count, dtype=float) - fraction
                    self.plot_widget.setXRange(0, w, padding=0.0)
                    self.plot_widget.setLabel("bottom", "Muestras en ventana (sin timestamps)", color="#ffffff")
            else:
                x_plot = np.arange(count, dtype=float) - fraction
                self.plot_widget.setXRange(0, w, padding=0.0)
                self.plot_widget.setLabel("bottom", "Muestras en ventana", color="#ffffff")

            y_slices = {}
            for col in active_columns:
                series_deque = self.series.get(col)
                if series_deque and len(series_deque) >= end_pos:
                    y_slices[col] = self._window_values(series_deque, start_pos, end_pos)
                else:
                    y_slices[col] = []

            self.trigger_t_marker.setVisible(False)

        else:
            self._roll_position = None
            # 2. Modo Trigger: El disparo se fija en X = 0 (Pre-trigger con H-Pos)
            shift = self.h_pos
            pre_samples = max(0, min(w - 1, int(w * 0.10) - shift))
            post_samples = w - pre_samples

            # ---- EJE X en modo TRIGGER: Muestras relativas o µs relativos al T=0 ----
            if self.x_axis_time_mode and self.current_dt_us > 0:
                dt = self.current_dt_us
                x_plot = np.arange(-pre_samples, post_samples, dtype=float) * dt
                self.plot_widget.setXRange(x_plot[0], x_plot[-1], padding=0.0)
            else:
                x_plot = np.arange(-pre_samples, post_samples, dtype=float)
                self.plot_widget.setXRange(-pre_samples, post_samples, padding=0.0)

            self.trigger_t_marker.setValue(0)
            self.trigger_t_marker.setVisible(True)

            source = self.trigger_source
            src_deque = self.series.get(source)
            n = len(src_deque) if src_deque else 0

            found_t_idx = None
            if src_deque and n >= (pre_samples + post_samples):
                required_post = post_samples
                if self.single_shot_armed and self.spectral.mode in (1, 2):
                    fft_samples = int(self.spectral.size.currentText())
                    required_post = max(required_post, fft_samples - fft_samples // 10)
                end_search = n - required_post
                search_window = min(n - required_post - pre_samples, max(3000, w * 4))
                start_search = end_search - search_window

                if start_search >= pre_samples and end_search > start_search:
                    search_vals = self._window_values(src_deque, start_search - 1, end_search + 1)
                    level = self.trigger_level
                    is_rising = (self.trigger_edge == "Ascendente")
                    is_adc = "ADC" in source
                    hysteresis = 20.0 if is_adc else 0.015
                    lookback = 10

                    crosses = ((search_vals[1:] >= level) & (search_vals[:-1] < level)) if is_rising else ((search_vals[1:] <= level) & (search_vals[:-1] > level))
                    for i in (np.flatnonzero(crosses) + 1)[::-1]:
                        prior = search_vals[max(0, i-lookback):i]
                        armed = np.min(prior) <= level-hysteresis if is_rising else np.max(prior) >= level+hysteresis
                        if armed:
                            found_t_idx = (start_search-1)+int(i)
                            break

            now = time.perf_counter()
            if found_t_idx is not None:
                slice_start = found_t_idx - pre_samples
                slice_end = found_t_idx + post_samples

                y_slices = {}
                for col in active_columns:
                    col_deque = self.series.get(col)
                    if col_deque and len(col_deque) >= slice_end:
                        y_slices[col] = self._window_values(col_deque, slice_start, slice_end)
                    else:
                        y_slices[col] = []

                self.frozen_frame = (x_plot, y_slices)
                self.last_trigger_time = now

                is_adc = "ADC" in source
                unit = "" if is_adc else "V"
                lvl_str = f"{int(self.trigger_level)}" if is_adc else f"{number(self.trigger_level, formats.n_2f)}"
                self.trigger_status_label.setText(
                    f"● Disparo ({source} {self.trigger_edge} @ {lvl_str}{unit})"
                )
                self.trigger_status_label.setStyleSheet("""
                    QLabel {
                        background:#171920;
                        border:1px solid #323946;
                        border-radius: 6px;
                        padding: 6px;
                        font-weight:normal;
                        font-size: 11px;
                        color:#aeb8c8;
                    }
                """)
                if self.x_axis_time_mode and self.current_dt_us > 0:
                    self.plot_widget.setLabel("bottom", "Tiempo relativo al Trigger (µs, T=0)", color="#ffffff")
                else:
                    self.plot_widget.setLabel("bottom", "Muestras relativas al Trigger (T=0)", color="#ffffff")

                if self.single_shot_armed:
                    if self.spectral.mode in (1, 2):
                        self.spectral.capture_single(found_t_idx)
                    self.single_shot_armed = False
                    self._set_single_state('captured')
                    self.is_running = False
                    self.run_stop_btn.setChecked(False)
                    self.run_stop_btn.setText("⏹ STOP")
                    self._set_connection_status("Pantalla congelada (SINGLE capturado)")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background:#171920;
                            border:1px solid #323946;
                            border-radius: 6px;
                            padding: 4px 10px;
                            color:#aeb8c8;
                            font-weight:normal;
                            font-size: 11px;
                        }
                    """)

            elif self.frozen_frame is not None and (self.trigger_mode == "Normal" or (now - self.last_trigger_time) < 0.3):
                _, y_slices = self.frozen_frame
                if self.trigger_mode == "Normal":
                    self.trigger_status_label.setText("● Esperando disparo (Normal)…")
                    self.trigger_status_label.setStyleSheet("""
                        QLabel {
                            background:#171920;
                            border:1px solid #323946;
                            border-radius: 6px;
                            padding: 6px;
                            font-weight:normal;
                            font-size: 11px;
                            color:#aeb8c8;
                        }
                    """)
            else:
                # Timeout en Auto mode (fallback continuo)
                end_pos = max(w, total_samples + self.h_pos)
                end_pos = min(end_pos, total_samples)
                start_pos = max(0, end_pos - w)
                y_slices = {
                    col: self._window_values(self.series[col], start_pos, end_pos)
                    for col in active_columns if col in self.series
                }
                self.trigger_status_label.setText("● Auto: buscando disparo · ajustar nivel")
                self.trigger_status_label.setStyleSheet("""
                    QLabel {
                        background:#171920;
                        border:1px solid #323946;
                        border-radius: 6px;
                        padding: 6px;
                        font-weight:normal;
                        font-size: 11px;
                        color:#aeb8c8;
                    }
                """)
                if self.x_axis_time_mode:
                    self.plot_widget.setLabel("bottom", "Tiempo en ventana (µs, Buscando Trigger)", color="#ffffff")
                else:
                    self.plot_widget.setLabel("bottom", "Muestras en ventana (Buscando Trigger)", color="#ffffff")

        # Cached independent window arrays allow changing detail in STOP
        # without advancing the capture or changing its measurements.
        if len(x_plot):
            self._last_display_frame = (x_plot, y_slices, tuple(active_columns))
            self._draw_display_frame(*self._last_display_frame)

        self._update_live_measurements(y_slices, active_columns)

        # ---------------------------------------------------------
        # ACTUALIZACIÓN DE FRECUENCIA DE MUESTREO (Fs y dt)
        # ---------------------------------------------------------
        fs_hz, dt_us, fs_text = self._calculate_sample_rate()
        self.lbl_top_fs.setText(fs_text)
        if dt_us > 0:
            if dt_us < 1000.0:
                tip = f"Frecuencia de Muestreo: {number(fs_hz, formats.n_1f)} Hz\nPeriodo entre muestras: {number(dt_us, formats.n_1f)} µs"
            else:
                tip = f"Frecuencia de Muestreo: {number(fs_hz, formats.n_1f)} Hz\nPeriodo entre muestras: {number(dt_us/1000.0, formats.n_2f)} ms"
            self.lbl_top_fs.setToolTip(tip)
            self.config_rate_combo.setToolTip(tip)

        # Medición de FPS
        self.render_count += 1
        now_calc = time.perf_counter()
        if (now_calc - self.last_fps_calc) >= 1.0:
            self.current_fps = self.render_count / (now_calc - self.last_fps_calc)
            self.render_count = 0
            self.last_fps_calc = now_calc
            mode_str = "RUN" if self.is_running else "STOP"
            self.plot_widget.setTitle(
                f"SCOPE V13 [{mode_str}] | Muestras: {number(self.sample_counter, formats.n_)} | "
                f"Ventana: {number(self.h_scale, formats.n_)} | Fs: {fs_text} | FPS: {number(self.current_fps, formats.n_1f)}"
            )

    def _update_live_measurements(self, y_slices, active_columns):
        # ---------------------------------------------------------
        # ACTUALIZACIÓN DE MEDICIONES EN VIVO (Vmax, Vmin, Vpp, Vrms, Vmed, Freq)
        # ---------------------------------------------------------
        meas_col = self.active_meas_channel
        if meas_col not in active_columns and active_columns:
            meas_col = active_columns[0]

        meas_vals = y_slices.get(meas_col, [])
        measurement_now = time.perf_counter()
        if len(meas_vals) >= 10 and measurement_now - getattr(self, '_last_measurement_update', 0) >= 0.1:
            self._last_measurement_update = measurement_now
            values = np.asarray(meas_vals, dtype=float)
            v_max = float(np.max(values))
            v_min = float(np.min(values))
            v_pp = v_max - v_min
            v_avg = float(np.mean(values))
            v_rms = float(np.sqrt(np.mean(values * values)))

            is_adc = "ADC" in meas_col
            unit = "" if is_adc else "V"
            dec = 0 if is_adc else 2

            self.val_vmax.setText(f"{v_max:.{dec}f}{unit}")
            self.val_vmin.setText(f"{v_min:.{dec}f}{unit}")
            self.val_vpp.setText(f"{v_pp:.{dec}f}{unit}")
            self.val_vrms.setText(f"{v_rms:.{dec}f}{unit}")
            self.val_vavg.setText(f"{v_avg:.{dec}f}{unit}")

            # Estimación de frecuencia física basada en timestamps o cruces
            freq_text = "--"
            if len(meas_vals) >= 50 and v_pp > (0.1 if unit == "V" else 50):
                cross_indices = np.flatnonzero((values[:-1] < v_avg) & (values[1:] >= v_avg)) + 1

                if len(cross_indices) >= 2:
                    delta_samples = (cross_indices[-1] - cross_indices[0]) / (len(cross_indices) - 1)
                    t_slice = y_slices.get("Tiempo (us)", [])
                    if len(t_slice) == len(meas_vals):
                        t_delta_us = (t_slice[cross_indices[-1]] - t_slice[cross_indices[0]]) / (len(cross_indices) - 1)
                        if t_delta_us > 0:
                            freq_hz = 1_000_000.0 / t_delta_us
                            if freq_hz < 1000:
                                freq_text = f"{number(freq_hz, formats.n_1f)} Hz"
                            else:
                                freq_text = f"{number(freq_hz/1000.0, formats.n_2f)} kHz"

                    # Fallback si no hay timestamps
                    if freq_text == "--" and delta_samples > 0 and self.current_fs_hz > 0:
                        freq_est = self.current_fs_hz / delta_samples
                        freq_text = f"{number(freq_est, formats.n_1f)} Hz"

            self.val_freq.setText(freq_text)


    def _update_curve_items(self, active_columns: List[str]):
        for idx, col in enumerate(self.known_columns):
            color = self.channel_colors.get(col, PALETTE[idx % len(PALETTE)])
            if col not in self.line_items:
                style = self.trace_style_combo.currentText()
                pen = pg.mkPen(color, width=2 if style == "Intenso" else 1)
                curve = self.plot_widget.plot([], [], pen=pen, name=col,
                                              antialias=style == "Suave")
                self.line_items[col] = curve
            self.line_items[col].setVisible(col in active_columns)

        self.selection_dirty = False

    def closeEvent(self, event):
        if self._q_preparation is not None and self._q_preparation.isRunning():
            self._set_connection_status('Esperar a que termine la carga del Q antes de cerrar')
            event.ignore()
            return
        self._wav_cancelled = True
        if hasattr(self, "_wav_thread") and self._wav_thread.isRunning():
            self._wav_thread.quit()
            self._wav_thread.wait()
        self.stop_recording()
        self.render_timer.stop()
        self.stop_input()
        event.accept()


def main():
    prepare_platform_plugins()
    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    app.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.GeneralFont))
    window = SerialMonitorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
