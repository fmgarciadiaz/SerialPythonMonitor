"""Monitor V12: adquisición configurable y generador DAC controlado desde el Q."""
import csv
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
from monitor.v12.history import SampleHistory
from monitor.v12.spectrum import SpectralDisplay
from monitor.v12.receiver.unoq_usb import Connection, usb_devices
from monitor.v12.receiver.unoq_switch import Mode
from monitor.v12.receiver.unoq_config_receiver import OutputReceiver
from monitor.v12.receiver.unoq_generator import GeneratorConfig, WAVES, MODES
from monitor.v12.receiver.unoq_acquisition import Configuration, BITS, RATES as RECEIVER_RATES, UART_RATES
# Perfil P992 validado a 14 bits/125 kHz; no ofrecer tasas superiores.
RATES = tuple(rate for rate in RECEIVER_RATES if rate <= 125000)
import queue
from serial.tools import list_ports

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

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



class GeneratorValueSpinBox(QtWidgets.QDoubleSpinBox):
    """Keep fractional precision without padding editable values with zeros."""
    def textFromValue(self, value):
        text = self.locale().toString(float(value), 'f', self.decimals())
        if self.decimals():
            text = text.rstrip('0').rstrip(self.locale().decimalPoint())
        return text


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


class GeneratorComboBox(QtWidgets.QComboBox):
    """Keep the entire closed control clickable, with centered text."""
    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        text, icon = option.currentText, QtGui.QIcon(option.currentIcon)
        option.currentText = ''
        option.currentIcon = QtGui.QIcon()
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, option)
        rect = self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox, option,
                                          QtWidgets.QStyle.SC_ComboBoxEditField, self)
        if not icon.isNull():
            small = self.width() < 150
            icon.paint(painter, QtCore.QRect(rect.left() + 2, rect.center().y() - (5 if small else 9),
                                           16 if small else 36, 10 if small else 18))
            rect.adjust(22 if small else 44, 0, 0, 0)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        painter.drawText(rect, QtCore.Qt.AlignCenter, text)


