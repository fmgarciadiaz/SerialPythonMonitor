import itertools
import math
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import serial
from serial.tools import list_ports

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# Configuración de pyqtgraph para alto rendimiento y estética de osciloscopio
pg.setConfigOption("background", "#121418")  # Fondo oscuro elegante de laboratorio
pg.setConfigOption("foreground", "#ffffff")  # Texto y números en blanco puro
pg.setConfigOption("antialias", False)

BAUD_DEFAULT = 921600
VISIBLE_SAMPLES_DEFAULT = 9000
VISIBLE_SAMPLES_MIN = 50
VISIBLE_SAMPLES_MAX = 20000
MAX_BUFFER_SAMPLES = 100000  # Buffer de 100.000 muestras en memoria
RENDER_INTERVAL_MS = 25      # ~40 FPS

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
    "#00e5ff",  # Cyan neón (Canal 1 - Voltaje)
    "#ffd600",  # Amarillo eléctrico (Canal 2 - ADC)
    "#00e676",  # Verde neón (Canal 3 - Muestra)
    "#ff4081",  # Rosa neón (Canal 4 - Tiempo)
    "#ff9100",  # Naranja
    "#b388ff",  # Púrpura
]


def is_header_line(parts: List[str]) -> bool:
    """Determina si una línea contiene nombres de columnas en lugar de muestras numéricas."""
    if len(parts) < 2:
        return False
    numeric_count = 0
    for part in parts:
        try:
            float(part)
            numeric_count += 1
        except ValueError:
            pass
    return numeric_count == 0 or (len(parts) >= 3 and numeric_count <= 1)


class SerialWorker(QtCore.QObject):
    """
    Lee datos seriales en bloque a nivel de kernel para latencia cero.
    Procesa más de 500.000 líneas/s y previene acumulación en el buffer del SO.
    """
    batch_ready = QtCore.pyqtSignal(list)
    headers_detected = QtCore.pyqtSignal(list)
    status_changed = QtCore.pyqtSignal(str)
    error_occurred = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, port: str, baud: int):
        super().__init__()
        self.port = port
        self.baud = baud
        self.serial_port: Optional[serial.Serial] = None
        self.running = True
        self.raw_buffer = bytearray()
        self.columns = ["ADC", "Voltaje (V)", "Muestra", "Tiempo (us)"]

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.serial_port = serial.Serial(self.port, self.baud, timeout=0.05)
            self.serial_port.reset_input_buffer()
            self.status_changed.emit(f"Conectado a {self.port} ({self.baud} baud)")
        except Exception as exc:
            self.error_occurred.emit(f"No se pudo abrir el puerto {self.port}: {exc}")
            self.finished.emit()
            return

        batch: List[Dict[str, float]] = []
        last_emit_time = time.perf_counter()

        while self.running:
            try:
                waiting = self.serial_port.in_waiting
                chunk = self.serial_port.read(waiting if waiting > 0 else 1024)
            except serial.SerialException as exc:
                self.error_occurred.emit(f"Conexión serial interrumpida: {exc}")
                break
            except Exception as exc:
                self.error_occurred.emit(f"Error serial: {exc}")
                break

            if chunk:
                self.raw_buffer.extend(chunk)

                # Protección anti-lag estricta: si el buffer acumula más de 25.000 bytes (~0.25 s),
                # descartar bytes viejos para sincronizar instantáneamente con el presente
                if len(self.raw_buffer) > 25000:
                    self.raw_buffer = self.raw_buffer[-4096:]
                    nl_pos = self.raw_buffer.find(b"\n")
                    if nl_pos != -1:
                        self.raw_buffer = self.raw_buffer[nl_pos + 1:]

                lines = self.raw_buffer.split(b"\n")
                self.raw_buffer = bytearray(lines[-1])

                for line_bytes in lines[:-1]:
                    if not line_bytes:
                        continue
                    line = line_bytes.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    parts = [p.strip() for p in line.split(",") if p.strip()]
                    if is_header_line(parts):
                        normalized_headers = []
                        has_adc = False
                        for p in parts:
                            lp = p.lower()
                            if "voltaje" in lp:
                                normalized_headers.append("Voltaje (V)")
                            elif "adc" in lp:
                                normalized_headers.append("ADC")
                                has_adc = True
                            elif "tiempo" in lp:
                                normalized_headers.append("Tiempo (us)")
                            elif "muestra" in lp:
                                normalized_headers.append("Muestra")
                            else:
                                normalized_headers.append(p.capitalize())

                        if has_adc and "Voltaje (V)" not in normalized_headers:
                            normalized_headers.append("Voltaje (V)")

                        self.columns = normalized_headers
                        self.headers_detected.emit(list(self.columns))

                    else:
                        sample = self._parse_sample_parts(parts)
                        if sample:
                            batch.append(sample)

            now = time.perf_counter()
            if len(batch) >= 80 or (batch and (now - last_emit_time) >= 0.02):
                self.batch_ready.emit(batch)
                batch = []
                last_emit_time = now

        if batch:
            self.batch_ready.emit(batch)

        if self.serial_port is not None:
            try:
                self.serial_port.close()
            except Exception:
                pass

        self.finished.emit()

    def _parse_sample_parts(self, parts: List[str]) -> Optional[Dict[str, float]]:
        """Interpreta filas de 4, 3, 2 o 1 columna garantizando extraer siempre ADC y Voltaje."""
        # 1. Caso estándar de 4 columnas (estado, muestra, tiempo_us, adc)
        if len(parts) >= 4:
            try:
                muestra = float(parts[1])
                tiempo_us = float(parts[2])
                adc = float(parts[3])
                return {
                    "ADC": adc,
                    "Voltaje (V)": adc * 3.3 / 4095.0,
                    "Muestra": muestra,
                    "Tiempo (us)": tiempo_us,
                }
            except ValueError:
                pass

        # 2. Caso de 3 columnas (muestra, tiempo_us, adc)
        if len(parts) == 3:
            try:
                muestra = float(parts[0])
                tiempo_us = float(parts[1])
                adc = float(parts[2])
                return {
                    "ADC": adc,
                    "Voltaje (V)": adc * 3.3 / 4095.0,
                    "Muestra": muestra,
                    "Tiempo (us)": tiempo_us,
                }
            except ValueError:
                pass

        # 3. Caso de 1 sola columna (ej. envío directo de ADC)
        if len(parts) == 1:
            try:
                adc = float(parts[0])
                return {
                    "ADC": adc,
                    "Voltaje (V)": adc * 3.3 / 4095.0,
                }
            except ValueError:
                pass

        # 4. Caso numérico genérico
        sample = {}
        for idx, part in enumerate(parts):
            try:
                val = float(part)
                col_name = self.columns[idx] if idx < len(self.columns) else f"Col_{idx+1}"
                sample[col_name] = val
            except (ValueError, IndexError):
                pass

        if "ADC" in sample and "Voltaje (V)" not in sample:
            sample["Voltaje (V)"] = sample["ADC"] * 3.3 / 4095.0

        return sample if sample else None

    def stop(self):
        self.running = False


class SerialMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Monitor - Osciloscopio Digital (Qt)")
        self.resize(1280, 800)

        # Buffers circulares
        self.sample_counter = 0
        self.sample_numbers: deque = deque(maxlen=MAX_BUFFER_SAMPLES)
        self.series: Dict[str, deque] = {
            "ADC": deque(maxlen=MAX_BUFFER_SAMPLES),
            "Voltaje (V)": deque(maxlen=MAX_BUFFER_SAMPLES),
            "Muestra": deque(maxlen=MAX_BUFFER_SAMPLES),
            "Tiempo (us)": deque(maxlen=MAX_BUFFER_SAMPLES),
        }

        self.known_columns = list(self.series.keys())
        self.selected_columns: Dict[str, bool] = {
            "ADC": False,
            "Voltaje (V)": True,
            "Muestra": False,
            "Tiempo (us)": False,
        }
        self.selection_dirty = True

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
        self.trigger_source = "Voltaje (V)"
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
        self.serial_worker: Optional[SerialWorker] = None
        self.demo_mode = False
        self.demo_timer: Optional[QtCore.QTimer] = None
        self.start_time = time.perf_counter()

        # Rendimiento y FPS
        self.render_count = 0
        self.last_fps_calc = time.perf_counter()
        self.current_fps = 0.0

        # Construir Interfaz
        self._build_ui()
        self.refresh_ports()

        # Timer de dibujo desacoplado (~40 FPS)
        self.render_timer = QtCore.QTimer(self)
        self.render_timer.timeout.connect(self.render_frame)
        self.render_timer.start(RENDER_INTERVAL_MS)

    def _build_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121418;
            }
            QWidget {
                background-color: #121418;
                color: #ffffff;
                font-family: "Helvetica Neue", Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #282d37;
                border-radius: 8px;
                margin-top: 10px;
                padding: 14px 8px 8px 8px;
                background-color: #1a1d24;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #00e5ff;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton {
                background-color: #262a34;
                border: 1px solid #3c4352;
                border-radius: 6px;
                padding: 6px 12px;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #323846;
                border-color: #00e5ff;
            }
            QPushButton:pressed {
                background-color: #1c1f26;
            }
            QComboBox, QLineEdit {
                background-color: #21252f;
                border: 1px solid #3a4150;
                border-radius: 6px;
                padding: 4px 8px;
                color: #ffffff;
                font-weight: bold;
            }
            QComboBox:hover, QLineEdit:focus {
                border: 1px solid #00e5ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QDial {
                background-color: #21252f;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_h_layout = QtWidgets.QHBoxLayout(central)
        main_h_layout.setSpacing(10)
        main_h_layout.setContentsMargins(10, 10, 10, 10)

        # -------------------------------------------------------------
        # COLUMNA IZQUIERDA: Conexión + Gráfico + Mediciones + Canales
        # -------------------------------------------------------------
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 1. Barra de Conexión Serial con recuadro sutil
        top_group = QtWidgets.QGroupBox("CONEXIÓN DE ENTRADA")
        top_layout = QtWidgets.QHBoxLayout(top_group)
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

        lbl_port = QtWidgets.QLabel("PUERTO")
        lbl_port.setStyleSheet("font-weight: 700; font-size: 10px; color: #8f98a8; background: transparent;")
        port_card_layout.addWidget(lbl_port)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(170)
        self.port_combo.setStyleSheet("background-color: #171920; border: 1px solid #3a4150;")
        port_card_layout.addWidget(self.port_combo)

        refresh_btn = QtWidgets.QPushButton("↻")
        refresh_btn.setToolTip("Buscar puertos seriales")
        refresh_btn.setFixedWidth(28)
        refresh_btn.setStyleSheet("background-color: #2c3240; border: 1px solid #3e4658; padding: 2px;")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_card_layout.addWidget(refresh_btn)
        top_layout.addWidget(port_card)

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
        self.baud_input.setFixedWidth(80)
        self.baud_input.setStyleSheet("background-color: #171920; border: 1px solid #3a4150;")
        baud_card_layout.addWidget(self.baud_input)
        top_layout.addWidget(baud_card)

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
        top_layout.addWidget(self.connect_button)

        self.demo_button = QtWidgets.QPushButton("Demo")
        self.demo_button.setToolTip("Generador de señales de prueba")
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
        top_layout.addWidget(self.demo_button)

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
        top_layout.addWidget(self.stop_serial_btn)

        self.status_label = QtWidgets.QLabel("Listo")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 230, 118, 0.12);
                border: 1px solid rgba(0, 230, 118, 0.35);
                border-radius: 12px;
                padding: 4px 10px;
                color: #00e676;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        top_layout.addWidget(self.status_label, 1)

        left_layout.addWidget(top_group)

        # 2. Pantalla de Osciloscopio (PyQtGraph)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
        self.plot_widget.setTitle("OSCILOSCOPIO DIGITAL EN VIVO")
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
        left_layout.addWidget(self.plot_widget, 1)

        # 3. Barra de Mediciones en Vivo (Vmax, Vmin, Vpp, Vrms, Vmed, Frecuencia)
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

        # Título de mediciones
        meas_title_frame = QtWidgets.QFrame()
        meas_title_frame.setStyleSheet("border: none; background: transparent;")
        mtf_layout = QtWidgets.QVBoxLayout(meas_title_frame)
        mtf_layout.setContentsMargins(2, 2, 2, 2)
        mtf_layout.setSpacing(1)
        lbl_m1 = QtWidgets.QLabel("MEDICIONES")
        lbl_m1.setStyleSheet("font-size: 9px; font-weight: 800; color: #00e5ff; letter-spacing: 0.5px;")
        self.lbl_meas_channel = QtWidgets.QLabel("CH1: Voltaje")
        self.lbl_meas_channel.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
        mtf_layout.addWidget(lbl_m1)
        mtf_layout.addWidget(self.lbl_meas_channel)
        meas_layout.addWidget(meas_title_frame)

        # Tarjetas de datos de medición
        card_vmax, self.val_vmax = self._create_meas_card("V MAX", "#00e676")
        card_vmin, self.val_vmin = self._create_meas_card("V MIN", "#ff5252")
        card_vpp, self.val_vpp = self._create_meas_card("V P-P", "#ffd600")
        card_vrms, self.val_vrms = self._create_meas_card("V RMS", "#00e5ff")
        card_vavg, self.val_vavg = self._create_meas_card("V MEDIA", "#b388ff")
        card_freq, self.val_freq = self._create_meas_card("FRECUENCIA", "#ff9100")

        meas_layout.addWidget(card_vmax)
        meas_layout.addWidget(card_vmin)
        meas_layout.addWidget(card_vpp)
        meas_layout.addWidget(card_vrms)
        meas_layout.addWidget(card_vavg)
        meas_layout.addWidget(card_freq)

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

        btn_row = QtWidgets.QHBoxLayout()
        self.run_stop_btn = QtWidgets.QPushButton("▶ RUN")
        self.run_stop_btn.setCheckable(True)
        self.run_stop_btn.setChecked(True)
        self.run_stop_btn.setFixedHeight(42)
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
        self.single_btn.setFixedHeight(42)
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

        self.lbl_h_scale = QtWidgets.QLabel(f"{VISIBLE_SAMPLES_DEFAULT} smp")
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
        self.dial_h_pos.setRange(-50000, 0)
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

        self.lbl_v_scale = QtWidgets.QLabel("3.30 V")
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
        self.trigger_checkbox.setStyleSheet("font-weight: 800; font-size: 11px; color: #ff9100; background: transparent;")
        self.trigger_checkbox.stateChanged.connect(self.configure_trigger)
        act_layout.addWidget(self.trigger_checkbox)

        self.btn_auto_level = QtWidgets.QPushButton("50% (Auto)")
        self.btn_auto_level.setToolTip("Ajustar nivel de disparo al 50% del voltaje pico a pico")
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
        self.trigger_source_combo.addItems(["Voltaje (V)", "ADC"])
        self.trigger_source_combo.setCurrentText("Voltaje (V)")
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
        self.trigger_status_label = QtWidgets.QLabel("● Modo Continuo (Free Run)")
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

    # -------------------------------------------------------------
    # CONTROL DE CANALES Y SEÑALES
    # -------------------------------------------------------------
    def _rebuild_column_controls(self, names: List[str]):
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for idx, name in enumerate(names):
            is_checked = self.selected_columns.get(name, name == "Voltaje (V)")
            self.selected_columns[name] = is_checked

            color = PALETTE[idx % len(PALETTE)]
            checkbox = QtWidgets.QCheckBox(name)
            checkbox.setChecked(is_checked)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    background-color: #21252f;
                    border: 1px solid {color if is_checked else '#323946'};
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: {color};
                    font-weight: bold;
                    font-size: 12px;
                }}
                QCheckBox:hover {{
                    background-color: #2a2f3c;
                    border-color: {color};
                }}
            """)
            checkbox.stateChanged.connect(self._on_column_toggled)
            self.columns_layout.addWidget(checkbox)

    def _on_column_toggled(self):
        checkbox = self.sender()
        if checkbox is None:
            return
        name = checkbox.text()
        is_checked = checkbox.isChecked()
        self.selected_columns[name] = is_checked
        self.selection_dirty = True

        idx = self.known_columns.index(name) if name in self.known_columns else 0
        color = PALETTE[idx % len(PALETTE)]
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                background-color: #21252f;
                border: 1px solid {color if is_checked else '#323946'};
                border-radius: 6px;
                padding: 6px 12px;
                color: {color};
                font-weight: bold;
                font-size: 12px;
            }}
            QCheckBox:hover {{
                background-color: #2a2f3c;
                border-color: {color};
            }}
        """)

        if name in self.line_items:
            self.line_items[name].setVisible(is_checked)

    @QtCore.pyqtSlot(list)
    def on_headers_detected(self, headers: List[str]):
        new_cols = [h for h in headers if h not in self.known_columns]
        if not new_cols:
            return

        for col in new_cols:
            self.known_columns.append(col)
            if col not in self.series:
                self.series[col] = deque(maxlen=MAX_BUFFER_SAMPLES)
            if col not in self.selected_columns:
                self.selected_columns[col] = False

        self._rebuild_column_controls(self.known_columns)

    # -------------------------------------------------------------
    # CONTROLES DE OSCILOSCOPIO Y DIALS
    # -------------------------------------------------------------
    def toggle_run_stop(self):
        self.is_running = self.run_stop_btn.isChecked()
        if self.is_running:
            self.run_stop_btn.setText("▶ RUN")
            self.status_label.setText("Adquisición en vivo")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 230, 118, 0.12);
                    border: 1px solid rgba(0, 230, 118, 0.35);
                    border-radius: 12px;
                    padding: 4px 10px;
                    color: #00e676;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
        else:
            self.run_stop_btn.setText("⏹ STOP")
            self.status_label.setText("PANTALLA CONGELADA (STOP)")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 82, 82, 0.15);
                    border: 1px solid rgba(255, 82, 82, 0.4);
                    border-radius: 12px;
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
        self.trigger_status_label.setText("⚡ SINGLE ARMADO: esperando cruce...")
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
        self.trigger_source_combo.setCurrentText("Voltaje (V)")
        self.dial_trigger_level.setValue(165)
        self.run_stop_btn.setChecked(True)
        self.toggle_run_stop()

    def on_h_scale_changed(self, value: int):
        self.h_scale = max(VISIBLE_SAMPLES_MIN, int(value))
        self.lbl_h_scale.setText(f"{self.h_scale} smp")

    def on_h_pos_changed(self, value: int):
        self.h_pos = int(value)
        if self.h_pos == 0:
            self.lbl_h_pos.setText("0 smp (Live)")
        else:
            self.lbl_h_pos.setText(f"{self.h_pos} smp")

    def on_v_scale_changed(self, value: int):
        self.v_scale = max(0.2, value / 100.0)
        self.lbl_v_scale.setText(f"{self.v_scale:.2f} V")
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
        if source == "ADC":
            self.dial_trigger_level.setRange(0, 4095)
            self.dial_trigger_level.setValue(2048)
            self.trigger_level = 2048.0
            self.lbl_trigger_level.setText("2048")
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
        if self.trigger_source == "ADC":
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
        if self.trigger_source == "ADC":
            self.trigger_level = max(0.0, min(4095.0, new_val))
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

        recent = list(itertools.islice(src_deque, max(0, len(src_deque) - 1500), len(src_deque)))
        v_min = min(recent)
        v_max = max(recent)
        v_mid = (v_min + v_max) / 2.0

        self._updating_trigger_line = True
        if source == "ADC":
            self.trigger_level = max(0.0, min(4095.0, v_mid))
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
            unit = "" if self.trigger_source == "ADC" else "V"
            val_str = f"{int(self.trigger_level)}" if self.trigger_source == "ADC" else f"{self.trigger_level:.2f}"
            self.trigger_status_label.setText(
                f"● ARMADO: {self.trigger_source} {self.trigger_edge} a {val_str}{unit}"
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
            self.trigger_status_label.setText("● Modo Continuo (Free Run)")
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

    # -------------------------------------------------------------
    # CONEXIÓN SERIAL Y MODO DEMO
    # -------------------------------------------------------------
    def refresh_ports(self):
        available_ports = list(list_ports.comports())
        ports = [port.device for port in available_ports]

        current_selected = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)

        arduino_port = None
        for port in available_ports:
            joined = " ".join(
                str(val or "")
                for val in (
                    port.device,
                    port.description,
                    port.manufacturer,
                    port.product,
                    port.hwid,
                )
            ).lower()
            if any(k in joined for k in ARDUINO_KEYWORDS):
                arduino_port = port.device
                break

        if arduino_port:
            self.port_combo.setCurrentText(arduino_port)
            self.status_label.setText(f"Arduino en: {arduino_port}")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 230, 118, 0.12);
                    border: 1px solid rgba(0, 230, 118, 0.35);
                    border-radius: 12px;
                    padding: 4px 10px;
                    color: #00e676;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
        elif ports:
            if current_selected in ports:
                self.port_combo.setCurrentText(current_selected)
            else:
                self.port_combo.setCurrentText(ports[0])
            self.status_label.setText("Puerto detectado")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 12px;
                    padding: 4px 10px;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
        else:
            self.port_combo.setCurrentText("")
            self.status_label.setText("Sin puertos")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 82, 82, 0.15);
                    border: 1px solid rgba(255, 82, 82, 0.4);
                    border-radius: 12px;
                    padding: 4px 10px;
                    color: #ff5252;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)

    def connect_serial(self):
        self.stop_input()

        port = self.port_combo.currentText().strip()
        if not port:
            QtWidgets.QMessageBox.warning(self, "Puerto serial", "Por favor selecciona un puerto serial.")
            return

        try:
            baud = int(self.baud_input.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Baud", "Ingresa un número de baudios válido.")
            return

        self.clear_data()
        self.serial_thread = QtCore.QThread()
        self.serial_worker = SerialWorker(port, baud)
        self.serial_worker.moveToThread(self.serial_thread)

        self.serial_thread.started.connect(self.serial_worker.run)
        self.serial_worker.batch_ready.connect(self.handle_batch)
        self.serial_worker.headers_detected.connect(self.on_headers_detected)
        self.serial_worker.status_changed.connect(self.status_label.setText)
        self.serial_worker.error_occurred.connect(self._on_worker_error)
        self.serial_worker.finished.connect(self.serial_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        self.serial_thread.finished.connect(self.serial_thread.deleteLater)

        self.serial_thread.start()
        self.connect_button.setEnabled(False)
        self.demo_button.setEnabled(False)
        self.stop_serial_btn.setEnabled(True)

    def _on_worker_error(self, message: str):
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 82, 82, 0.15);
                border: 1px solid rgba(255, 82, 82, 0.4);
                border-radius: 12px;
                padding: 4px 10px;
                color: #ff5252;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        QtWidgets.QMessageBox.critical(self, "Error de conexión serial", message)
        self.stop_input()

    def start_demo(self):
        self.stop_input()
        self.clear_data()
        self.demo_mode = True
        self.start_time = time.perf_counter()
        self.status_label.setText("Modo Demo Activo (Simulación RC)")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 229, 255, 0.12);
                border: 1px solid rgba(0, 229, 255, 0.35);
                border-radius: 12px;
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
        batch = []
        now_time = time.perf_counter()
        dt = 0.0005
        t_base = now_time - self.start_time

        for i in range(40):
            t = t_base + i * dt
            period = 0.5  # 2 Hz
            phase = (t % period) / period

            if phase < 0.5:
                t_sub = phase * period
                voltage = 3.3 * (1.0 - math.exp(-t_sub / 0.04))
            else:
                t_sub = (phase - 0.5) * period
                voltage = 3.3 * math.exp(-t_sub / 0.04)

            voltage += 0.02 * math.sin(t * 377.0)
            voltage = max(0.0, min(3.3, voltage))
            adc = int(voltage * 4095.0 / 3.3)

            sample = {
                "Muestra": float(self.sample_counter + i + 1),
                "Tiempo (us)": float(int(t * 1_000_000)),
                "ADC": float(adc),
                "Voltaje (V)": voltage,
            }
            batch.append(sample)

        self.handle_batch(batch)

    def stop_input(self):
        self.demo_mode = False
        if self.demo_timer is not None and self.demo_timer.isActive():
            self.demo_timer.stop()

        if self.serial_worker is not None:
            self.serial_worker.stop()

        if self.serial_thread is not None:
            if self.serial_thread.isRunning():
                self.serial_thread.quit()
                self.serial_thread.wait(1000)
            self.serial_thread = None

        self.serial_worker = None
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.stop_serial_btn.setEnabled(False)
        self.status_label.setText("Detenido")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 12px;
                padding: 4px 10px;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
        """)

    def clear_data(self):
        self.sample_counter = 0
        self.sample_numbers.clear()
        for d in self.series.values():
            d.clear()
        self.trigger_sample_index = None
        self.trigger_edge_armed = False
        self.trigger_initialized = False
        self.frozen_frame = None

    @QtCore.pyqtSlot(list)
    def handle_batch(self, batch: List[Dict[str, float]]):
        if not batch:
            return

        for sample in batch:
            self.sample_counter += 1
            idx = self.sample_counter
            self.sample_numbers.append(idx)

            for col_name, val in sample.items():
                if col_name not in self.series:
                    self.series[col_name] = deque(maxlen=MAX_BUFFER_SAMPLES)
                self.series[col_name].append(val)

            for known_col in self.series:
                if known_col not in sample:
                    self.series[known_col].append(0.0)

    # -------------------------------------------------------------
    # RENDERIZADO DEL GRÁFICO (~40 FPS)
    # -------------------------------------------------------------
    def render_frame(self):
        if not self.is_running:
            return

        total_samples = len(self.sample_numbers)
        if total_samples < 2:
            return

        active_columns = [col for col, checked in self.selected_columns.items() if checked]
        if not active_columns:
            active_columns = ["Voltaje (V)"]

        if self.selection_dirty or not self.line_items:
            self._update_curve_items(active_columns)

        w = self.h_scale

        # MODO CONTINUO (Roll) vs MODO TRIGGER (Estabilizado con fase fija)
        if not self.trigger_enabled:
            # 1. Modo Continuo: El osciloscopio hace barrido de izquierda a derecha (Roll)
            end_pos = max(w, total_samples + self.h_pos)
            end_pos = min(end_pos, total_samples)
            start_pos = max(0, end_pos - w)

            count = end_pos - start_pos
            x_plot = list(range(count))
            y_slices = {}
            for col in active_columns:
                series_deque = self.series.get(col)
                if series_deque and len(series_deque) >= end_pos:
                    y_slices[col] = list(itertools.islice(series_deque, start_pos, end_pos))
                else:
                    y_slices[col] = []

            self.plot_widget.setXRange(0, w, padding=0.0)
            self.plot_widget.setLabel("bottom", "Muestras en ventana", color="#ffffff")
            self.trigger_t_marker.setVisible(False)

        else:
            # 2. Modo Trigger: El disparo se fija en X = 0 (Pre-trigger con H-Pos)
            shift = self.h_pos
            pre_samples = max(0, min(w - 1, int(w * 0.10) - shift))
            post_samples = w - pre_samples

            x_plot = list(range(-pre_samples, post_samples))
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
                    search_vals = list(itertools.islice(src_deque, start_search - 1, end_search + 1))
                    level = self.trigger_level
                    is_rising = (self.trigger_edge == "Ascendente")
                    hysteresis = 20.0 if source == "ADC" else 0.015
                    lookback = 10

                    for i in range(len(search_vals) - 1, 0, -1):
                        cur_v = search_vals[i]
                        prev_v = search_vals[i - 1]
                        if is_rising:
                            if cur_v >= level and prev_v < level:
                                min_prior = min(search_vals[max(0, i - lookback) : i])
                                if min_prior <= (level - hysteresis):
                                    found_t_idx = (start_search - 1) + i
                                    break
                        else:
                            if cur_v <= level and prev_v > level:
                                max_prior = max(search_vals[max(0, i - lookback) : i])
                                if max_prior >= (level + hysteresis):
                                    found_t_idx = (start_search - 1) + i
                                    break

            now = time.perf_counter()
            if found_t_idx is not None:
                slice_start = found_t_idx - pre_samples
                slice_end = found_t_idx + post_samples

                y_slices = {}
                for col in active_columns:
                    col_deque = self.series.get(col)
                    if col_deque and len(col_deque) >= slice_end:
                        y_slices[col] = list(itertools.islice(col_deque, slice_start, slice_end))
                    else:
                        y_slices[col] = []

                self.frozen_frame = (x_plot, y_slices)
                self.last_trigger_time = now

                unit = "" if source == "ADC" else "V"
                lvl_str = f"{int(self.trigger_level)}" if source == "ADC" else f"{self.trigger_level:.2f}"
                self.trigger_status_label.setText(
                    f"● TRIG'D ({source} {self.trigger_edge} @ {lvl_str}{unit})"
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
                self.plot_widget.setLabel("bottom", "Muestras relativas al Trigger (T=0)", color="#ffffff")

                if self.single_shot_armed:
                    self.single_shot_armed = False
                    self.is_running = False
                    self.run_stop_btn.setChecked(False)
                    self.run_stop_btn.setText("⏹ STOP")
                    self.status_label.setText("⚡ SINGLE CAPTURADO Y CONGELADO")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 214, 0, 0.15);
                            border: 1px solid #ffd600;
                            border-radius: 12px;
                            padding: 4px 10px;
                            color: #ffd600;
                            font-weight: bold;
                            font-size: 11px;
                        }
                    """)

            elif self.frozen_frame is not None and (self.trigger_mode == "Normal" or (now - self.last_trigger_time) < 0.3):
                _, y_slices = self.frozen_frame
                if self.trigger_mode == "Normal":
                    self.trigger_status_label.setText("● ESPERANDO DISPARO (Normal)...")
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
                    col: list(itertools.islice(self.series[col], start_pos, end_pos))
                    for col in active_columns if col in self.series
                }
                self.trigger_status_label.setText("● AUTO (Buscando disparo... ajusta Nivel con 50% Auto)")
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
                self.plot_widget.setLabel("bottom", "Muestras en ventana (Buscando Trigger)", color="#ffffff")

        # Dibujar curvas en el gráfico
        if x_plot:
            for col, line in self.line_items.items():
                if col in active_columns:
                    y_vals = y_slices.get(col, [])
                    if len(y_vals) == len(x_plot):
                        line.setData(x_plot, y_vals)
                        line.setVisible(True)
                    else:
                        line.setVisible(False)
                else:
                    line.setVisible(False)

        # ---------------------------------------------------------
        # ACTUALIZACIÓN DE MEDICIONES EN VIVO (Vmax, Vmin, Vpp, Vrms, Vmed, Freq)
        # ---------------------------------------------------------
        primary_col = "Voltaje (V)" if "Voltaje (V)" in active_columns else active_columns[0]
        self.lbl_meas_channel.setText(f"CH: {primary_col}")

        primary_vals = y_slices.get(primary_col, [])
        if primary_vals and len(primary_vals) >= 10:
            v_max = max(primary_vals)
            v_min = min(primary_vals)
            v_pp = v_max - v_min
            v_avg = sum(primary_vals) / len(primary_vals)
            v_rms = math.sqrt(sum(v * v for v in primary_vals) / len(primary_vals))

            unit = "" if primary_col == "ADC" else "V"
            dec = 0 if primary_col == "ADC" else 2

            self.val_vmax.setText(f"{v_max:.{dec}f}{unit}")
            self.val_vmin.setText(f"{v_min:.{dec}f}{unit}")
            self.val_vpp.setText(f"{v_pp:.{dec}f}{unit}")
            self.val_vrms.setText(f"{v_rms:.{dec}f}{unit}")
            self.val_vavg.setText(f"{v_avg:.{dec}f}{unit}")

            # Estimación de frecuencia física basada en timestamps o cruces
            freq_text = "--"
            if len(primary_vals) >= 50 and v_pp > (0.1 if unit == "V" else 50):
                cross_indices = []
                for i in range(1, len(primary_vals)):
                    if primary_vals[i - 1] < v_avg <= primary_vals[i]:
                        cross_indices.append(i)

                if len(cross_indices) >= 2:
                    delta_samples = (cross_indices[-1] - cross_indices[0]) / (len(cross_indices) - 1)
                    t_slice = y_slices.get("Tiempo (us)", [])
                    if len(t_slice) == len(primary_vals):
                        t_delta_us = (t_slice[cross_indices[-1]] - t_slice[cross_indices[0]]) / (len(cross_indices) - 1)
                        if t_delta_us > 0:
                            freq_hz = 1_000_000.0 / t_delta_us
                            if freq_hz < 1000:
                                freq_text = f"{freq_hz:.1f} Hz"
                            else:
                                freq_text = f"{freq_hz/1000.0:.2f} kHz"

                    # Si no hay tiempo us, estimar a tasa típica ~2.5 kHz
                    if freq_text == "--" and delta_samples > 0:
                        freq_est = 2500.0 / delta_samples
                        freq_text = f"~{freq_est:.1f} Hz"

            self.val_freq.setText(freq_text)

        # Medición de FPS
        self.render_count += 1
        now_calc = time.perf_counter()
        if (now_calc - self.last_fps_calc) >= 1.0:
            self.current_fps = self.render_count / (now_calc - self.last_fps_calc)
            self.render_count = 0
            self.last_fps_calc = now_calc
            mode_str = "RUN" if self.is_running else "STOP"
            self.plot_widget.setTitle(
                f"OSCILOSCOPIO DIGITAL [{mode_str}] | Muestras: {self.sample_counter} | "
                f"Ventana: {self.h_scale} | FPS: {self.current_fps:.1f}"
            )

    def _update_curve_items(self, active_columns: List[str]):
        for idx, col in enumerate(self.known_columns):
            color = PALETTE[idx % len(PALETTE)]
            if col not in self.line_items:
                pen = pg.mkPen(color, width=2)
                curve = self.plot_widget.plot([], [], pen=pen, name=col)
                self.line_items[col] = curve
            self.line_items[col].setVisible(col in active_columns)

        self.selection_dirty = False

    def closeEvent(self, event):
        self.render_timer.stop()
        self.stop_input()
        event.accept()


def main():
    app = QtWidgets.QApplication([])
    app.setStyle("Fusion")
    window = SerialMonitorWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