class InstrumentLogo(QtWidgets.QWidget):
    """Small vector instrument mark, drawn at native display resolution."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 42)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor('#55a99e'), 1.5))
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
        painter.setFont(font)
        painter.setPen(QtGui.QColor('#aeb8c8'))
        painter.drawText(QtCore.QRect(72, 9, 100, 27), QtCore.Qt.AlignVCenter, 'fergd')


def generator_wave_icon(wave):
    pixmap = QtGui.QPixmap(64, 28)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
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


class OutputWorker(QtCore.QObject):
    # Python object transfer avoids converting every sample dictionary to QVariant.
    batch_ready = QtCore.pyqtSignal(object)
    headers_detected = QtCore.pyqtSignal(list)
    status_changed = QtCore.pyqtSignal(str)
    output_confirmed = QtCore.pyqtSignal(int, str)
    acquisition_confirmed = QtCore.pyqtSignal(int, int)
    generator_confirmed = QtCore.pyqtSignal(object)
    switching = QtCore.pyqtSignal(bool)
    error_occurred = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, port, mode, r4_port=None, config=Configuration()):
        super().__init__()
        self.port = port
        self.mode = Mode(mode)
        self.r4_port = r4_port
        self.config = config
        self.running = True
        self.requests = queue.Queue(maxsize=1)
        self.generator_requests = queue.Queue(maxsize=1)

    def set_adc_bits(self, bits):
        pass  # Hardware settings are applied together through configure(), not this display hook.

    def stop(self):
        self.running = False

    def request_output(self, mode, r4_port, config):
        self.requests.put_nowait((Mode(mode), r4_port, config))

    def request_generator(self, config):
        self.generator_requests.put_nowait(config)

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
            with Connection(self.port) as connection:
                connection.socket.settimeout(0.01)
                receiver = OutputReceiver(connection, collect, progress, lambda: self.running)
                receiver.on_configuration = settings_applied
                receiver.on_generator = self.generator_confirmed.emit
                apply(self.mode, self.r4_port, self.config)
                self.acquisition_confirmed.emit(receiver.config.bits, receiver.config.rate)
                published = True
                receiver.generator()
                while self.running:
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
        except Exception as exc:
            if self.running:
                if batch:
                    self.batch_ready.emit(TimedBatch(batch))
                    batch = []
                self.error_occurred.emit(str(exc))
        finally:
            if receiver is not None:
                receiver.close()
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
        self.active_meas_channel = "V_OUT"

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

        # Grabación CSV por lotes para minimizar el coste de E/S.
        self.recording = False
        self.record_start_time = 0.0
        self.record_last_flush_time = 0.0
        self.record_file: Optional[TextIO] = None
        self.record_writer = None
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
        self.refresh_ports()

        # Timer de dibujo desacoplado (~60 FPS)
        self.render_timer = QtCore.QTimer(self)
        self.render_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.render_timer.timeout.connect(self.render_frame)
        self.render_timer.timeout.connect(self.spectral.render)
        self.render_timer.start(RENDER_INTERVAL_MS)

        self.setWindowTitle('Scope V12 · SPI V3/992 · 125 kHz')
        self.baud_input.setText('—')
        self.baud_input.setReadOnly(True)
        self.baud_input.setToolTip('Destino confirmado por el Q. UART hacia R4: 3.000.000 baudios.')
        for label in self.baud_input.parent().findChildren(QtWidgets.QLabel):
            if label.text() == 'BAUD':
                label.setText('ENLACE')
        self.adc_combo.setCurrentText('14 bits (16383)')
        self.adc_combo.setEnabled(False)
        self.adc_combo.setToolTip('Resolución confirmada por el Q.')
        self.applied_configuration = Configuration()

    def _build_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121418;
            }
            QWidget {
                background-color: #121418;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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

        self.stop_serial_btn = QtWidgets.QPushButton("Desconectar")
        self.stop_serial_btn.setEnabled(False)
        self.stop_serial_btn.setStyleSheet("""
            QPushButton:disabled {
                background-color: #1e222b;
                border: 1px solid #2a2e3a;
                color: #555e6d;
            }
            QPushButton:enabled {
                background-color: #b71c1c;
                border: 1px solid #e53935;
                font-weight: bold;
            }
        """)
        self.stop_serial_btn.clicked.connect(self.stop_input)
        top_layout.addWidget(self.stop_serial_btn, 1, 2)

        self.status_label = QtWidgets.QLabel("Listo")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 230, 118, 0.12);
                border: 1px solid rgba(0, 230, 118, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                color: #00e676;
                font-weight: bold;
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
        self.r4_combo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.r4_combo.setToolTip('Puerto USB del R4 con puente V5 y cableado UART al Q.')
        self.r4_combo.setEnabled(False)
        destination_layout.addWidget(self.r4_combo, 1, 1, 1, 2)
        self.confirmed_output_label = QtWidgets.QLabel('Destino confirmado: sin conexión')
        self.confirmed_output_label.setWordWrap(True)
        top_layout.addWidget(self.confirmed_output_label, 3, 0, 1, 4)
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
        for bits in BITS: self.config_bits_combo.addItem('16 bits · oversampling ×16' if bits == 16 else f'{bits} bits', bits)
        self.config_bits_combo.setToolTip('16 bits: oversampling por hardware de 16 conversiones de 14 bits.\nMáximo 50 kHz SPI / 31,25 kHz UART; promedia ruido y señales rápidas.\nNo garantiza 16 bits de precisión analógica.')
        self.config_bits_combo.setCurrentIndex(self.config_bits_combo.findData(14))
        destination_layout.addWidget(self.config_bits_combo, 3, 1, 1, 2)
        destination_layout.addWidget(QtWidgets.QLabel('TASA'), 4, 0)
        self.config_rate_combo = QtWidgets.QComboBox()
        self.config_rate_combo.setToolTip('T: período entre pares de muestras.\nAdq: tiempo de carga del capacitor por canal y subconversión.\nUna ventana más corta exige menor impedancia de fuente para conservar el asentamiento.\nEn 16 bits se realizan 16 subconversiones por canal.')
        for rate in RATES:
            label = f'{rate/1000:g}'.replace('.', ',') + f' kHz · {1000000//rate} µs'
            config = Configuration(14, rate)
            if rate > 31250: label += f' · SPI · ADC {config.sampling_us:g} µs'
            self.config_rate_combo.addItem(label, rate)
        self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(31250))
        destination_layout.addWidget(self.config_rate_combo, 4, 1, 1, 2)
        self.configuration_note = QtWidgets.QLabel('Bits o tasa: nueva captura y cierre del CSV. Sólo salida: captura continua.')
        self.configuration_note.setText(self.configuration_note.text() + '\n16 bits: la ventana ADC se acorta al subir la tasa; precisión dependiente de la impedancia.')
        self.configuration_note.setWordWrap(True)
        destination_layout.addWidget(QtWidgets.QLabel('DETALLE / FPS'), 5, 0)
        detail_row = QtWidgets.QHBoxLayout()
        detail_row.addWidget(QtWidgets.QLabel('Más FPS'))
        self.detail_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
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
        self.config_bits_combo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        adc_card_layout.addWidget(self.config_bits_combo)
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
        self.config_rate_combo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
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
        lbl_fs.setAlignment(QtCore.Qt.AlignCenter)
        lbl_fs.setFixedWidth(58)
        lbl_fs.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent; border: none; padding: 0;")
        fs_card_layout.addWidget(lbl_fs)

        self.lbl_top_fs = QtWidgets.QLabel("-- S/s")
        self.lbl_top_fs.setFixedWidth(90)
        self.lbl_top_fs.setAlignment(QtCore.Qt.AlignCenter)
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
        self.btn_xaxis_toggle = QtWidgets.QPushButton("⧖ EJE: MUESTRAS")
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
                       self.stop_serial_btn, self.btn_xaxis_toggle):
            button.setFixedHeight(34)
            button.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        for card in (port_card, baud_card, adc_card, fs_card, trace_card):
            card.setFixedHeight(34)
        # Match the acquisition panel's two 34 px rows and 8 px gap.
        top_layout.setAlignment(QtCore.Qt.AlignTop)
        top_layout.setRowMinimumHeight(0, 34)
        top_layout.setRowMinimumHeight(1, 34)
        self.status_label.setMinimumWidth(0)
        self.status_label.setWordWrap(False)
        self.status_label.setFixedHeight(34)
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.port_combo.setMinimumWidth(0)
        self.port_combo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        refresh_btn.setFixedSize(28, 28)
        # Temporal display controls belong to the V/t mode panel.
        top_layout.removeWidget(self.btn_xaxis_toggle)
        top_layout.addWidget(fs_card, 1, 3)
        top_layout.removeWidget(trace_card)
        trace_card.hide()
        top_layout.removeWidget(destination_card)
        destination_card.hide()
        destination_layout.removeItem(detail_row)
        self.temporal_settings = QtWidgets.QWidget()
        temporal_form = QtWidgets.QFormLayout(self.temporal_settings)
        temporal_form.setContentsMargins(0,0,0,0)
        temporal_form.setVerticalSpacing(4)
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
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
        self.plot_widget.setTitle("SCOPE V12 - V_IN [A2] / V_OUT [A3]")
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
            pen=pg.mkPen(color="#ff9100", width=1.8, style=QtCore.Qt.DashLine),
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
            pen=pg.mkPen(color="#ff9100", width=1.2, style=QtCore.Qt.DotLine),
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
        instrument_layout.addWidget(InstrumentLogo(instrument_column), alignment=QtCore.Qt.AlignLeft)

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
        lbl_m1 = QtWidgets.QLabel("MEDICIONES EN VIVO")
        lbl_m1.setStyleSheet("font-size: 9px; font-weight: 800; color: #00e5ff; letter-spacing: 0.5px;")
        
        self.meas_channel_combo = QtWidgets.QComboBox()
        self.meas_channel_combo.addItems(["V_OUT", "V_IN", "ADC_OUT", "ADC_IN"])
        self.meas_channel_combo.setCurrentText("V_OUT")
        self.meas_channel_combo.setStyleSheet("""
            QComboBox {
                background-color: #21252f;
                border: 1px solid #3a4150;
                color: #ffd600;
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

        meas_layout.addWidget(card_vmax)
        meas_layout.addWidget(card_vmin)
        meas_layout.addWidget(card_vpp)
        meas_layout.addWidget(card_vrms)
        meas_layout.addWidget(card_vavg)
        meas_layout.addWidget(card_freq)

        left_layout.addWidget(self.measurements_box)

        # 4. Panel de Canales con tarjetas modulares por canal
        self.columns_panel = QtWidgets.QGroupBox("CANALES Y SEÑALES ACTIVAS (V2: V_IN & V_OUT)")
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
        self.single_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #ffa726;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.single_btn.clicked.connect(self.arm_single_shot)
        btn_row.addWidget(self.single_btn)
        acq_layout.addLayout(btn_row)

        record_row = QtWidgets.QHBoxLayout()
        self.record_btn = QtWidgets.QPushButton("● RECORD")
        self.record_btn.setFixedHeight(self.run_stop_btn.height())
        self.record_btn.setToolTip("Iniciar grabación CSV, máximo 30 segundos")
        self.record_btn.setStyleSheet("QPushButton {background:#7f0000;border:1px solid #ff5252;color:white;font-weight:bold;} QPushButton:hover {background:#b71c1c;} QPushButton:disabled {background:#1e222b;color:#555e6d;}")
        self.record_btn.clicked.connect(self.start_recording)
        record_row.addWidget(self.record_btn)
        self.stop_record_btn = QtWidgets.QPushButton("■ STOP REC")
        self.stop_record_btn.setFixedHeight(self.run_stop_btn.height())
        self.stop_record_btn.setEnabled(False)
        self.stop_record_btn.setToolTip("Detener y cerrar el archivo CSV")
        self.stop_record_btn.setStyleSheet("QPushButton:enabled {background:#b71c1c;border:1px solid #ff5252;color:white;font-weight:bold;} QPushButton:disabled {background:#1e222b;color:#555e6d;}")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        record_row.addWidget(self.stop_record_btn)
        acq_layout.addLayout(record_row)
        self.record_status_label = QtWidgets.QLabel("CSV: listo | máximo 30.0 s")
        self.record_status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.record_status_label.setStyleSheet("background:#171920;border:1px solid #323946;padding:4px;color:#8f98a8;font-weight:bold;")
        self.record_status_label.setFixedHeight(40)
        acq_layout.addWidget(self.record_status_label)

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
        horiz_layout.addWidget(lbl_h_s, 0, 0, QtCore.Qt.AlignCenter)

        self.dial_h_scale = QtWidgets.QDial()
        self.dial_h_scale.setRange(VISIBLE_SAMPLES_MIN, VISIBLE_SAMPLES_MAX)
        self.dial_h_scale.setValue(VISIBLE_SAMPLES_DEFAULT)
        self.dial_h_scale.setNotchesVisible(True)
        self.dial_h_scale.valueChanged.connect(self.on_h_scale_changed)
        horiz_layout.addWidget(self.dial_h_scale, 1, 0, QtCore.Qt.AlignCenter)

        self.lbl_h_scale = QtWidgets.QDoubleSpinBox()
        self.lbl_h_scale.setDecimals(0)
        self.lbl_h_scale.setRange(VISIBLE_SAMPLES_MIN, VISIBLE_SAMPLES_MAX)
        self.lbl_h_scale.setValue(VISIBLE_SAMPLES_DEFAULT)
        self.lbl_h_scale.setSuffix(" smp")
        self.lbl_h_scale.setGroupSeparatorShown(True)
        self.lbl_h_scale.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.lbl_h_scale.setKeyboardTracking(False)
        self.lbl_h_scale.valueChanged.connect(self._on_h_scale_input)
        self.lbl_h_scale.setAlignment(QtCore.Qt.AlignCenter)
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
        horiz_layout.addWidget(lbl_h_p, 0, 1, QtCore.Qt.AlignCenter)

        self.dial_h_pos = QtWidgets.QDial()
        self.dial_h_pos.setRange(-VISIBLE_SAMPLES_MAX, 0)
        self.dial_h_pos.setValue(0)
        self.dial_h_pos.setNotchesVisible(True)
        self.dial_h_pos.valueChanged.connect(self.on_h_pos_changed)
        horiz_layout.addWidget(self.dial_h_pos, 1, 1, QtCore.Qt.AlignCenter)

        self.lbl_h_pos = QtWidgets.QLabel("0 smp (Live)")
        self.lbl_h_pos.setAlignment(QtCore.Qt.AlignCenter)
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
        vert_layout.addWidget(lbl_v_s, 0, 0, QtCore.Qt.AlignCenter)

        self.dial_v_scale = QtWidgets.QDial()
        self.dial_v_scale.setRange(50, 1000)
        self.dial_v_scale.setValue(330)
        self.dial_v_scale.setNotchesVisible(True)
        self.dial_v_scale.valueChanged.connect(self.on_v_scale_changed)
        vert_layout.addWidget(self.dial_v_scale, 1, 0, QtCore.Qt.AlignCenter)

        self.lbl_v_scale = QtWidgets.QDoubleSpinBox()
        self.lbl_v_scale.setRange(0.5, 10)
        self.lbl_v_scale.setDecimals(2)
        self.lbl_v_scale.setValue(3.3)
        self.lbl_v_scale.setSuffix(" V")
        self.lbl_v_scale.setGroupSeparatorShown(True)
        self.lbl_v_scale.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.lbl_v_scale.setKeyboardTracking(False)
        self.lbl_v_scale.valueChanged.connect(lambda value: self.dial_v_scale.setValue(round(value * 100)))
        self.lbl_v_scale.setAlignment(QtCore.Qt.AlignCenter)
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
        vert_layout.addWidget(lbl_v_p, 0, 1, QtCore.Qt.AlignCenter)

        self.dial_v_pos = QtWidgets.QDial()
        self.dial_v_pos.setRange(-500, 500)
        self.dial_v_pos.setValue(0)
        self.dial_v_pos.setNotchesVisible(True)
        self.dial_v_pos.valueChanged.connect(self.on_v_pos_changed)
        vert_layout.addWidget(self.dial_v_pos, 1, 1, QtCore.Qt.AlignCenter)

        self.lbl_v_pos = QtWidgets.QLabel("0.00 V")
        self.lbl_v_pos.setAlignment(QtCore.Qt.AlignCenter)
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
        level_header_row.addWidget(self.lbl_trigger_level, 0, QtCore.Qt.AlignRight)
        level_card_layout.addLayout(level_header_row)

        self.dial_trigger_level = QtWidgets.QDial()
        self.dial_trigger_level.setRange(0, 330)
        self.dial_trigger_level.setValue(165)
        self.dial_trigger_level.setNotchesVisible(True)
        self.dial_trigger_level.valueChanged.connect(self.on_trigger_level_dial_changed)
        level_card_layout.addWidget(self.dial_trigger_level, 0, QtCore.Qt.AlignCenter)

        trig_layout.addWidget(level_card)

        # Fila 4: Status label
        self.trigger_status_label = QtWidgets.QLabel("● Modo continuo")
        self.trigger_status_label.setWordWrap(True)
        self.trigger_status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 229, 255, 0.08);
                border: 1px solid rgba(0, 229, 255, 0.25);
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
                color: #00e5ff;
            }
        """)
        trig_layout.addWidget(self.trigger_status_label)

        panel_layout.addWidget(trig_group)
        panel_layout.addStretch()

        main_h_layout.addWidget(panel_widget, 1)

    def _create_meas_card(self, title: str, color: str) -> Tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
        """Crea una tarjeta modular estilizada para una medición de osciloscopio."""
        card = QtWidgets.QFrame()
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
        lbl_t.setAlignment(QtCore.Qt.AlignCenter)

        lbl_v = QtWidgets.QLabel("--")
        lbl_v.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}; background: transparent;")
        lbl_v.setAlignment(QtCore.Qt.AlignCenter)

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return card, lbl_v

    def _on_meas_channel_changed(self, ch: str):
        self.active_meas_channel = ch
        color = self.channel_colors.get(ch, "#ffffff")
        self.meas_channel_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #21252f;
                border: 1px solid {color};
                color: {color};
                font-weight: bold;
                font-size: 11px;
                padding: 2px 6px;
            }}
        """)

    def _channel_checkbox_style(self, name):
        color = self.channel_colors.get(name, PALETTE[self.known_columns.index(name) % len(PALETTE)])
        if not self.selected_columns.get(name, False): color = '#8f98a8'
        check_icon = (ROOT / "monitor/v12/assets/check_neutral.svg").as_posix()
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
            picker.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            menu = QtWidgets.QMenu(picker)
            group = QtWidgets.QActionGroup(menu)
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
        grid.setAlignment(QtCore.Qt.AlignTop)
        self.generator_wave = GeneratorComboBox()
        for i, name in enumerate(WAVES):
            self.generator_wave.addItem(generator_wave_icon(i), name)
        self.generator_wave.setIconSize(QtCore.QSize(36,18))
        self.generator_wave.setFixedHeight(28)
        self.generator_mode = GeneratorComboBox()
        self.generator_mode.addItems(MODES)
        self.generator_frequency = GeneratorFrequencySpinBox()
        self.generator_final_frequency = GeneratorFrequencySpinBox()
        for spin in (self.generator_frequency, self.generator_final_frequency):
            spin.setRange(0.1, 20000); spin.setDecimals(3); spin.setValue(2.5)
        self.generator_frequency.setToolTip('0,1 Hz a 20 kHz. Lectura en Hz y kHz (1000 Hz = 1 kHz).\nEscribir en Hz o incluir kHz; confirmar con Enter o al salir.\nPara observar 20 kHz, elegir Fs de 50 o 62,5 kHz.')
        self.generator_frequency.setAlignment(QtCore.Qt.AlignCenter)
        self.generator_frequency.setStyleSheet('font-size:12px; font-weight:bold; color:#8df3dc;')
        self.generator_amplitude = GeneratorValueSpinBox()
        self.generator_amplitude.setRange(0, 3.3); self.generator_amplitude.setDecimals(3)
        self.generator_amplitude.setSuffix(' Vpp'); self.generator_amplitude.setValue(3.3)
        self.generator_offset = GeneratorValueSpinBox()
        self.generator_offset.setRange(0, 3.3); self.generator_offset.setDecimals(3)
        self.generator_offset.setSuffix(' V'); self.generator_offset.setValue(1.65)
        self.generator_duration = GeneratorValueSpinBox()
        self.generator_duration.setRange(0.001,600); self.generator_duration.setDecimals(3)
        self.generator_duration.setSuffix(' s'); self.generator_duration.setValue(1)
        self._generator_duration_ms = False
        self.generator_frequency_dial = QtWidgets.QDial()
        self.generator_frequency_dial.setRange(0,1000)
        self.generator_frequency_dial.setNotchesVisible(True)
        self.generator_frequency_dial.setTracking(True)
        self.generator_frequency_dial.setFixedSize(88,88)
        palette=self.generator_frequency_dial.palette()
        palette.setColor(QtGui.QPalette.Button,QtGui.QColor('#55a99e'))
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
        self.generator_enabled.setChecked(True)
        check_icon = (ROOT / "monitor/v12/assets/check_neutral.svg").as_posix()
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
                    ('Amplitud pico a pico',self.generator_amplitude),('Offset',self.generator_offset),
                    ('Duración',self.generator_duration)]
        self._generator_labels = {}
        positions = [(0,0,1),(0,1,1),(2,1,1),(5,0,1),(7,0,1),(7,1,1),(5,1,1)]
        for (label,control),(row,col,span) in zip(controls,positions):
            self._generator_labels[control] = QtWidgets.QLabel(label)
            self._generator_labels[control].setAlignment(QtCore.Qt.AlignCenter)
            self._generator_labels[control].setWordWrap(True)
            if isinstance(control, QtWidgets.QDoubleSpinBox):
                control.setAlignment(QtCore.Qt.AlignCenter)
            control.setFixedHeight(28)
            control.setMinimumWidth(0)
            control.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            grid.addWidget(self._generator_labels[control],row,col,1,span)
            grid.addWidget(control,row+1,col,1,span)
            if control is self.generator_frequency:
                grid.addWidget(self.generator_frequency_dial,2,0,3,1,alignment=QtCore.Qt.AlignHCenter)
        grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        self.generator_enabled.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.generator_restart.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        grid.addWidget(self.generator_enabled,11,0,1,2)
        self.generator_restart.setFixedHeight(34)
        self.generator_restart.setText('Disparar')
        grid.addWidget(self.generator_restart,12,0,1,2)
        self.generator_status = QtWidgets.QLabel('Conectar el Q · DAC 12 bits')
        self.generator_status.setWordWrap(True)
        self.generator_status.setAlignment(QtCore.Qt.AlignCenter)
        grid.addWidget(self.generator_status,13,0,1,2)
        self.generator_scroll = QtWidgets.QScrollArea()
        self.generator_scroll.setWidgetResizable(True)
        self.generator_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.generator_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.generator_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
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
            signal.connect(self._schedule_generator)
        self.generator_enabled.toggled.connect(self._schedule_generator)
        self._generator_dirty=False
        self._generator_syncing=False
        self._generator_requested=None
        self._generator_active=GeneratorConfig()
        self._generator_state_known=False
        self._generator_controls=[c for _,c in controls]+[self.generator_enabled,self.generator_restart]
        self._generator_availability()

    def _generator_availability(self):
        pulse=self.generator_wave.currentIndex()==4
        mode=self.generator_mode.currentIndex()
        if pulse != self._generator_duration_ms:
            duration_ms = self.generator_duration.value() * (1 if self._generator_duration_ms else 1000)
            was_blocked = self.generator_duration.blockSignals(True)
            self.generator_duration.setRange(1 if pulse else 0.001, 600000 if pulse else 600)
            self.generator_duration.setDecimals(0 if pulse else 3)
            self.generator_duration.setSuffix(' ms' if pulse else ' s')
            self.generator_duration.setValue(duration_ms if pulse else duration_ms / 1000)
            self.generator_duration.blockSignals(was_blocked)
            self._generator_duration_ms = pulse
        self._generator_labels[self.generator_frequency].setText('Frecuencia inicial' if mode else 'Frecuencia')
        self._generator_labels[self.generator_duration].setText('Ancho del pulso' if pulse else 'Duración del barrido')
        for control, visible in ((self.generator_mode, not pulse),
                                 (self.generator_frequency, not pulse),
                                 (self.generator_final_frequency, not pulse and mode != 0),
                                 (self.generator_duration, pulse or mode != 0)):
            control.setVisible(visible)
            self._generator_labels[control].setVisible(visible)
        self.generator_mode.setEnabled(not pulse)
        self.generator_frequency.setEnabled(not pulse)
        self.generator_final_frequency.setEnabled(not pulse and mode!=0)
        self.generator_duration.setEnabled(pulse or mode!=0)
        self.generator_restart.setEnabled(pulse or mode!=0)
        self.generator_restart.setVisible(pulse or mode!=0)
        self.generator_frequency_dial.setVisible(not pulse)
        self.generator_panel.layout().activate()
        self.generator_scroll.setMinimumHeight(self.generator_panel.sizeHint().height())

    def _schedule_generator(self, *args):
        if self._generator_syncing: return
        if self.generator_wave.currentIndex()==4:
            self.generator_mode.blockSignals(True)
            self.generator_mode.setCurrentIndex(0)
            self.generator_mode.blockSignals(False)
        self._generator_availability()
        self._generator_dirty=True
        self._generator_timer.stop()
        if not self.generator_frequency_dial.isSliderDown():
            self._generator_timer.start()

    def _generator_config(self):
        amp=self.generator_amplitude.value(); offset=self.generator_offset.value()
        low,high=offset-amp/2,offset+amp/2
        if low < -1e-9 or high > 3.3+1e-9:
            if self.generator_enabled.isChecked():
                raise ValueError('Amplitud y offset deben dejar ambos niveles entre 0 y 3,3 V')
            low=self._generator_active.low*3.3/4095
            high=self._generator_active.high*3.3/4095
        return GeneratorConfig(self.generator_wave.currentIndex(),int(self.generator_enabled.isChecked()),
            self.generator_mode.currentIndex(),round(self.generator_frequency.value()*1000),
            round(self.generator_final_frequency.value()*1000),round(max(0,low)*4095/3.3),
            round(min(3.3,high)*4095/3.3),round(self.generator_duration.value()*(1 if self._generator_duration_ms else 1000)))

    def _apply_generator(self):
        self._generator_timer.stop()
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
        from monitor.v12.receiver.unoq_switch import Phase
        if reply.phase == Phase.APPLIED and (self._generator_requested is None or reply.active == self._generator_requested):
            self._generator_active = reply.active
            self._generator_state_known = True
        self.spectral.bode.confirmed(reply)
        if self.spectral.bode.active: return
        if reply.phase==Phase.REJECTED:
            self.generator_status.setText(f'Q rechazó el generador: {reply.reason.name}')
            self._generator_requested=None
            return
        if reply.phase!=Phase.APPLIED: return
        if self._generator_requested is not None and reply.active!=self._generator_requested: return
        self._generator_requested=None
        c=reply.active
        self._generator_active=c
        editing = any(isinstance(control, QtWidgets.QDoubleSpinBox) and control.hasFocus()
                      for control in self._generator_controls)
        editing = editing or self.generator_frequency_dial.isSliderDown()
        if not self._generator_dirty and not editing:
            self._generator_syncing=True
            try:
                self.generator_wave.setCurrentIndex(c.wave)
                self.generator_mode.setCurrentIndex(c.mode)
                self.generator_frequency.setValue(c.frequency/1000)
                self.generator_final_frequency.setValue(c.final_frequency/1000)
                self.generator_amplitude.setValue((c.high-c.low)*3.3/4095)
                self.generator_offset.setValue((c.high+c.low)*3.3/8190)
                self._generator_availability()
                self.generator_duration.setValue(c.duration if self._generator_duration_ms else c.duration/1000)
                self.generator_enabled.setChecked(bool(c.enabled))
            finally:
                self._generator_syncing=False
            self._generator_availability()
        state='Activo' if reply.running else ('Finalizado' if c.enabled else 'Apagado · A0 a 0 V')
        self.generator_status.setText(f'A0 · {state} · {WAVES[c.wave]} · {c.frequency/1000:g} Hz · DAC 12 bits por DMA')
        if self._generator_dirty and not self._generator_timer.isActive(): self._generator_timer.start()

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
            self.btn_xaxis_toggle.setText("⧗ EJE: TIEMPO µs")
        else:
            self.btn_xaxis_toggle.setText("⧖ EJE: MUESTRAS")

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
        self.auto_gap_cut = bool(state == QtCore.Qt.Checked)

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

    def toggle_run_stop(self):
        self._roll_position = None
        self.is_running = self.run_stop_btn.isChecked()
        if self.is_running:
            self.run_stop_btn.setText("▶ RUN")
            self.status_label.setText("Adquisición en vivo")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 230, 118, 0.12);
                    border: 1px solid rgba(0, 230, 118, 0.35);
                    border-radius: 6px;
                    padding: 4px 10px;
                    color: #00e676;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
        else:
            self.run_stop_btn.setText("⏹ STOP")
            self.status_label.setText("Pantalla congelada (STOP)")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 82, 82, 0.15);
                    border: 1px solid rgba(255, 82, 82, 0.4);
                    border-radius: 6px;
                    padding: 4px 10px;
                    color: #ff5252;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)

    def arm_single_shot(self):
        self.single_shot_armed = True
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
                background-color: rgba(255, 214, 0, 0.12);
                border: 1px solid rgba(255, 214, 0, 0.4);
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
                color: #ffd600;
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
            text = f"{self.h_pos * self._horizontal_dt_us() / 1000:.1f} ms"
        else:
            text = f"{self.h_pos} smp"
        self.lbl_h_pos.setText(text + (" (En vivo)" if self.h_pos == 0 else ""))

    def on_v_scale_changed(self, value: int):
        self.v_scale = max(0.2, value / 100.0)
        self.lbl_v_scale.setValue(self.v_scale)
        self._apply_vertical_range()

    def on_v_pos_changed(self, value: int):
        self.v_pos = value / 100.0
        self.lbl_v_pos.setText(f"{self.v_pos:.2f} V")
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
            self.lbl_trigger_level.setText(f"{self.trigger_level:.2f} V")

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
            self.lbl_trigger_level.setText(f"{self.trigger_level:.2f} V")
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
            self.lbl_trigger_level.setText(f"{self.trigger_level:.2f} V")
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
            val_str = f"{int(self.trigger_level)}" if is_adc else f"{self.trigger_level:.2f}"
            self.trigger_status_label.setText(
                f"● Armado: {self.trigger_source} {self.trigger_edge} a {val_str}{unit}"
            )
            self.trigger_status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 145, 0, 0.12);
                    border: 1px solid rgba(255, 145, 0, 0.4);
                    border-radius: 6px;
                    padding: 6px;
                    font-weight: bold;
                    font-size: 11px;
                    color: #ff9100;
                }
            """)
        else:
            self.trigger_status_label.setText("● Modo continuo")
            self.trigger_status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 229, 255, 0.08);
                    border: 1px solid rgba(0, 229, 255, 0.25);
                    border-radius: 6px;
                    padding: 6px;
                    font-weight: bold;
                    font-size: 11px;
                    color: #00e5ff;
                }
            """)

    def _create_log_filename(self):
        folder = ROOT/'capturas/v12'
        folder.mkdir(parents=True, exist_ok=True)
        stem = datetime.now().strftime('log_%Y%m%d_%H%M%S') + f'_{self.applied_configuration.bits}bit_{self.applied_configuration.rate}Hz'
        number = 1
        while (folder/f'{stem}_{number:03d}.csv').exists():
            number += 1
        return folder/f'{stem}_{number:03d}.csv'

    def start_recording(self):
        if self.recording:
            return
        if self.serial_worker is None and not self.demo_mode:
            QtWidgets.QMessageBox.warning(self, "Grabación CSV", "Conectá el Q de control o iniciá Demo antes de grabar.")
            return
        try:
            path = self._create_log_filename()
            self.record_file = path.open("w", encoding="utf-8", newline="", buffering=1024 * 1024)
            self.record_writer = csv.writer(self.record_file, delimiter=",")
            self.record_writer.writerow(["Muestra", "Tiempo_us", "ADC_IN", "V_IN", "ADC_OUT", "V_OUT"])
            self.record_filename = str(path)
            self.record_rows = 0
            self.record_start_time = time.perf_counter()
            self.record_last_flush_time = self.record_start_time
            self.recording = True
            self.record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(True)
            self.record_timer.start()
            self._update_recording_status()
        except Exception as exc:
            self._close_record_file()
            QtWidgets.QMessageBox.critical(self, "Error de grabación", f"No se pudo crear el CSV:\n{exc}")

    def _write_record_batch(self, batch: List[Dict[str, float]]):
        if not self.recording or self.record_writer is None:
            return
        if time.perf_counter() - self.record_start_time >= RECORD_MAX_SECONDS:
            self.stop_recording(auto=True)
            return
        try:
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

    def _update_recording_status(self):
        if not self.recording:
            return
        elapsed = min(time.perf_counter() - self.record_start_time, RECORD_MAX_SECONDS)
        self.record_status_label.setText(f"● REC {elapsed:04.1f}/30.0 s | {self.record_rows:,} filas")
        self.record_status_label.setStyleSheet("background:rgba(255,82,82,0.15);border:1px solid #ff5252;padding:4px;color:#ff5252;font-weight:bold;")
        if elapsed >= RECORD_MAX_SECONDS:
            self.stop_recording(auto=True)

    def _close_record_file(self):
        if self.record_file is not None:
            try:
                self.record_file.flush()
                self.record_file.close()
            except Exception:
                pass
        self.record_file = None
        self.record_writer = None

    def stop_recording(self, checked=False, auto=False, error_message=None):
        was_recording = self.recording
        self.recording = False
        self.record_timer.stop()
        self._close_record_file()
        self.record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        filename = Path(self.record_filename).name if self.record_filename else ""
        if error_message:
            self.record_status_label.setText(f"Error CSV: {error_message}")
            self.record_status_label.setStyleSheet("color:#ff5252;font-weight:bold;")
            if was_recording:
                QtWidgets.QMessageBox.critical(self, "Error de grabación", f"La grabación se detuvo:\n{error_message}")
        elif was_recording:
            reason = "límite de 30 s" if auto else "detenida por usuario"
            self.record_status_label.setText(f"CSV guardado: {filename} | {self.record_rows:,} filas | {reason}")
            self.record_status_label.setStyleSheet("color:#00e676;font-weight:bold;")

    def _update_port_tooltip(self, index):
        self.port_combo.setToolTip(
            self.port_combo.itemData(index, QtCore.Qt.ToolTipRole) or "Seleccionar puerto serial")

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
                self.status_label.setText('Elegir el Q de control y el destino de muestras' if devices
                                          else 'No se encontró un UNO Q conectado por USB')
        except Exception as exc:
            self.status_label.setText(str(exc))
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
        self.adc_combo.setCurrentText(f'{bits} bits ({(1 << bits)-1})')
        self.adc_summary_label.setText(f'{bits} bits')
        self._refresh_applied_summary()

    def _refresh_applied_summary(self):
        config = self.applied_configuration
        mode = getattr(self, 'confirmed_mode', None)
        port = getattr(self, 'confirmed_r4', '')
        name = 'SPI · UNO Q' if mode == int(Mode.SPI) else f'UART · R4 {port}'
        self.confirmed_output_label.setText(f'{name} · {config.bits} bits' + (' OS ×16' if config.bits == 16 else '') + ' · ' + f'{config.rate/1000:g}'.replace('.', ',') + ' kHz')
        self.status_label.setText('Adquisición aplicada · control Q conectado')

    def _destination_changed(self):
        if hasattr(self, 'config_rate_combo'):
            uart = self.destination_combo.currentData() == int(Mode.UART)
            for i in range(self.config_rate_combo.count()):
                rate = self.config_rate_combo.itemData(i)
                allowed = (not uart or rate in UART_RATES) and (self.config_bits_combo.currentData() != 16 or rate <= 62500)
                self.config_rate_combo.model().item(i).setEnabled(allowed)
                bits = self.config_bits_combo.currentData()
                label = f'{rate/1000:g}'.replace('.', ',') + f' kHz · {1000000//rate} µs'
                if bits != 16 or rate <= 62500:
                    profile = Configuration(bits, rate)
                    acquisition = f'{profile.sampling_us:g}'.replace('.', ',')
                    tooltip = (f'Período entre pares: {profile.period} µs.\n'
                               f'Adquisición por canal y subconversión: {acquisition} µs '
                               f'({profile.sampling_cycles} ciclos ADC).\n'
                               + ('16 subconversiones por canal.\n' if bits == 16 else '')
                               + 'Menor tiempo de adquisición exige menor impedancia de fuente.\n'
                               + 'El límite en ohmios depende del circuito y la precisión buscada.')
                else:
                    tooltip = 'Esta tasa no admite el oversampling ×16 de ambos canales.'
                self.config_rate_combo.setItemText(i, label)
                self.config_rate_combo.setItemData(i, tooltip, QtCore.Qt.ToolTipRole)
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
            self.confirmed_output_label.setText('Destino: cambio en curso; esperando al Q')
            self.baud_input.setText('…')
        self.config_bits_combo.setEnabled(not pending)
        self.config_rate_combo.setEnabled(not pending)
        self.destination_combo.setEnabled(not pending)
        self._destination_changed()

    def _output_confirmed(self, mode, r4_port):
        self.confirmed_mode, self.confirmed_r4 = mode, r4_port
        self.control_summary_label.setText(str(self.port_combo.currentData()))
        self.baud_input.setText('SPI' if mode == int(Mode.SPI) else 'UART 3M')
        self._refresh_applied_summary()

    def _schedule_configuration(self):
        if self.serial_worker is not None and not self.output_pending:
            self._auto_apply_timer.start()

    def _auto_apply_configuration(self):
        if self.serial_worker is None or self.output_pending: return
        if self.destination_combo.currentData() == int(Mode.UART) and not self.r4_combo.currentData():
            self.status_label.setText('Seleccionar el R4 para aplicar la salida UART')
            return
        self.apply_output()

    def apply_output(self):
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

    def connect_serial(self):
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
            self.config_bits_combo.currentData(), self.config_rate_combo.currentData()))
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        worker = self.serial_worker
        self.serial_worker.batch_ready.connect(lambda batch: self._from_worker(worker, self.handle_batch, batch))
        self.serial_worker.headers_detected.connect(lambda headers: self._from_worker(worker, self.on_headers_detected, headers))
        self.serial_worker.status_changed.connect(lambda text: self._from_worker(worker, self.status_label.setText, text))
        self.serial_worker.output_confirmed.connect(lambda mode, r4: self._from_worker(worker, self._output_confirmed, mode, r4))
        self.serial_worker.acquisition_confirmed.connect(lambda bits, rate: self._from_worker(worker, self._acquisition_confirmed, bits, rate))
        self.serial_worker.generator_confirmed.connect(lambda reply: self._from_worker(worker, self._generator_confirmed, reply))
        self.serial_worker.switching.connect(lambda pending: self._from_worker(worker, self._set_output_pending, pending))
        self.serial_worker.error_occurred.connect(lambda text: self._from_worker(worker, self._on_worker_error, text))
        self.serial_worker.finished.connect(self.serial_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        # Keep the QThread alive until stop_input() finishes inspecting/joining it.
        self.port_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self._set_output_pending(True)
        self.serial_thread.start()
        self.connect_button.setEnabled(False)
        self.demo_button.setEnabled(False)
        self.stop_serial_btn.setEnabled(True)

    def _from_worker(self, worker, callback, *args):
        # Qt may deliver queued signals after stop_input() joined the old thread.
        if worker is self.serial_worker:
            callback(*args)

    def _on_worker_error(self, message: str):
        self.stop_input()
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 82, 82, 0.15);
                border: 1px solid rgba(255, 82, 82, 0.4);
                border-radius: 6px;
                padding: 4px 10px;
                color: #ff5252;
                font-weight: bold;
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
        self.status_label.setText("Demo activo · V_IN cuadrada / V_OUT filtro RC")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 229, 255, 0.12);
                border: 1px solid rgba(0, 229, 255, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                color: #00e5ff;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        if self.demo_timer is None:
            self.demo_timer = QtCore.QTimer(self)
            self.demo_timer.timeout.connect(self._generate_demo_samples)

        self.demo_timer.start(20)
        self.connect_button.setEnabled(False)
        self.demo_button.setEnabled(False)
        self.stop_serial_btn.setEnabled(True)

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
        self.port_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self._set_output_pending(False)
        self.confirmed_output_label.setText('Destino confirmado: sin conexión')
        self.baud_input.setText('—')
        self.control_summary_label.setText('Sin conexión')
        self.adc_summary_label.setText('—')
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.stop_serial_btn.setEnabled(False)
        self.status_label.setText("Detenido")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                padding: 4px 10px;
                color: #ffffff;
                font-weight: bold;
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
                text = f"{fs_hz / 1_000_000.0:.2f} MS/s"
            elif fs_hz >= 1000.0:
                text = f"{fs_hz / 1000.0:.2f} kS/s"
            else:
                text = f"{fs_hz:.1f} S/s"
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
                end_search = n - post_samples
                search_window = min(n - post_samples - pre_samples, max(3000, w * 4))
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
                lvl_str = f"{int(self.trigger_level)}" if is_adc else f"{self.trigger_level:.2f}"
                self.trigger_status_label.setText(
                    f"● Disparo ({source} {self.trigger_edge} @ {lvl_str}{unit})"
                )
                self.trigger_status_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(0, 230, 118, 0.15);
                        border: 1px solid #00e676;
                        border-radius: 6px;
                        padding: 6px;
                        font-weight: bold;
                        font-size: 11px;
                        color: #00e676;
                    }
                """)
                if self.x_axis_time_mode and self.current_dt_us > 0:
                    self.plot_widget.setLabel("bottom", "Tiempo relativo al Trigger (µs, T=0)", color="#ffffff")
                else:
                    self.plot_widget.setLabel("bottom", "Muestras relativas al Trigger (T=0)", color="#ffffff")

                if self.single_shot_armed:
                    self.single_shot_armed = False
                    self.is_running = False
                    self.run_stop_btn.setChecked(False)
                    self.run_stop_btn.setText("⏹ STOP")
                    self.status_label.setText("Pantalla congelada (SINGLE capturado)")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 214, 0, 0.15);
                            border: 1px solid #ffd600;
                            border-radius: 6px;
                            padding: 4px 10px;
                            color: #ffd600;
                            font-weight: bold;
                            font-size: 11px;
                        }
                    """)

            elif self.frozen_frame is not None and (self.trigger_mode == "Normal" or (now - self.last_trigger_time) < 0.3):
                _, y_slices = self.frozen_frame
                if self.trigger_mode == "Normal":
                    self.trigger_status_label.setText("● Esperando disparo (Normal)…")
                    self.trigger_status_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 145, 0, 0.12);
                            border: 1px solid rgba(255, 145, 0, 0.4);
                            border-radius: 6px;
                            padding: 6px;
                            font-weight: bold;
                            font-size: 11px;
                            color: #ff9100;
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
                        background-color: rgba(255, 214, 0, 0.12);
                        border: 1px solid rgba(255, 214, 0, 0.35);
                        border-radius: 6px;
                        padding: 6px;
                        font-weight: bold;
                        font-size: 11px;
                        color: #ffd600;
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
                tip = f"Frecuencia de Muestreo: {fs_hz:.1f} Hz\nPeriodo entre muestras: {dt_us:.1f} µs"
            else:
                tip = f"Frecuencia de Muestreo: {fs_hz:.1f} Hz\nPeriodo entre muestras: {dt_us/1000.0:.2f} ms"
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
                f"SCOPE V12 [{mode_str}] | Muestras: {self.sample_counter} | "
                f"Ventana: {self.h_scale} | Fs: {fs_text} | FPS: {self.current_fps:.1f}"
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
                                freq_text = f"{freq_hz:.1f} Hz"
                            else:
                                freq_text = f"{freq_hz/1000.0:.2f} kHz"

                    # Fallback si no hay timestamps
                    if freq_text == "--" and delta_samples > 0 and self.current_fs_hz > 0:
                        freq_est = self.current_fs_hz / delta_samples
                        freq_text = f"~{freq_est:.1f} Hz"

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
        self.stop_recording()
        self.render_timer.stop()
        self.stop_input()
        event.accept()


def main():
    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    window = SerialMonitorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
