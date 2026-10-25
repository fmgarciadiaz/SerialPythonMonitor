from dataclasses import replace
from collections import deque
from threading import Event, Lock
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing
"""Monitor V18: adquisición configurable y generador DAC controlado desde el Q."""
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
_flow_trace = None
if os.environ.get("MONITOR_V18_FLOW_TRACE"):
    from monitor.v18.io.flow_trace import record as _flow_trace
from monitor.v18.number_format import number, formats
from monitor.v18.locale_axis import LocaleAxis
from monitor.v18.wav_source import seek_playback
from monitor.v18.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from monitor.v18.wav_source import prepare_wav, inspect_wav
from monitor.v18.audio_dc import DCBlocker
from monitor.v18.digital_filter import DigitalFilter, FilterConfig
from monitor.v18.radio_am import RadioConfig, radio_input_supported, radio_tuning_max
from monitor.v18.radio_stream import RadioStream, RadioTimeline
from monitor.v18.radio_tuning import tuning_bounds,alias_frequency,rf_frequency
from monitor.v18.processing import same_audio_continuity
from monitor.v18.processing import (BatchProcessor, ProcessingSettings,
    initialize_process_owner, process_owner_ready, process_owned_result)
from monitor.v18.history import SampleHistory
from monitor.v18.trigger import last_trigger_crossing
from monitor.v18.numeric_batch import NumericBatch, SampleClock
from monitor.v18.startup_trace import StartupTrace
from monitor.v18.spectrum import SpectralDisplay
from monitor.v18.receiver.unoq_usb import Connection, usb_devices
from monitor.v18.receiver.unoq_switch import Mode
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
from monitor.v18.receiver.unoq_autoload import ensure_scope, connect_scope
from monitor.v18.receiver.unoq_generator import GeneratorConfig, WAVES, MODES
from monitor.v18.receiver.unoq_acquisition import Configuration, BITS, RATES as RECEIVER_RATES, UART_RATES, SINGLE_CHANNEL_PERIODS
# V18: perfiles altos con DMA temporal conservado.
def _configuration_supported(bits, rate):
    try:
        config=Configuration(bits, rate)
        return not (config._native and (config._native.get('integration_pending') or config._native.get('internal_only')))
    except ValueError:
        return False


def _rate_label(rate):
    if rate >= 1000000:
        return f'{number(rate/1000000, formats.n_2f)} MHz'
    return f'{number(rate/1000, formats.n_1f)} kHz'


def _period_label(dt_us):
    if dt_us >= 100:
        return f'{number(dt_us/1000, formats.ng)} ms'
    return f'{number(dt_us, formats.n_1f)} µs'


COMMON_RATES = (1000, 5000, 10000, 20000, 31250, 40000)
RATES = tuple(rate for rate in RECEIVER_RATES if rate in COMMON_RATES or any(
    _configuration_supported(bits, rate) and Configuration(bits, rate)._native
    for bits in BITS))
import queue
from serial.tools import list_ports

from PyQt6 import QtCore, QtGui, QtWidgets
from monitor.v18.status_widgets import StatusLabel, StatusBox, SingleLineStatusLabel
import pyqtgraph as pg
if pg.Qt.QT_LIB != "PyQt6":
    raise RuntimeError("V18 requiere pyqtgraph con PyQt6; iniciar en un proceso Qt separado.")

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
    """Flat knob and progress arc, using native QDial interaction."""
    def paintEvent(self,event):
        painter=QtGui.QPainter(self);painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        center=QtCore.QPointF(self.width()/2,self.height()/2)
        radius=min(self.width(),self.height())/2-(6 if self.property('radioStyle') else 5)
        sweep=360 if self.wrapping() else 300
        start_angle=270 if self.wrapping() else 240
        box=QtCore.QRectF(center.x()-radius,center.y()-radius,2*radius,2*radius)
        ratio=(self.value()-self.minimum())/max(1,self.maximum()-self.minimum())
        accent=QtGui.QColor(('#62d9c4' if self.property('radioStyle') else '#55dfc4') if self.isEnabled() else '#505968')
        if self.isEnabled() and (self.property('redColor') or self.property('orangeColor') or self.property('virtualColor') or isinstance(self,AmplitudeDial)):
            stops=((0.0,'#55dfc4'),(0.5,'#659fea'),(0.75,'#9a80ed'),(1.0,'#bc6fff'))
            if self.property('redColor'):
                stops=((0.0,'#55dfc4'),(0.5,'#ffd166'),(1.0,'#ff5757'))
            elif self.property('orangeColor'):
                stops=((0.0,'#55dfc4'),(0.5,'#b7cf72'),(1.0,'#ff9500'))
            elif not self.property('virtualColor'):
                stops=((0.0,'#55dfc4'),(0.65,'#55dfc4'),(0.85,'#ffd166'),(1.0,'#ff5757'))
            for (low,left),(high,right) in zip(stops,stops[1:]):
                if ratio <= high:
                    fraction=max(0.0,min(1.0,(ratio-low)/(high-low)))
                    first,last=QtGui.QColor(left),QtGui.QColor(right)
                    accent=QtGui.QColor(*(round(a+(b-a)*fraction) for a,b in zip(first.getRgb()[:3],last.getRgb()[:3])))
                    break
        painter.setPen(QtGui.QPen(QtGui.QColor('#344b50' if self.property('radioStyle') else '#3c4654'),3,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
        painter.drawArc(box,start_angle*16,-sweep*16)
        nyquist=self.property('radioNyquist')
        extended=bool(self.property('radioExtended')) and nyquist is not None
        split=max(0.,min(1.,(float(nyquist)-self.minimum())/max(1,self.maximum()-self.minimum()))) if extended else 1.
        if extended:
            painter.setPen(QtGui.QPen(QtGui.QColor('#404b62' if self.isEnabled() else '#414650'),3,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
            painter.drawArc(box,round((start_angle-sweep*split)*16),round(-sweep*(1-split)*16))
        painter.setPen(QtGui.QPen(accent,3,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
        painter.drawArc(box,start_angle*16,round(-sweep*ratio*16))
        if extended and ratio>split:
            accent=QtGui.QColor('#88abd8' if self.isEnabled() else '#626b79')
            painter.setPen(QtGui.QPen(accent,3,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
            painter.drawArc(box,round((start_angle-sweep*split)*16),round(-sweep*(ratio-split)*16))
        painter.setPen(QtGui.QPen(QtGui.QColor('#405760' if self.property('radioStyle') else '#485363'),1));painter.setBrush(QtGui.QColor('#202c34' if self.property('radioStyle') else '#292f39'))
        painter.drawEllipse(center,radius-6,radius-6)
        angle=math.radians(start_angle-sweep*ratio)
        end=center+QtCore.QPointF((radius-9)*math.cos(angle),-(radius-9)*math.sin(angle))
        painter.setPen(QtGui.QPen(accent,2.5,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
        painter.drawLine(center,end)
        meter=getattr(self,'audio_meter_level',None)
        if meter is not None:
            ring=box.adjusted(-4,-4,4,4)
            painter.setPen(QtGui.QPen(QtGui.QColor('#263d36'),2,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring,start_angle*16,-sweep*16)
            level=max(0.,min(1.,meter))
            stops=((0.,'#55dfc4'),(.5,'#ffd166'),(1.,'#ff5757'))
            for (low,left),(high,right) in zip(stops,stops[1:]):
                if level<=high:
                    fraction=max(0.,min(1.,(level-low)/(high-low)))
                    first,last=QtGui.QColor(left),QtGui.QColor(right)
                    color=QtGui.QColor(*(round(a+(b-a)*fraction) for a,b in zip(first.getRgb()[:3],last.getRgb()[:3])))
                    break
            painter.setPen(QtGui.QPen(color,2,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring,start_angle*16,round(-sweep*level*16))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for frequency,color in zip(getattr(self, 'peak_frequencies', ()),getattr(self,'peak_colors',())):
            painter.setBrush(QtGui.QColor(color))
            if self.minimum() <= frequency <= self.maximum():
                position=(frequency-self.minimum())/max(1,self.maximum()-self.minimum())
                angle=math.radians(start_angle-sweep*position)
                # Keep candidates outside the progress arc: small, separate dots.
                marker_radius=radius+4.5
                point=center+QtCore.QPointF(marker_radius*math.cos(angle),-marker_radius*math.sin(angle))
                painter.drawEllipse(point,1.5,1.5)

    def setPeakFrequencies(self, frequencies, levels=None):
        self.peak_frequencies=tuple(frequencies)
        levels=tuple(levels) if levels is not None else (-30.,)*len(self.peak_frequencies)
        if len(levels)!=len(self.peak_frequencies):raise ValueError('Cada pico requiere su nivel dBFS')
        self.peak_colors=tuple('#776346' if level < -40 else '#bd925a' if level < -20 else '#ffbf69' for level in levels)
        self.update()


class FilterDial(InstrumentDial):
    """Filter control using the shared instrument dial style."""


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
VISIBLE_SAMPLES_MIN = 8
VISIBLE_SAMPLES_MAX = 250000  # Base para FS bajas; crece hasta al menos 4 s.
MAX_BUFFER_SAMPLES = 510000  # Base; el historial crece con el máximo por FS.
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
    "#00e5ff",  # Cyan neón (CH1)
    "#ffd600",  # Amarillo eléctrico (CH2)
    "#00e676",  # Verde neón 
    "#ff4081",  # Rosa neón 
    "#ff9100",  # Naranja (Muestra)
    "#b388ff",  # Púrpura (Tiempo)
]

CHANNEL_COLORS = {
    "CH1": "#00e5ff",
    "CH2": "#ffd600",
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


class OffsetDial(FineAdjustment, InstrumentDial):
    centered = QtCore.pyqtSignal()
    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._centering = True
            self.centered.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_centering', False):
            self._centering = False
            self.setSliderDown(False)
            self.centered.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class VoltageSpinBox(GeneratorValueSpinBox):
    def textFromValue(self, value):
        return self.locale().toString(float(value), 'f', 2)


class GeneratorFrequencySpinBox(GeneratorValueSpinBox):
    """Display frequency in Hz or kHz with two decimal places."""
    def textFromValue(self, value):
        scaled = float(value) / 1000 if value >= 1000 else float(value)
        text = self.locale().toString(scaled, 'f', 2)
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


CONTROL_HEIGHT = 30


class AcquisitionButton(QtWidgets.QPushButton):
    """Fixed icon position with text centered independently of label length."""
    def paintEvent(self, event):
        painter=QtWidgets.QStylePainter(self)
        option=QtWidgets.QStyleOptionButton();self.initStyleOption(option)
        text=option.text;icon=QtGui.QIcon(option.icon)
        option.text='';option.icon=QtGui.QIcon()
        painter.drawControl(QtWidgets.QStyle.ControlElement.CE_PushButton,option)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color=option.palette.color(QtGui.QPalette.ColorRole.ButtonText)
        painter.setPen(color);painter.setBrush(color)
        x=12;y=self.height()/2
        if text.startswith('▶'):
            painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x,y-6),QtCore.QPointF(x+11,y),QtCore.QPointF(x,y+6)]))
            text=text[1:].strip()
        elif text.startswith('⏹'):
            painter.drawRect(QtCore.QRectF(x,y-6,12,12));text=text[1:].strip()
        elif not icon.isNull():
            icon.paint(painter,QtCore.QRect(x-1,round(y)-8,16,16))
        painter.drawText(self.rect(),QtCore.Qt.AlignmentFlag.AlignCenter,text)


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
        painter.setPen(QtGui.QPen(QtGui.QColor('#55dfc4'), 2.5))
        path = QtGui.QPainterPath(QtCore.QPointF(33,22))
        path.cubicTo(23,7,9,8,9,22)
        path.cubicTo(9,36,23,37,33,22)
        path.cubicTo(43,7,57,8,57,22)
        path.cubicTo(57,36,43,37,33,22)
        painter.drawPath(path)
        painter.drawLine(16,22,24,22)
        painter.drawLine(42,22,50,22)
        painter.drawLine(46,18,46,26)
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
    TIMEOUT_SECONDS = 1800
    progress = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(bool, str)

    def __init__(self, serial, parent=None):
        super().__init__(parent)
        self.serial = serial

    def run(self):
        import subprocess
        from datetime import datetime
        folder = ROOT / 'diagnosticos' / 'resultados_autoload_v18'
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / ('preparar_q_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
        try:
            with log.open('w') as output, log.open('r') as reader:
                process = subprocess.Popen([sys.executable, '-m', 'monitor.v18.q_support.service',
                                            '--serial', self.serial, '--report', str(log.with_suffix('.json'))],
                                           cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                           text=True, start_new_session=True)
                deadline = time.monotonic() + self.TIMEOUT_SECONDS
                last_error = ''
                stage = 'Preparando Q'
                last_progress = 0.0
                while True:
                    for line in reader.readlines():
                        text = line.strip()
                        if text.endswith('…'):
                            stage = text.rstrip('…')
                            self.progress.emit(text)
                        elif text and time.monotonic()-last_progress >= .5:
                            self.progress.emit(stage+' · '+text.removeprefix('[INFO] ')[:140])
                            last_progress = time.monotonic()
                        if text.startswith('Error:'): last_error = text
                    code = process.poll()
                    if code is not None:
                        for line in reader.readlines():
                            if line.strip().startswith('Error:'): last_error = line.strip()
                        break
                    if time.monotonic() >= deadline:
                        # Every board operation has its own bounded timeout.
                        # Never kill a transaction while it may be restoring Q.
                        self.progress.emit(f'Preparación prolongada; esperando cierre seguro · {log.name}')
                        deadline = float('inf')
                    self.msleep(100)
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
    trace_configuration_ready = QtCore.pyqtSignal(object)
    generator_confirmed = QtCore.pyqtSignal(object)
    instrument_confirmed = QtCore.pyqtSignal(object)
    wav_confirmed = QtCore.pyqtSignal(object)
    switching = QtCore.pyqtSignal(bool)
    error_occurred = QtCore.pyqtSignal(str)
    shutdown_confirmed = QtCore.pyqtSignal(bool, str)
    finished = QtCore.pyqtSignal()

    def __init__(self, port, mode, r4_port=None, config=Configuration(), autoload=False, initial_generator=None, processing_settings=None, startup_gui_ack=False, processing_backend='thread'):
        super().__init__()
        self.port = port
        self.autoload = autoload
        self.initial_generator = initial_generator
        self.mode = Mode(mode)
        self.r4_port = r4_port
        self.config = config
        self.trace = StartupTrace()
        self._batch_lock=Lock()
        from monitor.v18.radio_delivery_budget import DeliveryBudget
        self.delivery_budget=DeliveryBudget()
        self.pending_dsp=0;self.pending_dsp_peak=0
        self.pending_batches=0;self.pending_batches_peak=0
        self.pending_batch_limit=8
        self.coalesced_rf_peak=0
        self.coalesced_flush_calls=0
        self.processing_settings = processing_settings
        self.startup_gui_ack = startup_gui_ack
        self._startup_ready = Event()
        self._processor = BatchProcessor()
        self._processing_executor = None
        self.processing_backend = processing_backend
        self._processing_process = None
        self._process_ready = None
        self.running = True
        self.requests = queue.Queue(maxsize=1)
        self.generator_requests = queue.Queue(maxsize=1)
        self.wav_requests = queue.Queue(maxsize=4)
        self.wav_levels = queue.Queue(maxsize=1)
        self.radio_output_source = None
        self._radio_output_session = 0
        self._receiver_process = None
        self._receiver_failure_snapshot = None
        self._pcm_session = 0
        self._pcm_sources = {}
        self._pcm_pending = set()
        self._pcm_prepared = set()
        self._pending_control_signals = 0
        self._ipc_trace_generation = None
        self._wav_transfer_paths = set()
        self._wav_prepare_request = None
        self._wav_prepare_task = None
        self._wav_prepare_active = None

    def _capture_delivery_failure(self, error, rf_pending=0):
        if 'atrasad' not in str(error).lower() and self._receiver_failure_snapshot is None:
            return
        with self._batch_lock:
            budget=self.delivery_budget
            self.delivery_failure_snapshot=dict(
                error=str(error),monotonic=time.monotonic(),bits=self.config.bits,rate=self.config.rate,
                pending_gui=self.pending_batches,pending_gui_peak=self.pending_batches_peak,
                pending_dsp=self.pending_dsp,pending_dsp_peak=self.pending_dsp_peak,
                retained_samples=budget.samples,retained_seconds=budget.seconds,
                retained_bytes=budget.bytes,retained_batches=len(budget.entries),
                rf_pending_samples=rf_pending,radio_enabled=bool(getattr(self.processing_settings,'radio_enabled',False)))
            if self._receiver_failure_snapshot is not None:
                self.delivery_failure_snapshot['receiver_failure_snapshot']=self._receiver_failure_snapshot
            # The child snapshot records the exact receiver failure. This host
            # stack records notification time, which can follow restoration.
            import threading,traceback
            frame=sys._current_frames().get(threading.main_thread().ident)
            self.delivery_failure_snapshot['gui_thread_stack_at_notification']=(
                traceback.format_stack(frame,limit=32) if frame is not None else [])
            self.delivery_failure_snapshot['gui_thread_stack_at_failure']=self.delivery_failure_snapshot['gui_thread_stack_at_notification']

    def publish_batch(self,batch):
        with self._batch_lock:
            settings=self.processing_settings
            independent=(settings is not None and settings.radio_enabled) or self.delivery_budget.radio_entries>0 or getattr(self,'_audio_delivery_active',False)
            if not independent and self.pending_batches>=self.pending_batch_limit:
                raise RuntimeError('Procesamiento DSP/GUI atrasado: límite de 8 lotes pendientes; adquisición detenida sin descartar muestras silenciosamente.')
            self.delivery_budget.reserve(batch,settings,getattr(batch,'acquisition',self.config))
            self.pending_batches+=1
            self.pending_batches_peak=max(self.pending_batches_peak,self.pending_batches)
            batch.pending_batches=self.pending_batches
            settings = self.processing_settings
            batch.radio_output_session = self._radio_output_session
        if self.trace.enabled:
            self.trace.record(getattr(batch,'startup_trace_generation',None), 'first_batch_reserved', once=True)
        try:self._dispatch_reserved_batch(batch,settings)
        except Exception:
            self.batch_consumed(batch)
            raise

    def _emit_batch_ready(self,batch):
        if getattr(self,'_audio_delivery_active',False):
            with self._batch_lock:self._release_ipc_credit(batch)
        if self.trace.enabled:
            self.trace.record(getattr(batch,'startup_trace_generation',None),'first_batch_ready_signal',once=True)
        self.batch_ready.emit(batch)

    def _dispatch_reserved_batch(self,batch,settings):
        if settings is None:
            self._emit_batch_ready(batch)
        elif settings.active and self.processing_backend=='process' and not self._ensure_process().done():
            # Lazy startup after OFF: RF delivery remains live and bounded;
            # audio/filter activation waits for its state owner to be ready.
            batch.processing=dict(generation=settings.generation,settings=settings,
                audio=None,audio_filter=None,radio_key=None,radio_status='Preparando DSP…',timings={})
            if settings.filter.source in ('CH1','CH2'):
                batch.columns['FILTER']=np.full(len(batch),np.nan)
            self._emit_batch_ready(batch)
        elif not settings.active and self._processing_executor is None:
            batch.processing = dict(generation=settings.generation, settings=settings,
                audio=None, audio_filter=None, radio_key=None, radio_status=None, timings={})
            self._emit_batch_ready(batch)
        else:
            if self._processing_executor is None:
                self._processing_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='v18-dsp')
            process=self._process_separately if self.processing_backend=='process' else self._processor.process
            with self._batch_lock:
                self.pending_dsp+=1;self.pending_dsp_peak=max(self.pending_dsp_peak,self.pending_dsp)
            try:
                self._processing_executor.submit(process,batch,settings).add_done_callback(
                    lambda future,original=batch:self._processed(future,original))
            except Exception:
                with self._batch_lock:self.pending_dsp=max(0,self.pending_dsp-1)
                self.batch_consumed(batch)
                raise

    def _ensure_process(self):
        if self._processing_process is None:
            self._processing_process=ProcessPoolExecutor(max_workers=1,
                mp_context=multiprocessing.get_context('spawn'),initializer=initialize_process_owner)
            self._process_ready=self._processing_process.submit(process_owner_ready)
        return self._process_ready

    def _process_separately(self,batch,settings):
        if _flow_trace is not None:_flow_trace("dsp_start",getattr(batch,"_ipc_credit_id",None))
        self._ensure_process().result()
        # The parent keeps RF histories; the DSP owner needs only its input columns.
        from types import SimpleNamespace
        required={'Muestra','Tiempo (us)'}
        if settings.radio_enabled:required.add('CH1')
        if settings.filter.source in ('CH1','CH2'):required.add(settings.filter.source)
        payload=SimpleNamespace(columns={name:values for name,values in batch.columns.items() if name in required},
            acquisition=getattr(batch,'acquisition',settings.acquisition),
            flow_batch_id=getattr(batch,'_ipc_credit_id',None))
        batch.processing,filtered=self._processing_process.submit(process_owned_result,payload,settings).result()
        if filtered is None:
            batch.columns.pop('FILTER',None)
        else:
            batch.columns['FILTER']=filtered
        return batch

    def set_processing_settings(self, settings):
        with self._batch_lock:
            self.processing_settings = settings

    def set_radio_output_source(self, source):
        with self._batch_lock:
            self._radio_output_session += 1
            self.radio_output_source=source

    def _feed_radio_output(self,batch):
        result=getattr(batch,'processing',None)
        with self._batch_lock:
            source=self.radio_output_source;settings=self.processing_settings
            session=self._radio_output_session
        if source is None or result is None or settings is None or not settings.radio_enabled or getattr(batch,'radio_output_session',None)!=session:
            return
        if same_audio_continuity(result['settings'],settings):
            columns=getattr(batch,'columns',{})
            # Publish ready audio before passive correlation, which can take
            # longer than a DAC refill. Detection still clears/stops output.
            source.feed_result(result)
            if 'CH1' in columns:
                source.observe_input(columns['CH1'],settings.acquisition.actual_rate)
        else:
            previous=result['settings']
            # A retune intentionally rejects the old station's samples, but
            # losing their duration drains the live DAC reserve on every edit.
            # Only compensate within the same output session and sample clocks.
            if (previous.radio_enabled and previous.acquisition==settings.acquisition
                    and previous.audio_rate==settings.audio_rate==source.rate):
                audio=result.get('audio_filter' if source.input_source=='FILTER' else 'audio')
                if audio is not None:source.feed_transition_silence(len(audio))

    def _processed(self, future, original=None):
        try:
            batch = future.result()
            if _flow_trace is not None:_flow_trace("dsp_done",getattr(batch,"_ipc_credit_id",None))
            self._feed_radio_output(batch)
        except Exception as exc:
            self.batch_consumed(original)
            self.error_occurred.emit(f'Procesamiento DSP: {exc}')
            self.running = False
        else:
            if getattr(batch,'processing',{}).get('settings') is not None and batch.processing['settings'].radio_enabled:
                # IPC carries owned copies. RADIO DSP is finished with this
                # transfer; GUI retains the entire batch under DeliveryBudget.
                # Do not make new audio wait for GUI consumption of that copy.
                with self._batch_lock:self._release_ipc_credit(batch)
            self._emit_batch_ready(batch)
        finally:
            with self._batch_lock:self.pending_dsp=max(0,self.pending_dsp-1)

    def _emit_after_processing(self, signal, *args):
        # Control acknowledgements cannot overtake preceding samples, and their
        # executor queue remains bounded even if the device emits no RF.
        if self._processing_executor is None:
            signal.emit(*args)
            return
        with self._batch_lock:
            if self._pending_control_signals >= 64:
                raise RuntimeError('DSP atrasado: límite de confirmaciones pendientes')
            self._pending_control_signals += 1
        def emit_ordered():
            try:
                signal.emit(*args)
            finally:
                with self._batch_lock:
                    self._pending_control_signals -= 1
        try:
            self._processing_executor.submit(emit_ordered)
        except BaseException:
            with self._batch_lock:
                self._pending_control_signals -= 1
            raise

    def _release_ipc_credit(self,batch):
        # Caller holds _batch_lock. Exactly one release per copied RF transfer.
        backend=self._receiver_process
        credit=getattr(batch,'_ipc_credit_id',None)
        if backend is not None and credit is not None:
            del batch._ipc_credit_id
            backend.release(credit)

    def batch_consumed(self,batch=None):
        with self._batch_lock:
            before=len(self.delivery_budget.entries)
            if batch is None and before:
                batch = self.delivery_budget.entries[0][0]
            if _flow_trace is not None:_flow_trace("batch_consumed",getattr(batch,"_ipc_credit_id",None))
            self.delivery_budget.release(batch)
            if len(self.delivery_budget.entries)<before:
                self.pending_batches=max(0,self.pending_batches-1)
                self._release_ipc_credit(batch)

    def delivery_pressure(self):
        with self._batch_lock:
            settings=self.processing_settings
            return self.pending_dsp if (settings is not None and settings.radio_enabled) or self.delivery_budget.radio_entries>0 or getattr(self,'_audio_delivery_active',False) else self.pending_batches

    def ready_gui_batches(self):
        with self._batch_lock:return max(0,self.pending_batches-self.pending_dsp)

    def set_adc_bits(self, bits):
        pass  # Hardware settings are applied together through configure(), not this display hook.

    def _shutdown_receiver(self, receiver):
        try:
            receiver.shutdown_output()
            self.shutdown_confirmed.emit(True, 'Salida apagada confirmada')
        except Exception as exc:
            self.shutdown_confirmed.emit(False, f'Salida sin confirmar: {exc}')
            raise
        finally:
            receiver.close()

    def stop(self):
        self.running = False
        # Wake the receiver immediately, including while the parent drains DSP.
        backend=getattr(self,'_receiver_process',None)
        if backend is not None:backend.submit('shutdown')

    def confirm_startup(self, bits, rate):
        if (bits,rate)==(self.config.bits,self.config.rate):
            self._startup_ready.set()

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

    def _ipc_wav_source(self, source, rate):
        """Transfer descriptors only; mutable audio generators remain in the GUI host."""
        if getattr(source, 'live', False):
            self._pcm_session += 1
            session = self._pcm_session
            self._pcm_sources[session] = source
            descriptor = dict(kind='live', session=session, rate=rate,
                              length=len(source), radio_audio=bool(getattr(source, 'radio_audio', False)))
            for name in ('credit_window', 'poll_interval', 'chunk_interval', 'chunk_burst',
                         'minimum_blocks', 'maximum_blocks', 'target_blocks'):
                if hasattr(source, name):
                    descriptor[name] = getattr(source, name)
            return descriptor
        import tempfile
        handle = tempfile.NamedTemporaryFile(prefix='scope-v18-wav-', suffix='.npy', delete=False)
        path = handle.name
        try:
            with handle:
                np.save(handle, np.asarray(source), allow_pickle=False)
        except BaseException:
            Path(path).unlink(missing_ok=True)
            raise
        self._wav_transfer_paths.add(path)
        return dict(kind='npy', path=path)

    def _prepare_live_audio(self, source):
        from monitor.v18.fm_source import FMSource
        if isinstance(source, FMSource):
            from monitor.v18.synth_process import prepare, initialize_worker
            if getattr(self, '_synth_process', None) is None:
                self._synth_process = ProcessPoolExecutor(max_workers=1,
                    mp_context=multiprocessing.get_context('spawn'),
                    initializer=initialize_worker)
            with source.lock:
                parameters = source.parameters
            self._synth_process.submit(prepare, source.rate, parameters).result()
        else:
            source.prepare_audio()

    def _queue_ipc_wav(self, backend, op, source=None, rate=20000):
        # At most one warmup runs and one latest request is retained. STOP
        # invalidates that request immediately, even if native JIT is running.
        if op == 1 and getattr(source, 'live', False) and hasattr(source, 'prepare_audio'):
            self._wav_prepare_request = (source, rate)
            return
        self._wav_prepare_request = None
        if op == 4:
            backend.submit('seek', seconds=source)
        else:
            descriptor = self._ipc_wav_source(source, rate) if op == 1 else None
            backend.submit('wav', opcode=op, codes=descriptor, rate=rate)

    def _advance_wav_preparation(self, backend):
        task = self._wav_prepare_task
        if task is not None:
            if not task.done():
                return
            active = self._wav_prepare_active
            self._wav_prepare_task = self._wav_prepare_active = None
            requested = self._wav_prepare_request
            if requested is not None and requested[0] is active[0]:
                task.result()
                source, rate = requested
                descriptor = self._ipc_wav_source(source, rate)
                self._pcm_prepared.add(descriptor['session'])
                self._wav_prepare_request = None
                backend.submit('wav', opcode=1, codes=descriptor, rate=rate)
            else:
                # Retrieve stale errors, but a cancelled session cannot BEGIN.
                try:
                    task.result()
                except Exception:
                    pass
        if self._wav_prepare_request is not None and self._wav_prepare_task is None:
            self._wav_prepare_active = self._wav_prepare_request
            self._wav_prepare_task = self._pcm_executor.submit(
                self._prepare_live_audio, self._wav_prepare_active[0])

    def _produce_pcm(self, backend, event):
        """One producer owns rendering; session/offset travel with every response."""
        render_started_at=time.monotonic()
        session = event['session']
        source = self._pcm_sources.get(session)
        start, end = event['start'], event['end']
        flow_key=f'pcm:{session}:{start}'
        if _flow_trace is not None:_flow_trace('pcm_parent_produce_begin',flow_key)
        try:
            if source is None:
                return
            if event.get('requested_at') is not None and hasattr(source,'observe_transport'):
                source.observe_transport('pcm_request_to_render',time.monotonic()-event['requested_at'])
            if session not in self._pcm_prepared:
                if hasattr(source, 'prepare_audio'):
                    source.prepare_audio()
                self._pcm_prepared.add(session)
            levels = event.get('levels')
            from monitor.v18.fm_source import FMSource
            if isinstance(source, FMSource):
                from monitor.v18.synth_process import render
                with source.lock:
                    parameters = source.parameters
                codes, metrics = self._synth_process.submit(render, start, end, parameters, levels).result()
                source.position = metrics['position']
                source.remote_active_voice_count = len(metrics['active_notes'])
                source.max_render_ms = metrics['max_render_ms']
                source.slow_render_blocks = metrics['slow_render_blocks']
                source.compressor_gain = metrics['compressor_gain']
            elif getattr(source,'radio_audio',False) and event.get('chunk_points'):
                chunk_points=int(event['chunk_points'])
                if chunk_points<=0 or end-start>8*chunk_points or (end-start)%chunk_points:
                    raise ValueError('Ráfaga RADIO PCM inválida')
                rendered=[]
                for offset in range(start,end,chunk_points):
                    block=source.try_codes(offset,offset+chunk_points,levels)
                    if block is None:break
                    rendered.append(block)
                codes=np.concatenate(rendered) if rendered else None
            elif hasattr(source, 'try_codes'):
                codes = source.try_codes(start, end, levels)
            elif levels is None:
                codes = source[start:end]
            else:
                codes = source.render_dac_codes(start, end, *levels)
            if _flow_trace is not None:
                _flow_trace('pcm_parent_codes_none' if codes is None else 'pcm_parent_codes_ready',flow_key)
            # Radio starvation is retried by the child at this same offset.
            timing=dict(parent_received_at=event.get('parent_received_at',render_started_at),
                        render_started_at=render_started_at,render_finished_at=time.monotonic())
            backend.submit('pcm', session=session, offset=start, codes=codes,timing=timing)
            if _flow_trace is not None:_flow_trace('pcm_parent_submitted',flow_key)
        except Exception as exc:
            self.error_occurred.emit(f'Producción PCM: {exc}')
            self.running = False
        finally:
            self._pcm_pending.discard((session, start))

    def _ipc_event(self, backend, event):
        kind = event['type']
        if kind == 'batch':
            if _flow_trace is not None:_flow_trace('parent_recv_batch',event['id'])
            batch = event['batch']
            from monitor.v18.io.rf_batch import RawRfBatch, CompactAdc8RfBatch
            self.last_rf_ipc_kind = type(batch).__name__
            if isinstance(batch, (RawRfBatch, CompactAdc8RfBatch)):
                generation = batch.receiver_generation
                if getattr(self, '_rf_clock_generation', None) != generation:
                    from monitor.v18.numeric_batch import SampleClock
                    self._rf_clock = SampleClock(batch.acquisition.timestamp_hz)
                    self._rf_clock_generation = generation
                batch = batch.materialize(self._rf_clock)
            batch._ipc_credit_id = event['id']
            if self.trace.enabled:
                batch.startup_trace_generation = self._ipc_trace_generation
            try:
                self.publish_batch(batch)
            except BaseException:
                if hasattr(batch, '_ipc_credit_id'):
                    del batch._ipc_credit_id
                    backend.release(event['id'])
                raise
        elif kind == 'signal':
            name, args = event['name'], event.get('args', ())
            if name=='wav_confirmed' and args:
                # BUFFERING/PLAYING audio must not depend on GUI consumption.
                self._audio_delivery_active=getattr(args[0],'state',None) in (1,2)
            if name == 'instrument_confirmed' and args and args[0] is not None:
                # Calibration identity is stable; relay identity belongs to the
                # full restoration snapshot, not the three-field Bode key.
                identity = args[0]
                args = ({key: identity[key] for key in
                    ('board_serial', 'app', 'firmware_sha256')},)
            if name == 'wav_confirmed' and args:
                if int(getattr(args[0], 'state', -1)) == 4 and event.get('pcm_transport') is not None:
                    # Retain child-side failure evidence for every PCM source,
                    # including Synth, which has no RADIO diagnostics hook.
                    self.last_pcm_underrun = dict(source_session=event.get('source_session'),
                        status_observed_at=event.get('status_observed_at'),
                        pcm_transport=event['pcm_transport'])
                source = self._pcm_sources.get(event.get('source_session'))
                if source is not None and hasattr(source, 'observe_status'):
                    source.observe_status(args[0])
                    if event.get('pcm_transport') is not None and hasattr(source,'observe_transport_snapshot'):
                        source.observe_transport_snapshot(event['pcm_transport'])
                    if event.get('pcm_transport') is not None and int(args[0].state)==4 and hasattr(source,'record_transport_underrun'):
                        source.record_transport_underrun(event['pcm_transport'],event.get('status_observed_at'))
                        self.last_pcm_underrun=source.diagnostics()
            signal = getattr(self, name, None)
            if signal is None or not hasattr(signal, 'emit'):
                raise RuntimeError(f'Señal IPC desconocida: {name}')
            if name == 'acquisition_confirmed' and self.trace.enabled:
                config = Configuration(*args)
                self._ipc_trace_generation = self.trace.begin('receiver_configuration', config)
                self.trace.record(self._ipc_trace_generation, 'target_configuration_confirmed')
            # FIFO applies equally to acquisition, generator, WAV and shutdown ACKs.
            self._emit_after_processing(signal, *args)
            if name == 'acquisition_confirmed' and self.trace.enabled:
                self._emit_after_processing(self.trace_configuration_ready,
                    (self._ipc_trace_generation, *args))
        elif kind == 'pcm_request':
            event['parent_received_at']=time.monotonic()
            if _flow_trace is not None:_flow_trace('pcm_parent_request_recv',f"pcm:{event['session']}:{event['start']}")
            key = (event['session'], event['start'])
            if key not in self._pcm_pending:
                if len(self._pcm_pending) >= 2:
                    raise RuntimeError('Productor PCM atrasado: límite IPC excedido')
                self._pcm_pending.add(key)
                self._pcm_executor.submit(self._produce_pcm, backend, event)
        elif kind == 'error':
            raise RuntimeError(event.get('text', 'Error del proceso receptor'))
        elif kind == 'pcm_released':
            session = event['session']
            self._pcm_sources.pop(session, None)
            self._pcm_prepared.discard(session)
        elif kind == 'wav_released':
            path = event.get('path')
            if path in self._wav_transfer_paths:
                Path(path).unlink(missing_ok=True)
                self._wav_transfer_paths.discard(path)
        elif kind == 'finished':
            self.running = False

    @QtCore.pyqtSlot()
    def run(self):
        from monitor.v18.process_activity import MacActivity,acquisition_activity_mode
        activity=None
        try:
            mode=acquisition_activity_mode('parent')
            if self.running and mode!='off':activity=MacActivity(mode)
            self._run_receiver_process()
        finally:
            try:
                if activity is not None:activity.close()
            finally:self.finished.emit()

    def _run_receiver_process(self):
        from monitor.v18.io.receiver_process import ReceiverProcess
        from monitor.v18.io.pcm_request_pump import PcmRequestPump
        backend = None
        pcm_pump = None
        terminal = None
        self._pcm_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='v18-pcm')
        try:
            if not self.running:
                return
            # V18 only connects to the installed, known-good Q application.
            # It never invokes firmware/app autoload or programming helpers.
            backend = ReceiverProcess(self.port, self.mode, self.config,
                r4_port=self.r4_port, initial_generator=self.initial_generator,
                # Interactive close verifies restoration without the campaign's
                # ten-second sustained acquisition hold.
                startup_gui_ack=self.startup_gui_ack, recovery_seconds=.2)
            self._receiver_process = backend
            backend.start()
            def pcm_failed(exc):
                self.error_occurred.emit(f'Canal PCM: {exc}')
                self.running=False
            pcm_pump=PcmRequestPump(backend.receive_pcm_request,
                lambda event:self._ipc_event(backend,event),pcm_failed).start()
            startup_sent = not self.startup_gui_ack
            while self.running:
                if self._startup_ready.is_set():
                    backend.submit('startup', bits=self.config.bits, rate=self.config.rate)
                    self._startup_ready.clear()
                    startup_sent = True
                if startup_sent:
                    try:
                        mode, r4_port, config = self.requests.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        backend.submit('output', mode=mode, r4_port=r4_port, config=config)
                    try:
                        config = self.generator_requests.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        backend.submit('generator', config=config)
                    try:
                        amplitude, offset = self.wav_levels.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        backend.submit('levels', amplitude=amplitude, offset=offset)
                    try:
                        op, codes, rate = self.wav_requests.get_nowait()
                    except queue.Empty:
                        pass
                    else:
                        self._queue_ipc_wav(backend, op, codes, rate)
                self._advance_wav_preparation(backend)
                events = backend.poll()
                for event in events:
                    self._ipc_event(backend, event)
                terminal = backend.poll_terminal()
                if terminal is not None:
                    self._receiver_failure_snapshot=terminal.get('failure_snapshot')
                    if terminal.get('error'):
                        raise RuntimeError(terminal['error'])
                    break
                if not events:
                    time.sleep(.001)
        except Exception as exc:
            if self.running:
                self._capture_delivery_failure(exc)
                self.error_occurred.emit(str(exc))
        finally:
            self.running = False
            self._wav_prepare_request = None
            if pcm_pump is not None:pcm_pump.close()
            if backend is not None:
                backend.submit('shutdown')
                try:
                    backend.close()
                    terminal = terminal or backend.poll_terminal()
                except Exception as exc:
                    terminal = dict(error=str(exc), shutdown_confirmed=False)
            self._pcm_executor.shutdown(wait=True,cancel_futures=True)
            if getattr(self, '_synth_process', None) is not None:
                self._synth_process.shutdown(wait=True)
                self._synth_process = None
            if self._processing_executor is not None:
                self._processing_executor.shutdown(wait=True,cancel_futures=True)
            if self._processing_process is not None:
                self._processing_process.shutdown(wait=True)
            if backend is not None:
                terminal = terminal or dict(error='Sin resultado final del receptor V18', shutdown_confirmed=False)
                if terminal.get('failure_snapshot') is not None:
                    self._receiver_failure_snapshot=terminal['failure_snapshot']
                if terminal.get('error'):
                    captured=getattr(self,'delivery_failure_snapshot',None) or {}
                    if (captured.get('error')!=str(terminal['error']) or
                            captured.get('receiver_failure_snapshot')!=self._receiver_failure_snapshot):
                        self._capture_delivery_failure(terminal['error'])
                confirmed = bool(terminal.get('shutdown_confirmed'))
                self.shutdown_confirmed.emit(confirmed,
                    'Salida apagada confirmada' if confirmed else 'Salida sin confirmar')
                if terminal.get('error'):
                    self.error_occurred.emit(terminal['error'])
            self._receiver_process = None
            for path in self._wav_transfer_paths:
                Path(path).unlink(missing_ok=True)
            self._wav_transfer_paths.clear()
            self._pcm_sources.clear()


class SerialMonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setLocale(QtCore.QLocale.system())
        self.resize(1320, 920)

        self.channel_colors = CHANNEL_COLORS.copy()
        self.channel_palette = tuple(PALETTE)

        # Buffers circulares
        self.sample_counter = 0
        self.batch_queue_delay_ms = 0.0
        self.batch_queue_delay_max_ms = 0.0
        self.timed_batch_count = 0
        self.batch_pending_peak=0
        self.batch_processing_peak_ms=0;self.batch_processing_total_ms=0;self.batch_processing_count=0
        self.sample_numbers: SampleHistory = SampleHistory(MAX_BUFFER_SAMPLES)
        self.series: Dict[str, SampleHistory] = {
            "CH1": SampleHistory(MAX_BUFFER_SAMPLES),
            "CH2": SampleHistory(MAX_BUFFER_SAMPLES),
            "Muestra": SampleHistory(MAX_BUFFER_SAMPLES),
            "Tiempo (us)": SampleHistory(MAX_BUFFER_SAMPLES),
        }

        self.digital_filter = DigitalFilter()
        self.filter_config = FilterConfig(source='OFF')
        self._processing_generation = 0
        self._audio_continuity_epoch = 0
        self.channel_colors["FILTER"] = "#00e676"
        self.series["FILTER"] = SampleHistory(MAX_BUFFER_SAMPLES)
        self.known_columns = ["CH1", "CH2", "FILTER", "RADIO"]
        self.radio_stream = None
        self.radio_key = None
        self.radio_filter = DigitalFilter()
        self.channel_colors['RADIO'] = '#ffb74d'
        # Por defecto CH1 (CH1) y CH2 (CH2) activos simultáneamente
        self.selected_columns: Dict[str, bool] = {
            "CH1": True,
            "CH2": True,
            "FILTER": False,
            "RADIO": False,
        }
        self.selection_dirty = True

        # Canal activo seleccionado para la barra de mediciones
        self.active_meas_channel = "CH1"

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
        self.trigger_source = "CH1"
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
        self.demo_ch2_prev = 0.0

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
        for control in self.findChildren(QtWidgets.QPushButton)+self.findChildren(QtWidgets.QComboBox):
            control.setFixedHeight(CONTROL_HEIGHT)
        for options in (self.spectral.temporal_settings,self.spectral.settings,self.spectral.bode_settings):
            controls=(options.findChildren(QtWidgets.QComboBox)+options.findChildren(QtWidgets.QAbstractSpinBox)
                      +options.findChildren(QtWidgets.QPushButton))
            for control in controls:
                control.setMinimumSize(0,0)
                control.setMaximumSize(16777215,16777215)
                control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
                if control.property('bodeField'):
                    control.setFixedHeight(28)
                    control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
                elif control.property('bodeAction'):
                    control.setFixedSize(30,30)
                    control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,QtWidgets.QSizePolicy.Policy.Fixed)
            for form in options.findChildren(QtWidgets.QFormLayout):
                form.setVerticalSpacing(2)
                form.setHorizontalSpacing(4)
                form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
                form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.DontWrapRows)
        for control in (self.port_combo,self.destination_combo,self.r4_combo,
                        self.config_bits_combo,self.config_rate_combo,self.refresh_button):
            control.setFixedHeight(26)
        self.spectral.secondary_stack.setFixedHeight(CONTROL_HEIGHT)
        self._reserve_generator_height()
        self.refresh_ports()

        # Timer de dibujo desacoplado (~60 FPS)
        self.render_timer = QtCore.QTimer(self)
        self.render_timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self._gui_slow_callbacks=deque(maxlen=128)
        self.render_timer.timeout.connect(self._render_with_diagnostics)
        self.render_timer.start(RENDER_INTERVAL_MS)

        self.setWindowTitle('Scope V18 · PyQt6 · protocolo 4 · firmware Q V18')
        self.setWindowIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets/scope_app.svg')))
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
        self._sync_radio_input_controls()
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
        generator_text=self.generator_status.text()
        if self.generator_mode.currentIndex()==7:
            panel=self.radio_output_panel
            source=panel.source
            playback=('preparando A0' if not source.played else 'A0 activo') if source is not None else 'A0 detenido'
            reception='RADIO encendida' if self.radio_enabled.isChecked() else 'RADIO apagada'
            brief=f'Radio · IN {panel.input_source.currentText()} · {self.radio_frequency.value():g} kHz · {playback}'
            detail=(f'{brief}\n{reception} · audio {self.radio_output_rate.currentData()/1000:g} kHz'
                    f' · volumen {panel.volume.value()} % · offset {self.radio_offset.value():g} V\n{panel.state.text()}')
            self.generator_status_box.update_status(brief,detail)
        else:
            self.generator_status_box.update_status(generator_text)
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
            if mode == 1:
                name += ' · ' + self.spectral.fft_mode.currentText()
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
                padding: 2px 8px;
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
        generator_layout.setContentsMargins(9,4,9,4)
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
        port_card.setObjectName("controlQCard")
        port_card.setStyleSheet("""
            QFrame#controlQCard {
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

        self.port_combo = GeneratorComboBox()
        self.port_combo.setProperty("centerInWholeBox", True)
        self.port_combo.setMinimumWidth(0)
        self.port_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
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
        self.demo_button.setToolTip("Generador de prueba 2 Canales (CH1 y CH2)")
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
                padding: 2px 8px;
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
        self.destination_combo = GeneratorComboBox()
        self.destination_combo.setProperty("centerInWholeBox", True)
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
        self.config_bits_combo = GeneratorComboBox()
        self.config_bits_combo.setProperty("centerInWholeBox", True)
        for bits in BITS: self.config_bits_combo.addItem('16 bits · (OS)' if bits == 16 else f'{bits} bits', bits)
        self.config_bits_combo.setToolTip('16 bits: oversampling por hardware de 16 conversiones de 14 bits.\nMáximo 76,23 kHz SPI / 31,25 kHz UART; promedia ruido y señales rápidas.\nNo garantiza 16 bits de precisión analógica.')
        self.config_bits_combo.setCurrentIndex(self.config_bits_combo.findData(14))
        destination_layout.addWidget(self.config_bits_combo, 3, 1, 1, 2)
        destination_layout.addWidget(QtWidgets.QLabel('TASA'), 4, 0)
        self.config_rate_combo = GeneratorComboBox()
        self.config_rate_combo.setProperty("centerInWholeBox", True)
        self.config_rate_combo.setToolTip('T: período entre pares de muestras.\nAdq: tiempo de carga del capacitor por canal y subconversión.\nUna ventana más corta exige menor impedancia de fuente para conservar el asentamiento.\nEn 16 bits se realizan 16 subconversiones por canal.')
        for rate in RATES:
            label = _rate_label(rate) + ' · ' + _period_label(next(Configuration(bits, rate) for bits in BITS if _configuration_supported(bits, rate)).dt_us)
            config = next(Configuration(bits, rate) for bits in (14,8,10,12,16)
                          if _configuration_supported(bits, rate))
            if rate > 31250: label += f' · SPI · ADC {number(config.sampling_us, formats.n_1f)} µs'
            if config.channels==1: label=_rate_label(rate) + ' (CH1)'
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
        self.port_combo.setStyleSheet(compact_selector_style.replace("2px 16px 2px 4px", "2px 4px"))

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

        lbl_fs = QtWidgets.QLabel("FS")
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
        self.prepare_q_button.setToolTip('Verificar la pareja Scope V18 aceptada o actualizarla con respaldo y recuperación.')
        self.prepare_q_button.setEnabled(True)
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
                padding: 2px 8px;
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

        lbl_baud.setText("ENLACE")
        # Explicit tag widths avoid squeezing labels inside inherited frame padding.
        for label in (lbl_port,lbl_baud,lbl_adc,lbl_fs):
            label.setFixedWidth(label.fontMetrics().horizontalAdvance(label.text())+12)
            label.setFixedHeight(22)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight:700; font-size:10px; color:#8f98a8; background:transparent; border:1px solid #2e3543; border-radius:4px; padding:0; margin:0;")
        # Compact control/connect/demo columns; equal wider link/ADC columns.
        for column, stretch in enumerate((3, 3, 4, 4)):
            top_layout.setColumnStretch(column, stretch)
            top_layout.setColumnMinimumWidth(column, 120 if column < 2 else 180)
        for button in (self.connect_button, self.demo_button,
                       self.prepare_q_button, self.btn_xaxis_toggle):
            button.setFixedHeight(34)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        for card in (port_card, baud_card, adc_card, fs_card, trace_card):
            card.setStyleSheet(card.styleSheet().replace('padding: 2px 6px;', 'padding: 0;'))
            card.layout().setContentsMargins(4, 1, 4, 1)
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
        self.btn_xaxis_toggle.setStyleSheet(self.btn_xaxis_toggle.styleSheet().replace('padding: 2px 8px;', 'padding: 2px 6px;'))
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
        self.plot_widget.setTitle("SCOPE V18 - CH1 [A2] / CH2 [A3]")
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
            label="Trig",
            labelOpts={"position": 0.95, "color": "#ffffff", "fill": (255, 145, 0, 200)},
        )
        self.trigger_line.sigPositionChanged.connect(self._on_trigger_line_dragged)
        self.trigger_line.sigPositionChanged.connect(self._update_trigger_plot_label)
        self._update_trigger_plot_label()
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
                padding: 2px 6px;
            }
        """)
        meas_layout = QtWidgets.QHBoxLayout(self.measurements_box)
        meas_layout.setContentsMargins(6, 2, 6, 2)
        meas_layout.setSpacing(8)

        # Selector de canal para medición
        meas_title_frame = QtWidgets.QFrame()
        meas_title_frame.setStyleSheet("border: none; background: transparent;")
        mtf_layout = QtWidgets.QVBoxLayout(meas_title_frame)
        mtf_layout.setContentsMargins(2, 1, 2, 1)
        mtf_layout.setSpacing(2)
        lbl_m1 = QtWidgets.QLabel("Medición")
        lbl_m1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        meas_title_frame.setFixedWidth(94)
        lbl_m1.setStyleSheet("font-size: 12px; font-weight: 800; color: #8f98a8; letter-spacing: 0.5px;")
        
        self.meas_channel_combo = GeneratorComboBox()
        self.meas_channel_combo.setProperty("centerInWholeBox", True)
        self.meas_channel_combo.setProperty("selectedTextColor", self.channel_colors.get("CH1", "#00e5ff"))
        popup = QtWidgets.QListView(self.meas_channel_combo)
        popup.setItemDelegate(NeutralMeasurementDelegate(self.config_bits_combo.view(), popup))
        popup.setUniformItemSizes(True)
        popup.setSpacing(0)

        popup.setStyleSheet("QListView {background-color:#1a1d24; color:#ffffff; border:1px solid #323946;} QListView::item {background-color:#1a1d24; color:#ffffff; padding:4px 8px;} QListView::item:selected {background-color:#323946; color:#ffffff;}")
        self.meas_channel_combo.setView(popup)
        self.meas_channel_combo.addItems(["CH1", "CH2", "FILTER"])
        self.meas_channel_combo.setCurrentText("CH1")
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
        card_extra, val_extra = self._create_meas_card("", "#55dfc4")
        meas_layout.addWidget(card_extra, 1)
        card_extra.hide()
        self._measurement_cards = [card_vmax, card_vmin, card_vpp, card_vrms, card_vavg, card_freq, card_extra]
        self._measurement_values = [self.val_vmax, self.val_vmin, self.val_vpp, self.val_vrms, self.val_vavg, self.val_freq, val_extra]

        left_layout.addWidget(self.measurements_box)

        self.columns_panel = QtWidgets.QGroupBox("FILTRO DIGITAL")
        self.columns_panel.setStyleSheet('QGroupBox {background:#21252f;border:none;border-radius:0;margin-top:0;padding-top:0;} QLabel {background:transparent;border:none;padding:0;}')
        self.columns_layout = QtWidgets.QHBoxLayout(self.columns_panel)
        self.columns_layout.setContentsMargins(10,3,10,3)
        self.filter_source = GeneratorComboBox(); self.filter_source.addItems(['OFF','CH1','CH2','RADIO'])
        self.filter_source.setToolTip('OFF: filtro apagado, sin procesamiento. Seleccionar un canal para activarlo.')
        self.filter_source.setProperty('centerInWholeBox', True)
        self.filter_mode = GeneratorComboBox()
        for label,key in [('Low pass','lowpass'),('Band pass','bandpass'),('High pass','highpass'),('Band reject','bandstop'),('Directo','bypass')]:self.filter_mode.addItem(QtGui.QIcon(str(ROOT / f'monitor/v18/assets/filter_{key}.svg')),label,key)
        from monitor.v18.filter_presets import FILTER_PRESETS
        self.filter_preset=GeneratorComboBox();self.filter_preset.addItem('Manual',None)
        for key,(label,config) in FILTER_PRESETS.items():self.filter_preset.addItem(label,key)
        self.filter_preset.setToolTip('Aplica parámetros sin activar FILTER ni cambiar su fuente')
        self.filter_design = GeneratorComboBox()
        for label,design in [('Butterw','Butterworth'),('RC','RC'),('Bessel','Bessel'),('Cheby I','Chebyshev I'),('Cheby II','Chebyshev II'),('Elliptic','Elliptic')]:
            self.filter_design.addItem(QtGui.QIcon(str(ROOT / f'monitor/v18/assets/filter_{design.lower()}.svg')),label,design)
        self.filter_order = QtWidgets.QSpinBox();self.filter_order.setRange(1,8);self.filter_order.setValue(2)
        self.filter_order.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.filter_cut = QtWidgets.QDoubleSpinBox();self.filter_cut.setRange(1,18000);self.filter_cut.setValue(100);self.filter_cut.setDecimals(0);self.filter_cut.setSuffix(' Hz')
        self.filter_upper = QtWidgets.QDoubleSpinBox();self.filter_upper.setRange(2,19600);self.filter_upper.setValue(1000);self.filter_upper.setDecimals(0);self.filter_upper.setSuffix(' Hz')
        self.filter_design.setToolTip('Chebyshev I / Elliptic: ripple 1 dB. Chebyshev II / Elliptic: rechazo 40 dB. Bessel: corte normalizado a −3 dB.')
        self.filter_frequency_boxes={}
        self.filter_dials={}
        self.filter_value_labels={}
        for label,control in [('Fuente',self.filter_source),('Preset',self.filter_preset),('Modo',self.filter_mode),('Tipo',self.filter_design),('Orden',self.filter_order),('Low',self.filter_cut),('High',self.filter_upper)]:
            column=QtWidgets.QVBoxLayout();column.setSpacing(2);column.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            title=QtWidgets.QLabel(label.upper());title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-weight:700;font-size:9px;color:#8f98a8;background:transparent;border:none;padding:0;")
            column.addWidget(title)
            if control in (self.filter_cut,self.filter_upper):
                self.filter_frequency_boxes[control]=column
                control.setParent(self.columns_panel);control.hide()
                dial=FilterDial();dial.setRange(0,1000);dial.setFixedSize(44,44)
                self.filter_dials[control]=dial
                dial.setValue(round(1000*math.log10(control.value())/math.log10(60000)))
                dial.valueChanged.connect(lambda value,spin=control:spin.setValue(60000**(value/1000)))
                column.addWidget(dial,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
                value_label=QtWidgets.QLabel();value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                value_label.setFixedHeight(18)
                value_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
                value_label.setStyleSheet('color:#aeb8c8;background:transparent;border:none;padding:0;font-size:11px;')
                self.filter_value_labels[control]=value_label;column.addWidget(value_label)
                control.valueChanged.connect(lambda value,dial=dial: self._sync_filter_dial(dial,value))
            else:column.addWidget(control)
            self.columns_layout.addLayout(column)
            signal=control.valueChanged if isinstance(control,(QtWidgets.QSpinBox,QtWidgets.QDoubleSpinBox)) else control.currentIndexChanged
            signal.connect(self._filter_preset_changed if control is self.filter_preset else self._filter_changed)
        # Channel visibility lives on the graph, outside the filter panel.
        self.graph_channel_actions={}
        for channel in self.known_columns:
            action=QtGui.QAction(channel,self)
            action.setCheckable(True);action.setChecked(self.selected_columns.get(channel,False))
            action.toggled.connect(self._filter_view_changed);self.graph_channel_actions[channel]=action
        self._update_curve_items([name for name,checked in self.selected_columns.items() if checked])
        self.channel_checkboxes={};self.channel_color_buttons={}
        self._filter_changed()

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
        self.run_stop_btn = AcquisitionButton("▶ RUN")
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
        self.record_btn = AcquisitionButton("RECORD")
        self.record_btn.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets/record.svg')))
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
        check_icon = (ROOT / 'monitor/v18/assets/check_neutral.svg').as_posix()
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
        reset_view_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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

        self.dial_h_scale = OffsetDial()
        self.dial_h_scale.centered.connect(lambda:self._reset_view_dial("h_scale"))
        self.dial_h_scale.setRange(0, 1000)
        self.dial_h_scale.setToolTip("Ventana visible según FS: mínimo 8 muestras y máximo de al menos 4 s. Recorrido logarítmico para ajustar ventanas cortas.")
        self.dial_h_scale.setValue(500)
        self.dial_h_scale.setNotchesVisible(True)
        self.dial_h_scale.setNotchTarget(7.0)
        self.dial_h_scale.valueChanged.connect(self._on_h_scale_dial)
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
            color: #55dfc4;
        """)
        horiz_layout.addWidget(self.lbl_h_scale, 2, 0)

        lbl_h_p = QtWidgets.QLabel("POSICIÓN")
        lbl_h_p.setStyleSheet("font-weight: bold; color: #ffffff;")
        horiz_layout.addWidget(lbl_h_p, 0, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_h_pos = OffsetDial()
        self.dial_h_pos.centered.connect(lambda:self._reset_view_dial("h_pos"))
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
            color: #55dfc4;
        """)
        horiz_layout.addWidget(self.lbl_h_pos, 2, 1)

        panel_layout.addWidget(horiz_group,1)

        # 3. VERTICAL
        vert_group = QtWidgets.QGroupBox("VERTICAL")
        vert_layout = QtWidgets.QGridLayout(vert_group)

        lbl_v_s = QtWidgets.QLabel("ESCALA (V)")
        self.vertical_scale_title=lbl_v_s
        lbl_v_s.setStyleSheet("font-weight: bold; color: #ffffff;")
        vert_layout.addWidget(lbl_v_s, 0, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_v_scale = OffsetDial()
        self.dial_v_scale.centered.connect(lambda:self._reset_view_dial("v_scale"))
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
            color: #55dfc4;
        """)
        vert_layout.addWidget(self.lbl_v_scale, 2, 0)

        lbl_v_p = QtWidgets.QLabel("POSICIÓN (V)")
        self.vertical_position_title=lbl_v_p
        lbl_v_p.setStyleSheet("font-weight: bold; color: #ffffff;")
        vert_layout.addWidget(lbl_v_p, 0, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.dial_v_pos = OffsetDial()
        self.dial_v_pos.centered.connect(lambda:self._reset_view_dial("v_pos"))
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
            color: #55dfc4;
        """)
        vert_layout.addWidget(self.lbl_v_pos, 2, 1)

        panel_layout.addWidget(vert_group,1)

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

        self.trigger_checkbox = QtWidgets.QCheckBox("")
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
        trigger_column = QtWidgets.QWidget()
        trigger_column.setStyleSheet("background-color: #21252f;")
        trigger_column_layout = QtWidgets.QHBoxLayout(trigger_column)
        trigger_column_layout.setContentsMargins(0, 0, 0, 0)
        trigger_column_layout.setSpacing(0)
        trigger_column_layout.addWidget(self.trigger_checkbox, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        trigger_text = QtWidgets.QLabel("TRIGGER")
        trigger_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        trigger_text.setStyleSheet("color: #ff9100; font-weight: 800; font-size: 11px; background: transparent; border: none; padding: 0;")
        trigger_text.setBuddy(self.trigger_checkbox)
        trigger_text.mousePressEvent = lambda event: self.trigger_checkbox.click()
        trigger_column_layout.addWidget(trigger_text, 1)
        trigger_column_layout.addSpacing(14)
        act_layout.addWidget(trigger_column, 1)

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
        act_layout.addWidget(self.btn_auto_level, 1)
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
        lbl_src_tag.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl_src_tag.setStyleSheet("font-weight: 700; font-size: 9px; color: #8f98a8; background: transparent; border: none; padding: 0;")
        src_layout.addWidget(lbl_src_tag)

        self.trigger_source_combo = GeneratorComboBox()
        self.trigger_source_combo.setProperty("centerInWholeBox", True)
        self.trigger_source_combo.addItems(["CH1", "CH2", "FILTER", "RADIO"])
        self.trigger_source_combo.setCurrentText("CH1")
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
        lbl_edge_tag.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl_edge_tag.setStyleSheet("font-weight: 700; font-size: 9px; color: #8f98a8; background: transparent; border: none; padding: 0;")
        edge_layout.addWidget(lbl_edge_tag)

        self.trigger_edge_combo = GeneratorComboBox()
        self.trigger_edge_combo.setProperty("centerInWholeBox", True)
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

        # Reflow the filter controls into two columns in the former Trigger slot.
        filter_columns=[]
        while self.columns_layout.count():
            filter_columns.append(self.columns_layout.takeAt(0).layout())
        old_layout_holder=QtWidgets.QWidget()
        old_layout_holder.setLayout(self.columns_layout)
        self.columns_layout=QtWidgets.QGridLayout(self.columns_panel)
        self.columns_layout.setContentsMargins(8,8,8,8)
        self.columns_layout.setHorizontalSpacing(10);self.columns_layout.setVerticalSpacing(8)
        self.columns_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        # The preset has descriptive names; give it a full row and keep Low/High paired.
        filter_columns=[filter_columns[1]]+[column for i,column in enumerate(filter_columns) if i!=1]
        for index,column in enumerate(filter_columns):
            column.setParent(None)
            card=QtWidgets.QFrame()
            card.setStyleSheet("QFrame {background-color:#21252f;border:1px solid #2e3543;border-radius:6px;padding:2px 6px;}")
            card.setLayout(column)
            column.setContentsMargins(4,3,4,3)
            if column in self.filter_frequency_boxes.values():
                column.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
                card.setMinimumHeight(column.sizeHint().height()+2)
            self.columns_layout.addWidget(card,0,0,1,2) if index==0 else self.columns_layout.addWidget(card,1+(index-1)//2,(index-1)%2)
        old_layout_holder.deleteLater()
        self.columns_panel.setTitle('');trig_group.setTitle('')
        trig_group.setStyleSheet('QGroupBox {background:#21252f;border:none;border-radius:0;margin-top:0;padding-top:0;}')
        self.trigger_filter_tabs=QtWidgets.QTabWidget()
        self.trigger_filter_tabs.setStyleSheet('QTabWidget::pane {border:1px solid #323946;border-radius:0;background:#21252f;} QTabBar::tab {background:#1a1e26;color:#aeb8c8;padding:5px 6px;border:1px solid #323946;} QTabBar::tab:selected {background:#2b333f;color:#55dfc4;}')
        self.trigger_filter_tabs.addTab(trig_group,'Trigger')
        self.trigger_filter_tabs.addTab(self.columns_panel,'Filtro')
        self._build_radio_panel()
        self.trigger_filter_tabs.addTab(self.radio_panel,'Radio')
        from monitor.v18.scope_cursors import ScopeCursors
        self.scope_cursors=ScopeCursors(self,GeneratorComboBox)
        self.trigger_filter_tabs.insertTab(1,self.scope_cursors,'Cursor')
        # Match the Trigger page's top inset across all instrument tabs.
        tab_top_margin=trig_layout.contentsMargins().top()
        for page in (self.scope_cursors,self.columns_panel,self.radio_panel):
            page_layout=page.layout()
            margins=page_layout.contentsMargins()
            page_layout.setContentsMargins(margins.left(),tab_top_margin,margins.right(),margins.bottom())
        for index,icon in enumerate(('tab_trigger','tab_cursor','tab_filter','tab_radio')):
            self.trigger_filter_tabs.setTabIcon(index,QtGui.QIcon(str(ROOT/'monitor/v18/assets'/f'{icon}.svg')))
        self.trigger_filter_tabs.setIconSize(QtCore.QSize(12,12))
        self.trigger_filter_tabs.currentChanged.connect(self._resize_trigger_filter_tabs)
        self._resize_trigger_filter_tabs()
        panel_layout.addWidget(self.trigger_filter_tabs)
        panel_layout.addStretch()

        main_h_layout.addWidget(panel_widget, 1)

    def _resize_trigger_filter_tabs(self,*args):
        if not hasattr(self,'_trigger_filter_height'):
            pages=[self.trigger_filter_tabs.widget(i) for i in range(self.trigger_filter_tabs.count())]
            self._trigger_filter_height=max(page.minimumSizeHint().height() for page in pages)+self.trigger_filter_tabs.tabBar().sizeHint().height()+4
        self.trigger_filter_tabs.setFixedHeight(self._trigger_filter_height)

    def _build_radio_panel(self):
        self.radio_panel = QtWidgets.QWidget()
        self.radio_panel.setObjectName('radioPanel')
        self.radio_panel.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground,True)
        self.radio_panel.setStyleSheet('QWidget#radioPanel {background-color:#21252f;}')
        layout = QtWidgets.QVBoxLayout(self.radio_panel)
        layout.setContentsMargins(6,4,6,4);layout.setSpacing(4)
        header_widget=QtWidgets.QWidget()
        header_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        header=QtWidgets.QHBoxLayout(header_widget)
        header.setContentsMargins(0,0,0,0);header.setSpacing(0)
        self.radio_enabled = QtWidgets.QPushButton('▶')
        self.radio_enabled.setToolTip('Iniciar RADIO')
        self.radio_enabled.setAccessibleName('Iniciar o detener RADIO')
        self.radio_enabled.setCheckable(True)
        header.addWidget(self.radio_enabled,1)
        badge=QtWidgets.QLabel('AM CH1 · ADC8/10/12/14')
        self.radio_input_badge=badge
        badge.setStyleSheet('color:#55dfc4;background:transparent;font-size:9px;')
        badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        badge.setFixedHeight(18)
        badge.setMinimumWidth(0)
        badge.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.radio_scan_button=QtWidgets.QPushButton('')
        self.radio_scan_button.setAccessibleName('Scan')
        scan_icon=QtGui.QPixmap(16,16);scan_icon.fill(QtCore.Qt.GlobalColor.transparent)
        painter=QtGui.QPainter(scan_icon);painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor('#ff9d36'),2))
        painter.drawEllipse(2,2,8,8);painter.drawLine(10,10,14,14);painter.end()
        self.radio_scan_button.setIcon(QtGui.QIcon(scan_icon))
        for button in (self.radio_enabled,self.radio_scan_button):
            button.setFixedHeight(CONTROL_HEIGHT)
            button.setMinimumWidth(0)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.radio_scan_button.setToolTip('Buscar candidatos RF una vez; independiente de la FFT visual')
        header.addWidget(self.radio_scan_button,1)
        self.radio_candidates=[]
        self._radio_scan_executor=None;self._radio_scan_future=None;self._radio_scan_generation=0
        self._radio_scan_timer=QtCore.QTimer(self);self._radio_scan_timer.setInterval(50)
        self._radio_scan_timer.timeout.connect(self._radio_scan_finished)
        self.radio_scan_button.clicked.connect(self._radio_scan)
        self.radio_frequency = QtWidgets.QDoubleSpinBox()
        self.radio_frequency.setRange(5,600);self.radio_frequency.setValue(550)
        self.radio_frequency.setDecimals(3);self.radio_frequency.setSuffix(' kHz')
        self.radio_frequency.setSingleStep(.1);self.radio_frequency.setKeyboardTracking(False)
        self.radio_frequency.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.radio_frequency.setParent(self.radio_panel);self.radio_frequency.hide()
        self.radio_frequency_text=QtWidgets.QWidget()
        self.radio_frequency_text.setStyleSheet('background:#10151d;border:1px solid #3a4659;border-radius:7px;padding:0;')
        frequency_layout=QtWidgets.QHBoxLayout(self.radio_frequency_text)
        frequency_layout.setContentsMargins(7,5,4,5);frequency_layout.setSpacing(2)
        self.radio_frequency_led=QtWidgets.QLCDNumber(5)
        self.radio_frequency_led.setSegmentStyle(QtWidgets.QLCDNumber.SegmentStyle.Flat)
        self.radio_frequency_led.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.radio_frequency_led.setSmallDecimalPoint(True)
        self.radio_frequency_led.setMinimumWidth(0)
        self.radio_frequency_led.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Expanding)
        self.radio_frequency_led.setStyleSheet('color:#55dfc4;background:transparent;border:none;padding:0;margin:0;')
        self.radio_frequency_led.display('550.0')
        frequency_layout.addWidget(self.radio_frequency_led,1)
        unit=QtWidgets.QLabel('kHz')
        unit.setFixedWidth(22)
        unit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        unit.setStyleSheet('color:#8f98a8;background:transparent;border:none;font-size:10px;padding:0;')
        frequency_layout.addWidget(unit)

        self.radio_output_rate = GeneratorComboBox()
        for rate in (20000,40000,48000):self.radio_output_rate.addItem(f'{rate//1000} kHz',rate)
        self.radio_output_rate.setCurrentIndex(self.radio_output_rate.findData(40000))
        self.radio_output_rate.setProperty('centerInWholeBox',True)
        self.radio_frequency_dial=InstrumentDial()
        self.radio_frequency_dial.setProperty('radioStyle',True)
        self.radio_frequency_dial.setRange(5000,600000)
        self.radio_frequency_dial.setSingleStep(100);self.radio_frequency_dial.setPageStep(1000)
        self.radio_frequency_dial.setValue(550000)
        self.radio_frequency_dial.setToolTip('Sintonía AM · rueda: 100 Hz · flechas: picos de FFT RF')
        self.radio_peak_previous=QtWidgets.QPushButton('<<')
        self.radio_peak_next=QtWidgets.QPushButton('>>')
        self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        self.radio_peak_previous.setToolTip('Candidato anterior de la última búsqueda Scan')
        self.radio_peak_next.setToolTip('Candidato siguiente de la última búsqueda Scan')
        header.insertWidget(1,self.radio_peak_previous,1)
        header.insertWidget(2,self.radio_peak_next,1)
        for button in (self.radio_enabled,self.radio_peak_previous,self.radio_peak_next,self.radio_scan_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            button.setStyleSheet('padding:0;margin:0;font-size:12px;border-radius:0;')

        scan_options=QtWidgets.QVBoxLayout()
        scan_options.setSpacing(4)
        threshold_label=QtWidgets.QLabel('Umbral')
        threshold_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        threshold_label.setStyleSheet('color:#8f98a8;background:transparent;border:none;padding:0;')
        scan_options.addWidget(threshold_label)
        self.radio_scan_threshold=GeneratorComboBox()
        for threshold in (5,10,20,40,60):self.radio_scan_threshold.addItem(f'{threshold} dB',threshold)
        self.radio_scan_threshold.setCurrentIndex(self.radio_scan_threshold.findData(10))
        self.radio_scan_threshold.setProperty('centerInWholeBox',True)
        self.radio_scan_threshold.setToolTip('Exceso mínimo sobre el piso de ruido local. Mayor valor reduce candidatos; no identifica una estación AM.')
        self.radio_scan_strict=QtWidgets.QCheckBox('3/3')
        check_icon=(ROOT/'monitor/v18/assets/check_neutral.svg').as_posix()
        self.radio_scan_strict.setStyleSheet(f'QCheckBox {{background:transparent;border:none;spacing:6px;}} QCheckBox::indicator {{width:14px;height:14px;border:1px solid #737d8d;border-radius:3px;background:#171920;}} QCheckBox::indicator:checked {{image:url("{check_icon}");}} QCheckBox::indicator:unchecked {{image:none;}}')
        self.radio_scan_strict.setToolTip('Exigir detección en los tres bloques, en lugar de dos')
        self.radio_scan_threshold.setFixedHeight(CONTROL_HEIGHT)
        self.radio_scan_threshold.setMinimumWidth(0)
        self.radio_scan_threshold.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        scan_options.addWidget(self.radio_scan_threshold)
        scan_options.addWidget(self.radio_scan_strict,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
        grid=QtWidgets.QGridLayout();grid.setSpacing(10)
        self.radio_controls_grid=grid
        self.radio_control_cards=[]
        self.radio_us=QtWidgets.QToolButton()
        self.radio_us.setCheckable(True)
        self.radio_us.setFixedSize(12,12)
        self.radio_us.setAccessibleName('US · undersampling')
        self.radio_us.setStyleSheet('QToolButton {padding:0;border:1px solid #657080;border-radius:6px;background:qradialgradient(cx:.35,cy:.3,radius:.8,stop:0 #536071,stop:.55 #2b3440,stop:1 #151b23);} QToolButton:checked {border-color:#3fa591;background:qradialgradient(cx:.35,cy:.3,radius:.8,stop:0 #4dcbB2,stop:.3 #3fa591,stop:.7 #3fa591,stop:1 #303b48);} QToolButton:hover {border-color:#8b98aa;} QToolButton:disabled {background:#34434a;border-color:#45545c;}')
        self.radio_us.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.radio_us.setToolTip('US · dial directo y segunda zona Nyquist. Scan compara tres tasas para estimar RF. Requiere selección analógica de banda; otras zonas se superponen.')
        self.radio_us.toggled.connect(self._radio_us_changed)
        self.radio_bandwidth=GeneratorComboBox()
        self.radio_bandwidth.setProperty('centerInWholeBox',True)
        for width in (6000,8000,10000,12000,20000):self.radio_bandwidth.addItem(f'{width//1000} kHz',width)
        self.radio_bandwidth.setCurrentIndex(self.radio_bandwidth.findData(8000))
        self.radio_bandwidth.setToolTip('Ancho total del canal RF: cada banda lateral ocupa la mitad. No cambia FS SALIDA.')
        for column,(title,dial,control) in enumerate((
                ('SINTONÍA',self.radio_frequency_dial,self.radio_frequency_text),
                ('FS SALIDA',None,self.radio_output_rate))):
            card=QtWidgets.QFrame()
            card.setMinimumWidth(0)
            card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
            self.radio_control_cards.append(card)
            card.setStyleSheet('QFrame {background:#21252f;border:1px solid #2e3543;border-radius:6px;padding:2px 6px;}')
            box=QtWidgets.QVBoxLayout(card);box.setContentsMargins(4,3,4,3);box.setSpacing(4)
            label=QtWidgets.QLabel(title);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet('font-weight:700;font-size:9px;color:#8f98a8;background:transparent;border:none;padding:0;')
            if dial is not None:dial.setFixedSize(56,56)
            control.setFixedHeight(CONTROL_HEIGHT);control.setMinimumWidth(0)
            control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            if dial is not None:
                heading=QtWidgets.QHBoxLayout()
                heading.setContentsMargins(0,0,0,0);heading.setSpacing(3)
                us_label=QtWidgets.QLabel('US')
                us_label.setStyleSheet('font-size:9px;color:#8f98a8;background:transparent;border:none;padding:0;')
                heading.addWidget(self.radio_us);heading.addWidget(us_label)
                heading.addWidget(label,1)
                box.addLayout(heading)
                box.addWidget(dial,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
            else:box.addWidget(label)
            if dial is None:
                label.setText('FS / BANDA RF')
                rates=QtWidgets.QHBoxLayout();rates.setContentsMargins(0,0,0,0);rates.setSpacing(4)
                self.radio_bandwidth.setFixedHeight(CONTROL_HEIGHT)
                self.radio_bandwidth.setMinimumWidth(0)
                self.radio_bandwidth.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
                rates.addWidget(control,1);rates.addWidget(self.radio_bandwidth,1)
                box.addLayout(rates)
                box.addLayout(scan_options)
                box.addStretch()
            else:
                box.addWidget(control)
                box.addWidget(header_widget)
            grid.addWidget(card,0,column);grid.setColumnStretch(column,1)
        self.radio_gain=GeneratorValueSpinBox()
        self.radio_gain.setRange(1,80);self.radio_gain.setDecimals(1)
        self.radio_gain.setSingleStep(.5);self.radio_gain.setValue(10)
        self.radio_gain.setSuffix(' ×')
        self.radio_gain.setStyleSheet('QDoubleSpinBox {background:#21252f;border:1px solid #3a4150;border-radius:6px;}')
        self.radio_gain.setToolTip('Ganancia digital del audio demodulado; también amplifica el ruido. No cambia el ADC.')
        self.radio_gain_dial=InstrumentDial();self.radio_gain_dial.setRange(10,800)
        self.radio_gain_dial.setValue(100);self.radio_gain_dial.setFixedSize(56,56)
        self.radio_gain_dial.setProperty('redColor',True)
        self.radio_gain_dial.setStyleSheet('background:transparent;border:none;')
        self.radio_gain_dial.valueChanged.connect(lambda value:self.radio_gain.setValue(value/10))
        self.radio_gain.valueChanged.connect(self._sync_radio_gain_dial)
        self.radio_auto_gain=QtWidgets.QPushButton('  Manual');self.radio_auto_gain.setCheckable(True)
        gain_mode_icons={False:QtGui.QIcon(str(ROOT/'monitor/v18/assets/instrument_manual.svg')),
                         True:QtGui.QIcon(str(ROOT/'monitor/v18/assets/gain_auto.svg'))}
        self.radio_auto_gain.setIconSize(QtCore.QSize(18,18))
        self.radio_auto_gain.setIcon(gain_mode_icons[False])
        self.radio_auto_gain.toggled.connect(lambda checked:self.radio_auto_gain.setIcon(gain_mode_icons[checked]))
        self.radio_auto_gain.setAccessibleName('Auto gain')
        self.radio_auto_gain.setToolTip('Ajuste gradual: sube 1 dB/s y baja 2 dB/s; reducción inmediata ante clipping fuerte. Objetivo 0,5–2,8 V. También amplifica ruido.')
        self.radio_auto_gain.toggled.connect(lambda checked:self.radio_auto_gain.setText('  Auto' if checked else '  Manual'))
        self.radio_auto_gain.toggled.connect(lambda _:setattr(self,'_radio_auto_gain_at',0.))
        self.radio_offset=VoltageSpinBox()
        self.radio_offset.setRange(-3.3,3.3);self.radio_offset.setDecimals(2)
        self.radio_offset.setSingleStep(.01);self.radio_offset.setSuffix(' V');self.radio_offset.setValue(1.65)
        self.radio_offset.setToolTip('Offset digital sumado después de la ganancia. No cambia el offset del generador.')
        for control in (self.radio_gain,self.radio_offset):
            control.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            control.setKeyboardTracking(False);control.setFixedHeight(CONTROL_HEIGHT)
            control.setMinimumWidth(0)
            control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.radio_output_panel.offset_box.insertWidget(2,self.radio_offset)
        gain_box=QtWidgets.QVBoxLayout();gain_box.setSpacing(4)
        gain_label=QtWidgets.QLabel('Gain');gain_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        gain_label.setStyleSheet('color:#8f98a8;background:transparent;border:none;padding:0;')
        gain_box.addWidget(gain_label);gain_box.addWidget(self.radio_gain)
        compact=QtWidgets.QHBoxLayout();compact.setContentsMargins(0,0,0,0);compact.setSpacing(10)
        compact.addWidget(self.radio_gain_dial);compact.addLayout(gain_box,1)
        grid.addLayout(compact,1,0)
        mode_box=QtWidgets.QVBoxLayout();mode_box.setSpacing(4)
        mode_label=QtWidgets.QLabel('Gain · modo');mode_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        mode_label.setStyleSheet('color:#8f98a8;background:transparent;border:none;padding:0;')
        mode_box.addWidget(mode_label);mode_box.addWidget(self.radio_auto_gain)
        self.radio_auto_gain.setFixedHeight(CONTROL_HEIGHT)
        grid.addLayout(mode_box,1,1)
        layout.addLayout(grid)
        layout.addWidget(badge)
        self.radio_status = SingleLineStatusLabel('RADIO · mono · salida 40 kHz')
        self.radio_status.setWordWrap(False)
        self.radio_status.setFixedHeight(CONTROL_HEIGHT)
        self.radio_status.setMinimumWidth(0)
        self.radio_status.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.radio_status.setStyleSheet('color:#aeb8c8;background:#171920;border:1px solid #323946;border-radius:6px;padding:6px;font-size:11px;')
        layout.addWidget(self.radio_status);layout.addStretch()
        self.radio_frequency_dial.valueChanged.connect(lambda value:self.radio_frequency.setValue(value/1000))
        self.radio_frequency.valueChanged.connect(self._sync_radio_dials)
        self.radio_peak_previous.clicked.connect(lambda:self._radio_select_peak(-1))
        self.radio_peak_next.clicked.connect(lambda:self._radio_select_peak(1))
        self.radio_enabled.toggled.connect(self._radio_changed)
        self.radio_frequency.valueChanged.connect(self._radio_changed)
        self.radio_output_rate.currentIndexChanged.connect(self._radio_changed)
        self.radio_bandwidth.currentIndexChanged.connect(self._radio_bandwidth_changed)
        self.radio_gain.valueChanged.connect(self._radio_levels_changed)
        self.radio_offset.valueChanged.connect(self._radio_levels_changed)

    def _sync_radio_input_controls(self):
        config=self.applied_configuration
        self.radio_frequency_dial.setProperty('radioExtended',self.radio_us.isChecked())
        self.radio_frequency_dial.setProperty('radioNyquist',config.actual_rate/2)
        self.radio_frequency_dial.update()
        self.radio_input_badge.setText(f'AM CH1 · ADC{config.bits} · {number(config.actual_rate/1e6, ".4f")} MHz')
        if radio_input_supported(config):
            minimum,maximum=tuning_bounds(config.actual_rate,self.radio_bandwidth.currentData(),self.radio_us.isChecked())
            if maximum<minimum:
                self.radio_status.setText('Banda RF demasiado ancha para esta FS; reducir banda o aumentar FS.')
                return
            with QtCore.QSignalBlocker(self.radio_frequency),QtCore.QSignalBlocker(self.radio_frequency_dial):
                self.radio_frequency.setRange(minimum/1000,maximum/1000)
                self.radio_frequency_dial.setRange(minimum,maximum)
            self._sync_radio_dials()
            self.radio_frequency_dial.setToolTip(f'Sintonía AM · {minimum/1000:g}–{maximum/1000:g} kHz · rueda: 100 Hz · flechas: candidatos Scan')

    def _sync_radio_dials(self,*args):
        with QtCore.QSignalBlocker(self.radio_frequency_dial):
            self.radio_frequency_dial.setValue(round(self.radio_frequency.value()*1000))
        self.radio_frequency_led.display(f'{self.radio_frequency.value():.1f}')
        self.radio_frequency_text.setToolTip(f'{number(self.radio_frequency.value(), ".3f")} kHz')
        if hasattr(self,'spectral'):self.spectral.refresh_radio_overlay()
        self._update_radio_bandwidth_suggestion()

    def _update_radio_bandwidth_suggestion(self):
        combo=self.radio_bandwidth
        width=combo.currentData()
        with QtCore.QSignalBlocker(combo):
            combo.setCurrentIndex(combo.findData(width))
            while combo.count()>5:combo.removeItem(5)
            tolerance=max(100,self.applied_configuration.actual_rate/65536*2)
            current=self.radio_frequency.value()*1000
            candidate=next((p for p in self.radio_candidates if abs(p['frequency']-current)<=tolerance),None)
            suggested=candidate.get('suggested_bandwidth') if candidate else None
            if suggested is not None:
                combo.addItem(f'Sugerida: {suggested//1000} kHz',suggested)
        combo.setToolTip('Banda RF total. Scan puede sugerir un ancho según bandas laterales persistentes; elegir Sugerida para aplicar. Es una estimación del contenido observado, no del ancho de la emisora.')

    def _radio_us_changed(self,*args):
        self.radio_candidates=[];self._radio_scan_generation+=1
        self.radio_frequency_dial.setPeakFrequencies(())
        self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        self._sync_radio_input_controls()
        self._radio_changed()

    def _radio_bandwidth_changed(self,*args):
        self.radio_candidates=[];self._radio_scan_generation+=1
        self.radio_frequency_dial.setPeakFrequencies(())
        self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        self._sync_radio_input_controls()
        self._radio_changed()

    def _set_radio_scan_playback(self,playing):
        """Pause/resume DSP without treating Scan as a user configuration edit."""
        with QtCore.QSignalBlocker(self.radio_enabled):
            self.radio_enabled.setChecked(playing)
        self._radio_display_enabled=playing
        self.radio_enabled.setText('■' if playing else '▶')
        self.radio_enabled.setToolTip('Detener RADIO' if playing else 'Iniciar RADIO')
        self.radio_stream=None;self.radio_key=None;self.radio_filter.reset()
        self._reset_processing_settings()

    def _pause_a0_for_radio_scan(self):
        panel=self.radio_output_panel
        self._radio_scan_a0=dict(worker=self.serial_worker,volume=panel.volume.value(),
            input=panel.input_source.currentText(),rate=self.radio_output_rate.currentData(),
            enabled=panel.isEnabled(),deadline=time.monotonic()+8,waiting=True,source=panel.source,stop_sent=False)
        panel.setEnabled(False)
        source=panel.source
        if source is not None:
            self._radio_scan_a0['fade_target']=source.fade_out()
        else:
            panel.stop(reason='Pausa A0 para Scan');self._radio_scan_a0['stop_sent']=True
        self._auto_apply_timer.stop()
        timer=QtCore.QTimer(self);timer.setInterval(50)
        self._radio_scan_a0_timer=timer
        timer.timeout.connect(self._wait_a0_for_radio_scan);timer.start()
        self.radio_status.setText('Scan · pausando A0…')

    def _wait_a0_for_radio_scan(self):
        context=getattr(self,'_radio_scan_a0',None)
        if context is None:return
        if self.serial_worker is not context['worker'] or time.monotonic()>context['deadline']:
            self._finish_radio_scan_a0(False)
            self.radio_status.setText('Scan cancelado · no se confirmó Stop de A0.');return
        if not context['stop_sent']:
            source=context['source']
            if source.error or self.radio_output_panel.source is not source:
                self._finish_radio_scan_a0(False)
                self.radio_status.setText('Scan cancelado · salida A0 interrumpida.');return
            if source.played<context['fade_target']:return
            self.radio_output_panel.stop(reason='Pausa suave A0 para Scan')
            context['stop_sent']=True
            return
        if self._wav_active or self.output_pending:return
        self._radio_scan_a0_timer.stop();context['waiting']=False
        self._auto_apply_timer.stop()
        self._radio_scan()
        if self._radio_scan_future is None and not getattr(getattr(self,'_radio_multiscan',None),'active',False):
            self._finish_radio_scan_a0(True)

    def _finish_radio_scan_a0(self,success):
        context=getattr(self,'_radio_scan_a0',None)
        if context is None:return
        self._radio_scan_a0=None;self._radio_scan_a0_timer.stop()
        panel=self.radio_output_panel;panel.setEnabled(context['enabled'])
        if (not success and not context['stop_sent'] and context['source'] is not None
                and panel.source is context['source']):
            panel.stop(reason='Scan cancelado: pausa A0 incompleta')
        if (success and self.serial_worker is context['worker'] and not self._wav_active
                and self.generator_mode.currentIndex()==7 and self.radio_enabled.isChecked()
                and self.radio_output_rate.currentData()==context['rate']
                and panel.input_source.currentText()==context['input']):
            panel.volume.setValue(context['volume']);panel.scan_fade_in=True;panel.toggle()

    def _radio_scan(self):
        context=getattr(self,'_radio_scan_a0',None)
        if context is not None and context['waiting']:return
        if self.radio_output_panel.source is not None:
            self._pause_a0_for_radio_scan();return
        from concurrent.futures import ThreadPoolExecutor
        from monitor.v18.radio_scan import SCAN_SIZE, SCAN_BLOCKS, scan_carriers
        if self.radio_us.isChecked():
            if self._radio_scan_executor is None:self._radio_scan_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='radio-scan')
            from monitor.v18.radio_multiscan import MultirateScan
            if not hasattr(self,'_radio_multiscan'):self._radio_multiscan=MultirateScan(self)
            self._radio_multiscan.start();return
        if self._radio_scan_future is not None:return
        if self._wav_active or self._wav_preparing:
            self.radio_status.setText('Scan · detener salida A0 antes de escanear.');return
        self.radio_candidates=[]
        self._update_radio_bandwidth_suggestion()
        self.spectral.refresh_radio_overlay()
        self.radio_frequency_dial.setPeakFrequencies(())
        self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        config=self.applied_configuration
        count=SCAN_SIZE*SCAN_BLOCKS
        history=self.series.get('CH1');times=self.series.get('Tiempo (us)')
        if self.demo_mode or not radio_input_supported(config) or history is None or len(history)<count:
            self.radio_status.setText(f'Scan · adquisición ≥20 kHz y esperar {count:,} muestras.');return
        if times is None or len(times)<count or np.any(np.abs(np.diff(times[-count:])-config.dt_us)>.01):
            self.radio_status.setText('Scan · bloque RF discontinuo.');return
        values=history[-count:]
        if self.sample_counter-count<getattr(self,'_radio_scan_not_before_sample',-1):
            self.radio_status.setText('Scan · esperar tres bloques nuevos tras el cambio de generador.');return
        if self._radio_scan_executor is None:self._radio_scan_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='radio-scan')
        self._radio_scan_resume=self.radio_enabled.isChecked()
        self._set_radio_scan_playback(False)
        self._radio_scan_job_generation=self._radio_scan_generation
        low,high=tuning_bounds(config.actual_rate,self.radio_bandwidth.currentData(),self.radio_us.isChecked())
        self._radio_scan_band=f'{"US Z2 RF" if self.radio_us.isChecked() else "RF"} {low/1000:g}–{high/1000:g} kHz'
        self._radio_scan_future=self._radio_scan_executor.submit(scan_carriers,values,config.actual_rate,
            self.radio_scan_threshold.currentData(),3 if self.radio_scan_strict.isChecked() else 2,self.radio_bandwidth.currentData())
        self.radio_scan_button.setEnabled(False);self.radio_scan_button.setText('')
        self.radio_status.setText(f'Scan {self._radio_scan_band} · 3 × 65.536 muestras · Hann')
        self._radio_scan_timer.start()

    def _radio_scan_finished(self):
        future=self._radio_scan_future
        if future is None or not future.done():return
        self._radio_scan_timer.stop();self._radio_scan_future=None
        self.radio_scan_button.setEnabled(True);self.radio_scan_button.setText('')
        resume=getattr(self,'_radio_scan_resume',False)
        self._radio_scan_resume=False
        if resume and self._radio_scan_job_generation==self._radio_scan_generation:self._set_radio_scan_playback(True)
        try:peaks=future.result()
        except Exception as exc:
            self.radio_status.setText(f'Scan falló · {exc}');self._finish_radio_scan_a0(False);return
        if self._radio_scan_job_generation!=self._radio_scan_generation:
            self.radio_status.setText('Scan descartado · adquisición reiniciada.');self._finish_radio_scan_a0(False);return
        self._publish_radio_scan(peaks)
        self._finish_radio_scan_a0(True)

    def _publish_radio_scan(self,peaks):
        self.radio_candidates=peaks
        self._update_radio_bandwidth_suggestion()
        self.spectral.refresh_radio_overlay()
        self.radio_frequency_dial.setPeakFrequencies((p["frequency"] for p in peaks),(p["dbfs"] for p in peaks))
        self.radio_scan_button.setToolTip('\n'.join(f'{p["frequency"]/1000:.3f} kHz · {p.get("confidence","candidato")} · {p["dbfs"]:.1f} dBFS · piso +{p["above_noise_db"]:.1f} dB · {p["persistence"]}/3' for p in peaks) or 'Sin candidatos; ajustar umbral y repetir Scan')
        self.radio_peak_previous.setEnabled(bool(peaks));self.radio_peak_next.setEnabled(bool(peaks))
        self.radio_status.setText(f'Scan {getattr(self,"_radio_scan_band","RF")} · {len(peaks)} candidatos' if peaks else 'Scan · sin candidatos RF sobre el ruido local.')

    def _radio_select_peak(self,direction):
        peaks=[p['frequency'] for p in self.radio_candidates]
        if not peaks:
            self.radio_status.setText('Pulsar Scan para buscar candidatos RF.');return
        current=self.radio_frequency.value()*1000
        tolerance=max(1,self.applied_configuration.actual_rate/65536/2)
        candidates=[f for f in peaks if (f-current)*direction>tolerance]
        selected=(min(candidates) if direction>0 else max(candidates)) if candidates else (peaks[0] if direction>0 else peaks[-1])
        self.radio_frequency.setValue(selected/1000)
        candidate=next(p for p in self.radio_candidates if p['frequency']==selected)
        self.radio_status.setText(f'{number(self.radio_frequency.value(), ".1f")} kHz · '
            f'{candidate.get("confidence","candidato")} · {candidate["dbfs"]:.1f} dBFS · piso +{candidate["above_noise_db"]:.1f} dB · {candidate["persistence"]}/3')

    def _radio_changed(self,*args):
        self.radio_enabled.setText('■' if self.radio_enabled.isChecked() else '▶')
        self.radio_enabled.setToolTip('Detener RADIO' if self.radio_enabled.isChecked() else 'Iniciar RADIO')
        starting=self.radio_enabled.isChecked() and not getattr(self,'_radio_display_enabled',False)
        self._radio_display_enabled=self.radio_enabled.isChecked()
        if starting and hasattr(self,'graph_channel_actions'):
            self.graph_channel_actions['RADIO'].setChecked(True)
            if hasattr(self,'spectral') and not any(c.currentText()=='CH1' for c in self.spectral.channels):
                self.spectral.channels[0].setCurrentText('RADIO')
        if hasattr(self,'radio_output_panel') and hasattr(self,'radio_frequency'):self.radio_output_panel.radio_changed()
        self.radio_stream = None;self.radio_key = None;self.radio_filter.reset()
        self.radio_status.setText('RADIO esperando muestras de CH1' if self.radio_enabled.isChecked() else 'RADIO apagada')
        self._preserve_rf_history=True
        try:self._filter_changed()
        finally:self._preserve_rf_history=False

    def _radio_levels_changed(self,*args):
        # Automatic level corrections retain the rolling FFT/audio window.
        # Manual edits still begin a fresh display scale.
        if not getattr(self,'_radio_auto_adjusting',False):
            self.radio_stream=None;self.radio_key=None
            self.radio_filter.reset()
            if hasattr(self,'spectral'):self.spectral.reset()
        self._reset_processing_settings(levels_only=True)

    def _sync_radio_gain_dial(self,value):
        with QtCore.QSignalBlocker(self.radio_gain_dial):self.radio_gain_dial.setValue(round(value*10))
        if hasattr(self,'radio_auto_gain') and not getattr(self,'_radio_auto_adjusting',False):self.radio_auto_gain.setChecked(False)

    def _update_radio_auto_gain(self,result,now):
        if not self.radio_auto_gain.isChecked() or not self.radio_enabled.isChecked():return
        settings=result['settings']
        if result['generation']!=self._processing_generation:return
        from monitor.v18.radio_autogain import target_gain,UPDATE_SECONDS
        if not getattr(self,'_radio_auto_gain_at',0.):self._radio_auto_gain_at=now-.2
        normal=now-getattr(self,'_radio_auto_measure_at',0.)>=UPDATE_SECONDS
        if normal:self._radio_auto_measure_at=now
        value=target_gain(result['audio'],settings.radio_gain,settings.radio_offset,
                          elapsed=max(0.,now-self._radio_auto_gain_at),allow_normal=normal)
        if value is not None:
            self._radio_auto_adjusting=True
            try:
                self.radio_gain.setValue(value)
                self._radio_auto_gain_at=now
            finally:self._radio_auto_adjusting=False

    def _filter_sample_rate(self):
        if self.filter_source.currentText() == 'RADIO':
            return self.radio_output_rate.currentData() if hasattr(self,'radio_output_rate') else 20000
        return 2500 if self.demo_mode else getattr(self,'applied_configuration',Configuration(14,40000)).actual_rate

    def _processing_settings(self):
        return ProcessingSettings(generation=self._processing_generation,
            continuity_epoch=self._audio_continuity_epoch,
            acquisition=self.applied_configuration, filter=self.filter_config,
            radio_enabled=hasattr(self,'radio_enabled') and self.radio_enabled.isChecked(),
            radio_frequency=self.radio_frequency.value()*1000 if hasattr(self,'radio_frequency') else 550000,
            audio_rate=self.radio_output_rate.currentData() if hasattr(self,'radio_output_rate') else 40000,
            radio_gain=self.radio_gain.value() if hasattr(self,'radio_gain') else 10.0,
            radio_offset=self.radio_offset.value() if hasattr(self,'radio_offset') else 1.65,
            radio_bandwidth=self.radio_bandwidth.currentData() if hasattr(self,'radio_bandwidth') else 8000.,
            radio_undersampling=hasattr(self,'radio_us') and self.radio_us.isChecked())

    def _reset_processing_settings(self, *, levels_only=False):
        self._processing_generation += 1
        if not levels_only:self._audio_continuity_epoch += 1
        worker = getattr(self,'serial_worker',None)
        if worker is not None:
            worker.set_processing_settings(self._processing_settings())

    def _accept_processed_radio(self, result):
        self.radio_output_panel.observe_audio(result)
        if result['radio_status'] is not None:
            self.radio_stream=None;self.radio_key=None
            self.radio_status.setText(result['radio_status'])
        audio=result['audio']
        if audio is None:return
        key=result['radio_key']
        if self.radio_key!=key or self.radio_stream is None:
            self.radio_stream=RadioTimeline(key[2]);self.radio_key=key
        self.radio_stream.append(audio,result['audio_filter'],result.get('audio_first_time_us'))
        now=time.monotonic()
        if now-getattr(self,'_radio_status_updated',0)>.1:
            self._radio_status_updated=now
            self.radio_status.setText((f'US · RF {key[1]/1000:g} · alias {abs((key[1]+key[0]/2)%key[0]-key[0]/2)/1000:g} kHz · ' if self.radio_us.isChecked() else '')+f'RADIO {key[2]/1000:g} kHz · {self.radio_stream.counter} muestras')
        self._update_radio_auto_gain(result,now)

    def _process_radio(self,columns):
        if not hasattr(self,'radio_enabled') or not self.radio_enabled.isChecked():return
        config=self.applied_configuration
        if self.demo_mode or not radio_input_supported(config):
            self.radio_stream=None;self.radio_key=None
            self.radio_status.setText('RADIO requiere adquisición de al menos 20 kHz (entrada CH1).')
            return
        key=(config.actual_rate,self.radio_frequency.value()*1000,self.radio_output_rate.currentData(),self.radio_bandwidth.currentData())
        try:
            if self.radio_key!=key:
                self.radio_stream=RadioStream(RadioConfig(key[0],alias_frequency(key[0],key[1],key[3],self.radio_us.isChecked()),key[3]),key[2])
                self.radio_key=key;self.radio_filter.reset()
            indices=columns.get('Muestra')
            if indices is not None and np.any((np.diff(indices.astype(np.int64))&0xffffffff)!=1):
                raise ValueError('Discontinuidad RF')
            timestamps=columns.get('Tiempo (us)')
            if timestamps is not None:
                previous=getattr(self.radio_stream,'last_rf_time',None)
                delta=np.diff(timestamps)
                if previous is not None:delta=np.r_[timestamps[0]-previous,delta]
                if np.any(np.abs(delta-1e6/key[0])>.01):raise ValueError('Discontinuidad de tiempo RF')
                self.radio_stream.last_rf_time=float(timestamps[-1])
            if not hasattr(self.radio_stream,'rf_time_origin'):
                self.radio_stream.rf_time_origin=float(timestamps[0]) if timestamps is not None and len(timestamps) else 0.
            audio_first=self.radio_stream.rf_time_origin+self.radio_stream.resampler.output_count*(1e6/key[2])
            audio=self.radio_stream.process(columns['CH1'],int(indices[0]) if indices is not None else None)
            if self.radio_gain.value()!=1.0 or self.radio_offset.value()!=0.0:
                audio=audio*self.radio_gain.value()+self.radio_offset.value()
            filtered=(self.radio_filter.process(audio,key[2],replace(self.filter_config,source='CH1'))
                      if self.filter_config.source=='RADIO' else None)
            self.radio_stream.append(audio,filtered,audio_first)
            now=time.monotonic()
            if now-getattr(self,'_radio_status_updated',0)>.1:
                self._radio_status_updated=now
                self.radio_status.setText((f'US · RF {key[1]/1000:g} · alias {abs((key[1]+key[0]/2)%key[0]-key[0]/2)/1000:g} kHz · ' if self.radio_us.isChecked() else '')+f'RADIO {key[2]/1000:g} kHz · {self.radio_stream.counter} muestras')
        except ValueError as exc:
            self.radio_stream=None;self.radio_key=None;self.radio_filter.reset()
            self.radio_status.setText(f'RADIO silenciada · {exc}')

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
        lbl_t.setStyleSheet("font-size: 9px; font-weight: 800; color: #8f98a8; background: transparent; border:none; padding:0;")
        lbl_t.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        lbl_v = QtWidgets.QLabel("--")
        lbl_v.setMinimumWidth(0)
        lbl_v.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        lbl_v.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}; background: transparent; border:none; padding:0;")
        lbl_v.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_v)
        return card, lbl_v

    def _on_meas_channel_changed(self, ch: str):
        self.active_meas_channel = ch
        if hasattr(self, '_measurement_cards') and self.spectral.mode == 1:
            self.spectral.measurement_channel_changed()
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
        check_icon = (ROOT / "monitor/v18/assets/check_neutral.svg").as_posix()
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

    def _sync_filter_dial(self,dial,value):
        with QtCore.QSignalBlocker(dial):dial.setValue(round(1000*math.log10(max(value,1))/math.log10(60000)))

    def _filter_view_changed(self,*args):
        chosen={name for name,action in self.graph_channel_actions.items() if action.isChecked()}
        self.selected_columns={name:name in chosen for name in self.known_columns}
        self.selection_dirty=True
        self._update_curve_items([name for name,checked in self.selected_columns.items() if checked])

    def _legend_channel_clicked(self,name,item):
        self.graph_channel_actions[name].setChecked(item.isVisible())

    def _legend_label_clicked(self,event,name):
        if event.button()==QtCore.Qt.MouseButton.LeftButton:
            self.graph_channel_actions[name].toggle();event.accept()

    def _filter_preset_changed(self,*args):
        name=self.filter_preset.currentData()
        if name is None:return
        from monitor.v18.filter_presets import apply_filter_preset
        config=apply_filter_preset(name,self.filter_source.currentText())
        controls=(self.filter_mode,self.filter_design,self.filter_order,self.filter_cut,self.filter_upper)
        blockers=[QtCore.QSignalBlocker(control) for control in controls]
        self.filter_mode.setCurrentIndex(self.filter_mode.findData(config.mode))
        self.filter_design.setCurrentIndex(self.filter_design.findData(config.design))
        self.filter_order.setValue(config.order)
        self.filter_cut.setRange(1,self._filter_sample_rate()*.45)
        self.filter_upper.setRange(1,self._filter_sample_rate()*.49)
        self.filter_cut.setValue(config.cutoff);self.filter_upper.setValue(config.upper)
        del blockers
        self._applying_filter_preset=True
        try:self._filter_changed()
        finally:self._applying_filter_preset=False

    def _filter_changed(self,*args):
        if hasattr(self,'filter_preset') and not getattr(self,'_applying_filter_preset',False) and not getattr(getattr(self,'_radio_multiscan',None),'active',False):
            with QtCore.QSignalBlocker(self.filter_preset):self.filter_preset.setCurrentIndex(0)
        rate=self._filter_sample_rate()
        mode=self.filter_mode.currentData()
        rc=self.filter_design.findData('RC')
        self.filter_design.model().item(rc).setEnabled(mode!='bandstop')
        if mode=='bandstop' and self.filter_design.currentData()=='RC':
            with QtCore.QSignalBlocker(self.filter_design):self.filter_design.setCurrentIndex(self.filter_design.findData('Butterworth'))
        with QtCore.QSignalBlocker(self.filter_cut), QtCore.QSignalBlocker(self.filter_upper):
            self.filter_cut.setMaximum(rate*.45)
            self.filter_upper.setMaximum(rate*.49)
            self.filter_upper.setMinimum(self.filter_cut.value()+1 if mode in ('bandpass','bandstop') else 1)
        cutoff=self.filter_upper.value() if mode=='lowpass' else self.filter_cut.value()
        self.filter_config=FilterConfig(self.filter_source.currentText(),mode,self.filter_design.currentData(),cutoff,self.filter_upper.value(),self.filter_order.value())
        active=self.filter_config.source!='OFF'
        self.filter_mode.setEnabled(active)
        self.filter_design.setEnabled(active and mode!='bypass')
        for control,enabled in ((self.filter_cut,mode in ('highpass','bandpass','bandstop')),(self.filter_upper,mode in ('lowpass','bandpass','bandstop'))):
            enabled=enabled and active
            control.setEnabled(enabled);self.filter_dials[control].setEnabled(enabled);self.filter_value_labels[control].setEnabled(enabled)
            self._sync_filter_dial(self.filter_dials[control],control.value())
            value=control.value()
            self.filter_value_labels[control].setText(f'{number(value/1000, formats.n_2f)} kHz' if value>=1000 else f'{number(value, ".0f")} Hz')
        self.filter_order.setEnabled(active and self.filter_config.mode!='bypass')
        self.filter_order.setToolTip('Cantidad de etapas RC en cascada por corte' if self.filter_config.design=='RC' else 'Orden del filtro')
        self.digital_filter.reset()
        self.radio_filter.reset()
        if self.radio_stream is not None:
            self.radio_stream=None;self.radio_key=None
        if hasattr(self,'spectral'):
            self.spectral.bode.cancel('Filtro modificado')
            for panel in self.spectral.bode.panels:
                if 'FILTER' in panel.pair():panel.pair_changed()
            self.spectral.reset()
        # Start a fresh display history; never mix incompatible filter settings.
        if self.sample_counter and not getattr(self,'_preserve_rf_history',False):self.clear_data()
        if (hasattr(self,'dial_trigger_level') and self.trigger_source=='FILTER' and
                (self.dial_trigger_level.minimum()<0)!=self._is_audio_channel('FILTER')):
            self.on_trigger_source_changed('FILTER')
        self._reset_processing_settings()
        if hasattr(self,'radio_output_panel') and hasattr(self,'radio_frequency'):self.radio_output_panel.radio_changed()

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
            is_checked = self.selected_columns.get(name, name in ('CH1', 'CH2'))
            self.selected_columns[name] = is_checked
            checkbox.setChecked(is_checked)
            checkbox.setStyleSheet(self._channel_checkbox_style(name))
            checkbox.setToolTip({'CH1': 'Entrada A2 (ADC1_IN11). Mostrar u ocultar este canal.',
                                 'CH2': 'Entrada A3 (ADC1_IN12). Mostrar u ocultar este canal.'}.get(name, 'Mostrar u ocultar este canal'))
            checkbox.stateChanged.connect(self._on_column_toggled)
            self.channel_color_buttons[name] = picker
            self.channel_checkboxes[name] = checkbox
            layout.addWidget(checkbox, 1)
            layout.addWidget(picker)
            self.columns_layout.addWidget(row)

    def _build_generator_panel(self, layout):
        self.generator_column.setStyleSheet("""
            QLabel { background:transparent; border:0; color:#aeb8c8; }
            QComboBox, QDoubleSpinBox, QSpinBox { background:#10151d; border:1px solid #3a4659;
                border-radius:7px; padding:3px; color:#eef5ff; min-height:18px; }
            QComboBox:hover, QDoubleSpinBox:focus, QSpinBox:focus { border-color:#55dfc4; }
            QPushButton { background:#253f40; border:1px solid #3b7c72; border-radius:8px;
                color:#d6fff6; padding:2px 8px; font-weight:bold; }
            QPushButton:hover { background:#315551; }
            QPushButton:disabled { background:#202630; border-color:#303a48; color:#627083; }
            QDial { background:transparent; }
            QCheckBox { color:#d6fff6; padding:6px 0; }
        """)
        self.generator_panel = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(self.generator_panel)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(2)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.generator_wave = GeneratorComboBox()
        for i, name in enumerate(WAVES[:4]):
            self.generator_wave.addItem(generator_wave_icon(i), name)
        self.generator_wave.setIconSize(QtCore.QSize(36,18))
        self.generator_wave.setFixedHeight(28)
        self.generator_mode = GeneratorComboBox()
        for name, icon in zip((*MODES, "Pulso", "Wav", "Synth", "Radio Test", "Radio"),
                              ('continuous', 'sweep', 'chirp', 'pulse', 'wav', 'fm', 'continuous', 'radio')):
            self.generator_mode.addItem(QtGui.QIcon(str(ROOT / f'monitor/v18/assets/mode_{icon}.svg')), name)
        self.generator_mode.setIconSize(QtCore.QSize(18, 18))
        self.generator_mode.setMinimumWidth(0)
        self.generator_mode.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.generator_mode.setFixedHeight(28)
        self.generator_frequency = GeneratorFrequencySpinBox()
        self.generator_final_frequency = GeneratorFrequencySpinBox()
        for spin in (self.generator_frequency, self.generator_final_frequency):
            spin.setRange(0.1, 50000); spin.setDecimals(3); spin.setValue(2.5)
        self.generator_frequency.setToolTip('0,1 Hz a 50 kHz. Lectura en Hz y kHz (1000 Hz = 1 kHz).\nEscribir en Hz o incluir kHz; confirmar con Enter o al salir.\nPara observar 40–50 kHz, elegir Fs de 200 o 250 kHz.')
        self.generator_frequency.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_frequency.setStyleSheet('font-size:12px; font-weight:bold; color:#8df3dc;')
        self.generator_amplitude = VoltageSpinBox()
        self.generator_amplitude.setRange(0, 3.3); self.generator_amplitude.setDecimals(2)
        self.generator_amplitude.setSingleStep(.01)
        self.generator_amplitude.setSuffix(' Vpp'); self.generator_amplitude.setValue(2.0)
        self.wav_amplitude_dial = AmplitudeDial()
        self.wav_amplitude_dial.setFixedSize(64,64)
        self.wav_amplitude_dial.setRange(0, 330)
        self.wav_amplitude_dial.setValue(200)
        self.wav_amplitude_dial.setNotchesVisible(True)
        self.wav_amplitude_dial.setNotchTarget(7)
        self.wav_amplitude_dial.setTracking(True)
        self.wav_amplitude_dial.setSingleStep(1)
        self.wav_amplitude_dial.setPageStep(10)
        self.wav_amplitude_dial.setToolTip("Amplitud: 0,01 V por paso. Shift + arrastrar: ajuste fino.")
        self.wav_amplitude_dial.valueChanged.connect(lambda value: self.generator_amplitude.setValue(value / 100))
        self.generator_amplitude.valueChanged.connect(self._sync_wav_amplitude_dial)
        self.wav_amplitude_value = QtWidgets.QLabel()
        self.wav_amplitude_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.wav_amplitude_value.setStyleSheet('color:#aeb8c8;background:transparent;border:none;padding:0;')
        self.wav_amplitude_box = QtWidgets.QWidget()
        self.wav_amplitude_box.setFixedHeight(84)
        amplitude_layout = QtWidgets.QVBoxLayout(self.wav_amplitude_box)
        amplitude_layout.setContentsMargins(0,0,0,0)
        amplitude_layout.setSpacing(0)
        amplitude_layout.addWidget(self.wav_amplitude_dial,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
        amplitude_layout.addWidget(self.wav_amplitude_value)
        self._sync_wav_amplitude_dial(self.generator_amplitude.value())
        self.generator_offset = VoltageSpinBox()
        self.generator_offset.setRange(0, 3.3); self.generator_offset.setDecimals(2)
        self.generator_offset.setSingleStep(.01)
        self.generator_offset.setSuffix(' V'); self.generator_offset.setValue(1.65)
        self.generator_offset_slider = OffsetDial()
        self.generator_offset_slider.setFixedSize(64,64)
        self.generator_offset_slider.setProperty("virtualColor",True)
        self.generator_offset_slider.centered.connect(lambda: self.generator_offset.setValue(1.65))
        self.generator_offset_slider.setSingleStep(1)
        self.generator_offset_slider.setPageStep(10)
        self.generator_offset_slider.setToolTip("Offset: 0,01 V por paso. Shift + arrastrar: ajuste fino; doble clic: centrar.")
        self.generator_offset_box = QtWidgets.QWidget()
        offset_layout = QtWidgets.QVBoxLayout(self.generator_offset_box)
        offset_layout.setContentsMargins(0,0,0,0);offset_layout.setSpacing(0)
        self.generator_offset_value = QtWidgets.QLabel()
        self.generator_offset_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_offset_value.setStyleSheet('color:#aeb8c8;background:transparent;border:none;padding:0;')
        offset_layout.addWidget(self.generator_offset_slider,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
        offset_layout.addWidget(self.generator_offset_value)
        self.generator_offset_box.setFixedHeight(84)
        self.generator_headroom = QtWidgets.QLabel()
        self.generator_headroom.setWordWrap(False)
        self.generator_headroom.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.generator_headroom.setToolTip('La señal se acerca a los extremos del DAC: puede recortarse por debajo de 0,2 V o por encima de 3,1 V.')
        self.generator_headroom.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_headroom.setStyleSheet('color:#ffbf69; font-size:10px;')
        self.generator_duration = GeneratorValueSpinBox()
        self.generator_duration.setRange(0.001,600); self.generator_duration.setDecimals(3)
        self.generator_duration.setSuffix(' s'); self.generator_duration.setValue(1)
        self._generator_duration_ms = False
        self._generator_duration_us = False
        self._pulse_us_capable = False
        self.generator_frequency_dial = InstrumentDial()
        self.generator_frequency_dial.setFixedSize(64,64)
        self.generator_frequency_dial.setRange(0,1000)
        self.generator_frequency_dial.setNotchesVisible(True)
        self.generator_frequency_dial.setNotchTarget(7.0)
        self.generator_frequency_dial.setTracking(True)
        palette=self.generator_frequency_dial.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Button,QtGui.QColor('#55a99e'))
        self.generator_frequency_dial.setPalette(palette)
        self.generator_frequency_dial.setToolTip('Dial logarítmico · 0,1 Hz → 50 kHz. El número permite ajuste preciso.')
        self.generator_frequency_dial.valueChanged.connect(
            lambda value:self.generator_frequency.setValue(round(.1*(self.generator_frequency.maximum()/.1)**(value/1000), 3 if .1*(self.generator_frequency.maximum()/.1)**(value/1000) < 1 else 0)))
        def sync_dial(value):
            blocker=QtCore.QSignalBlocker(self.generator_frequency_dial)
            self.generator_frequency_dial.setValue(round(1000*math.log(value/.1)/math.log(self.generator_frequency.maximum()/.1)))
            del blocker
        self.generator_frequency.valueChanged.connect(sync_dial)
        sync_dial(2.5)
        self.generator_final_frequency_dial = InstrumentDial()
        self.generator_final_frequency_dial.setFixedSize(64,64)
        self.generator_final_frequency_dial.setRange(0,1000)
        self.generator_final_frequency_dial.valueChanged.connect(
            lambda value:self.generator_final_frequency.setValue(round(.1*(self.generator_frequency.maximum()/.1)**(value/1000),3 if .1*(self.generator_frequency.maximum()/.1)**(value/1000)<1 else 0)))
        def sync_final_dial(value):
            with QtCore.QSignalBlocker(self.generator_final_frequency_dial):
                self.generator_final_frequency_dial.setValue(round(1000*math.log(max(.1,value)/.1)/math.log(self.generator_frequency.maximum()/.1)))
        self.generator_final_frequency.valueChanged.connect(sync_final_dial)
        sync_final_dial(self.generator_final_frequency.value())
        self._duty_capable = False
        self.generator_duty_box = QtWidgets.QWidget()
        duty_layout = QtWidgets.QGridLayout(self.generator_duty_box)
        duty_layout.setContentsMargins(0,0,0,0)
        duty_title=QtWidgets.QLabel('Duty Cycle')
        duty_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        duty_layout.addWidget(duty_title,0,0,1,2)
        self.generator_duty = QtWidgets.QSpinBox()
        self.generator_duty.setRange(1,99);self.generator_duty.setValue(50)
        self.generator_duty.setSuffix(' %')
        self.generator_duty_dial = InstrumentDial()
        self.generator_duty_dial.setFixedSize(64,64)
        self.generator_duty_dial.setRange(1,99);self.generator_duty_dial.setValue(50)
        self.generator_duty_dial.setProperty('virtualColor',True)
        self.generator_duty_dial.setNotchesVisible(True)
        self.generator_duty_dial.setNotchTarget(7.0)
        self.generator_duty_dial.valueChanged.connect(self.generator_duty.setValue)
        self.generator_duty.valueChanged.connect(self.generator_duty_dial.setValue)
        duty_layout.setColumnStretch(0,1);duty_layout.setColumnStretch(1,1)
        duty_layout.setRowMinimumHeight(1,64)
        duty_layout.setRowMinimumHeight(2,20)
        duty_layout.addWidget(self.generator_duty_dial,1,0,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignTop)
        self.generator_duty.setFixedHeight(28)
        self.generator_duty.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.generator_duty.setMinimumWidth(0)
        self.generator_duty.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        duty_layout.addWidget(self.generator_duty,1,1)
        grid.addWidget(self.generator_duty_box,10,0,1,2)
        self.generator_enabled = QtWidgets.QPushButton('▶ Encender')
        self.generator_enabled.setCheckable(True)
        self.generator_enabled.setChecked(False)
        self.generator_enabled.setFixedHeight(34)
        self.generator_enabled.setStyleSheet('QPushButton:checked {background-color:#303e40;border-color:#577b75;}')
        self.generator_restart = QtWidgets.QPushButton('Disparar de nuevo')
        self.generator_restart.clicked.connect(self._apply_generator)
        controls = [('Modo',self.generator_mode),('Forma de onda',self.generator_wave),
                    ('Frecuencia',self.generator_frequency),('Frecuencia final',self.generator_final_frequency),
                    ('Amplitud',self.generator_amplitude),('Offset',self.generator_offset),
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
        grid.addWidget(self.wav_amplitude_box,8,0,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        grid.setColumnStretch(0,1); grid.setColumnStretch(1,1)
        self.generator_enabled.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.generator_restart.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        grid.addWidget(self.generator_offset_box,8,1,2,1)
        grid.addWidget(self.generator_headroom,14,0,1,2)
        grid.addWidget(self.generator_enabled,11,0,1,2)
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
        self.generator_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.generator_scroll.setWidget(self.generator_panel)
        layout.addWidget(self.generator_scroll,1)
        self._generator_timer = QtCore.QTimer(self)
        self._generator_timer.setSingleShot(True)
        self._generator_timer.setInterval(250)
        self._generator_timer.timeout.connect(self._apply_generator)
        self.generator_duty.valueChanged.connect(self._schedule_generator)
        self.generator_frequency_dial.sliderReleased.connect(self._schedule_generator)
        for _,control in controls:
            if isinstance(control, QtWidgets.QDoubleSpinBox):
                control.setKeyboardTracking(False)
            signal=control.currentIndexChanged if isinstance(control,QtWidgets.QComboBox) else control.valueChanged
            signal.connect(self._generator_mode_changed if control is self.generator_mode else self._schedule_generator)
        self.generator_enabled.toggled.connect(lambda checked: self.generator_enabled.setText('■ Apagar' if checked else '▶ Encender'))
        self.generator_enabled.toggled.connect(self._schedule_generator)
        self._generator_dirty=False
        self._generator_syncing=False
        self._generator_requested=None
        self._generator_active=GeneratorConfig()
        self._generator_state_known=False
        self._generator_controls=[c for _,c in controls]+[self.generator_enabled,self.generator_restart,self.generator_offset_slider,self.generator_duty,self.generator_duty_dial]
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
            button.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets' / icon)))
            button.setToolTip(('Retroceder' if delta < 0 else 'Avanzar') + ' 10 segundos')
            button.setAccessibleName(button.toolTip())
            button.setEnabled(False)
            button.clicked.connect(lambda checked=False, seconds=delta: self._seek_wav(seconds))
        self.wav_play = QtWidgets.QToolButton()
        self.wav_play.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets/wav_play.svg')))
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
        self.wav_rate.setCurrentIndex(self.wav_rate.findData(40000))
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
        from monitor.v18.fm_panel import FMPanel
        self.fm_panel = FMPanel(self)
        self._build_radio_test_panel()
        from monitor.v18.radio_output_panel import RadioOutputPanel
        self.radio_output_panel=RadioOutputPanel(self,InstrumentDial,GeneratorComboBox)
        self.radio_generator_input_label=QtWidgets.QLabel('IN')
        self.radio_generator_input_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.radio_generator_input_label,0,1)
        grid.addWidget(self.radio_output_panel.input_source,1,1)
        self.radio_generator_input_label.hide();self.radio_output_panel.input_source.hide()
        grid.addWidget(self.radio_output_panel,2,0,9,2)
        self.radio_output_panel.hide()
        grid.addWidget(self.radio_test_panel,2,0,5,2)
        grid.addWidget(self.fm_panel,2,0,9,2)
        self.fm_editor_label=QtWidgets.QLabel("Editar")
        self.fm_editor_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.fm_editor_label,0,1)
        grid.addWidget(self.fm_panel.editor_mode,1,1)
        self.fm_editor_label.hide();self.fm_panel.editor_mode.hide()
        self.fm_panel.hide()
        self._previous_generator_mode = 0
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
        self.wav_play.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets' / icon)))
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
        began = time.perf_counter()
        dialog = getattr(self, '_wav_file_dialog', None)
        if dialog is not None:
            dialog.raise_()
            dialog.activateWindow()
            return
        # A modeless Qt dialog lets acquisition deliveries run while browsing.
        dialog = QtWidgets.QFileDialog(self, 'Elegir archivo WAV', str(ROOT / 'audios'))
        dialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter('WAV (*.wav *.WAV)')
        dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        dialog.fileSelected.connect(self._wav_file_selected)
        dialog.finished.connect(lambda _result: self._wav_file_dialog_finished(dialog))
        self._wav_file_dialog = dialog
        dialog.show()
        self._note_gui_callback('WAV: abrir selector', began)

    def _wav_file_dialog_finished(self, dialog):
        if getattr(self, '_wav_file_dialog', None) is dialog:
            self._wav_file_dialog = None
        dialog.deleteLater()

    def _wav_file_selected(self, path):
        began = time.perf_counter()
        if path:
            try:
                metadata = inspect_wav(path)
            except (ValueError, OSError) as exc:
                self.wav_path = ''
                self._wav_metadata = None
                self.wav_info.setText(f'WAV inválido: {exc}')
                self.generator_status.setText(f'WAV inválido: {exc}')
                self._sync_wav_transport()
                self._note_gui_callback('WAV: inspeccionar archivo', began)
                return
            self.wav_path = path
            self._wav_metadata = metadata
            description = f"{number(metadata['rate']/1000, formats.ng)} kHz · {metadata['bits']} bits · {metadata['channels']} canales · {number(metadata['duration'], formats.n_1f)} s"
            self.wav_info.setText(description + f'\nSalida: {number(self.wav_rate.currentData()/1000, formats.ng)} kHz · 12 bits · mono')
            self.generator_status.setText('WAV válido · ' + description)
            self._sync_wav_transport()
            self.wav_file.setText(self.wav_file.fontMetrics().elidedText(Path(path).name, QtCore.Qt.TextElideMode.ElideMiddle, 210))
            self.wav_file.setToolTip(path)
        self._note_gui_callback('WAV: inspeccionar archivo', began)

    def _play_wav(self):
        if self._wav_preparing or self._wav_active or not self.wav_path or not self.serial_worker or not self._wav_capable:
            self.generator_status.setText('Elegir un WAV válido.' if not self.wav_path else 'Conectar el Q con V18 para reproducir WAV.' if not self.serial_worker else 'WAV: esperando confirmación de V18; reconectar el Q.')
            return
        if self.spectral.bode.active:
            self.generator_status.setText('Detener Bode antes de reproducir WAV.')
            return
        if self.output_pending or self._auto_apply_timer.isActive():
            self.generator_status.setText('Esperar la confirmación de adquisición antes de reproducir WAV.')
            return
        if self.applied_configuration.rate > 100000:
            self.generator_status.setText('Wav: usar muestreo de adquisición hasta 100 kHz; 125 kHz queda pendiente de validación conjunta en V18.')
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
        if not self._wav_active and self.config_rate_combo.currentData()!=self.applied_configuration.rate:
            self._schedule_configuration()
        if self.generator_mode.currentIndex()==7 or self.radio_output_panel.source is not None:
            self.radio_output_panel.status(status)
        if self.generator_mode.currentIndex() == 5:
            self.fm_panel.status(status)
        if self.generator_mode.currentIndex() == 4:
            names = ('Listo','Cargando','Reproduciendo','Finalizado','Interrumpido: faltaron muestras','Error')
            metadata = self._wav_metadata
            detail = f" · {number(metadata['rate']/1000, formats.ng)} kHz · {metadata['bits']} bits · {metadata['channels']} canales" if metadata else ''
            if int(status.state) == 0 and not self._wav_preparing and self.applied_configuration.rate > 100000:
                self.generator_status.setText('WAV: seleccionar adquisición de 100 kHz o menos para reproducir.')
            else:
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
        self.generator_offset_value.setText(f'{number(offset, formats.n_2f)} V')
        near_rail = offset - half < 0.2 - 1e-9 or offset + half > 3.1 + 1e-9
        self.generator_headroom.setText(
            '<span style="color:#ffbf69;font-size:14px;">●</span>&nbsp;&nbsp; Posible clipping' if near_rail else '')
        self.generator_headroom.setVisible(near_rail)

    def _build_radio_test_panel(self):
        self.radio_test_panel=QtWidgets.QWidget()
        layout=QtWidgets.QVBoxLayout(self.radio_test_panel)
        layout.setContentsMargins(0,6,0,0);layout.setSpacing(4)
        grid=QtWidgets.QGridLayout();grid.setSpacing(4)
        self.radio_test_carriers=[];self.radio_test_dials=[];self.radio_test_values=[];self.radio_test_switches=[]
        self.radio_test_tone=QtWidgets.QSpinBox();self.radio_test_tone.setRange(0,4000)
        self.radio_test_tone.setValue(1000)
        for i,(title,value,control) in enumerate((
                ('PORTADORA 1',20000,QtWidgets.QSpinBox()),
                ('PORTADORA 2',40000,QtWidgets.QSpinBox()),
                ('TONO AM',1000,self.radio_test_tone))):
            if i<2:control.setRange(25,50000);self.radio_test_carriers.append(control)
            control.setValue(value);control.setParent(self.radio_test_panel);control.hide()
            card=QtWidgets.QFrame();card.setStyleSheet('QFrame {background:#21252f;border:1px solid #2e3543;border-radius:6px;}')
            box=QtWidgets.QVBoxLayout(card);box.setContentsMargins(4,2,4,2);box.setSpacing(1)
            label=QtWidgets.QLabel(title);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet('font-size:9px;color:#8f98a8;border:none;')
            dial=InstrumentDial();dial.setRange(control.minimum(),control.maximum());dial.setValue(value)
            dial.setFixedSize(60,60);dial.setSingleStep(25);dial.setPageStep(100)
            control.setSingleStep(25)
            dial.setToolTip('Frecuencia: pasos de 25 Hz con las flechas; Page Up/Down: 100 Hz')
            text=QtWidgets.QLabel(self._radio_test_frequency_text(value));text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            text.setStyleSheet('color:#aeb8c8;border:none;')
            heading=QtWidgets.QHBoxLayout();heading.setContentsMargins(0,0,0,0);heading.setSpacing(2)
            if i<2:
                switch=QtWidgets.QToolButton();switch.setCheckable(True);switch.setChecked(True)
                switch.setFixedSize(10,10);switch.setEnabled(False)
                switch.setAccessibleName(f'Activa portadora F{i+1}')
                switch.setToolTip(f'Activar/apagar F{i+1} · requiere firmware actualizado')
                switch.setStyleSheet('QToolButton {padding:0;border:1px solid #617079;border-radius:5px;background:#26323a;} QToolButton:checked {background:#55dfc4;border-color:#83ead5;} QToolButton:disabled {background:#34434a;border-color:#45545c;}')
                self.radio_test_switches.append(switch)
                heading.addWidget(switch);heading.addWidget(label,1);heading.addSpacing(10)
                switch.toggled.connect(lambda checked,index=i:self._radio_test_carrier_changed(index,checked))
            else:heading.addWidget(label)
            box.addLayout(heading);box.addSpacing(4);box.addWidget(dial,0,QtCore.Qt.AlignmentFlag.AlignHCenter);box.addWidget(text)
            grid.addWidget(card,i//2,i%2);grid.setColumnStretch(i%2,1)
            self.radio_test_dials.append(dial);self.radio_test_values.append(text)
            def selected(v,dial=dial,control=control):
                snapped=max(control.minimum(),min(control.maximum(),round(v/25)*25))
                with QtCore.QSignalBlocker(dial):dial.setValue(snapped)
                control.setValue(snapped)
            dial.valueChanged.connect(selected)
            def changed(v,dial=dial,text=text):
                with QtCore.QSignalBlocker(dial):dial.setValue(v)
                text.setText(self._radio_test_frequency_text(v))
                if hasattr(self,'_radio_test_update_timer') and self.radio_test_play.isChecked():self._radio_test_update_timer.start()
            control.valueChanged.connect(changed)
        layout.addLayout(grid)
        info=QtWidgets.QLabel('AM 50 % · tono 0: sin modulación')
        info.setWordWrap(True);layout.addWidget(info)
        self.radio_test_play=QtWidgets.QPushButton('▶ Play');self.radio_test_play.setCheckable(True)
        self.radio_test_play.setEnabled(False);self.radio_test_play.setToolTip('Requiere firmware V18 con Radio Test en pasos de 25 Hz')
        layout.addWidget(self.radio_test_play)
        self._radio_test_update_timer=QtCore.QTimer(self);self._radio_test_update_timer.setSingleShot(True)
        self._radio_test_update_timer.setInterval(200);self._radio_test_update_timer.timeout.connect(self._radio_test_toggle)
        self.radio_test_play.clicked.connect(self._radio_test_toggle)
        self.radio_test_panel.hide()

    def _radio_test_carrier_changed(self,index,checked):
        self.radio_test_dials[index].setEnabled(checked)
        self.radio_test_values[index].setEnabled(checked)
        if hasattr(self,'_radio_test_update_timer') and self.radio_test_play.isChecked():self._radio_test_update_timer.start()

    @staticmethod
    def _radio_test_frequency_text(hz):
        return f'{hz} Hz' if hz<1000 else f'{hz/1000:g} kHz'

    def _radio_test_config(self,enabled):
        amp=self.generator_amplitude.value();offset=self.generator_offset.value()
        if offset-amp/2<0 or offset+amp/2>3.3:raise ValueError('Radio Test: amplitud/offset fuera del DAC')
        return GeneratorConfig(wave=1,enabled=int(enabled),mode=3,
            frequency=self.radio_test_carriers[0].value()*1000 if self.radio_test_switches[0].isChecked() else 0,
            final_frequency=self.radio_test_carriers[1].value()*1000 if self.radio_test_switches[1].isChecked() else 0,
            duration=self.radio_test_tone.value(),
            low=round((offset-amp/2)*4095/3.3),high=round((offset+amp/2)*4095/3.3))

    def _radio_test_toggle(self):
        self._radio_test_update_timer.stop()
        try:
            if self.serial_worker is None:raise ValueError('Conectar Q con firmware V18 Radio Test')
            config=self._radio_test_config(True) if self.radio_test_play.isChecked() else replace(self._generator_active,enabled=0)
            self.serial_worker.request_generator(config);self._generator_requested=config
            self.radio_test_play.setText('■ Stop' if config.enabled else '▶ Play')
            self.generator_status.setText('Radio Test: esperando confirmación Q')
        except (ValueError,queue.Full) as exc:
            running=self._generator_active.mode==3 and bool(self._generator_active.enabled)
            self.radio_test_play.setChecked(running);self.radio_test_play.setText('■ Stop' if running else '▶ Play')
            self.generator_status.setText(str(exc))

    def _generator_frequency_limits(self):
        from monitor.v18.receiver.unoq_generator import waveform_limit
        wave=4 if self.generator_mode.currentIndex()==3 else self.generator_wave.currentIndex()
        maximum=waveform_limit(wave)/1000.
        for control in (self.generator_frequency,self.generator_final_frequency):
            with QtCore.QSignalBlocker(control):control.setMaximum(maximum)
            control.setToolTip(f'0,1 Hz a {maximum/1000:g} kHz. Permite valores intermedios; el timer redondea la frecuencia efectiva.')
        for spin,dial in ((self.generator_frequency,self.generator_frequency_dial),(self.generator_final_frequency,self.generator_final_frequency_dial)):
            with QtCore.QSignalBlocker(dial):dial.setValue(round(1000*math.log(max(.1,spin.value())/.1)/math.log(maximum/.1)))
            dial.setToolTip(f'Dial logarítmico · 0,1 Hz → {maximum/1000:g} kHz. Ajuste preciso en el número.')

    def _generator_availability(self):
        self._generator_frequency_limits()
        if hasattr(self,'radio_output_panel'):
            self.radio_output_panel.setVisible(self.generator_mode.currentIndex()==7)
            if self.generator_mode.currentIndex()==7:self.radio_output_panel.sync()
        if hasattr(self,'radio_test_panel'):self.radio_test_panel.setVisible(self.generator_mode.currentIndex()==6)
        duty_visible=self.generator_mode.currentIndex()==0 and self.generator_wave.currentIndex()==0
        for widget in (self.generator_duty_box,self.generator_duty,self.generator_duty_dial):widget.setVisible(duty_visible)
        self.generator_duty_box.setEnabled(self._duty_capable)
        self.generator_duty_box.setToolTip('Tiempo en alto por período. Frecuencia conservada; el DAC redondea el duty al paso disponible.' if self._duty_capable else 'Duty 50 %. Preparar Q para habilitar duty ajustable.')

        fm_mode = self.generator_mode.currentIndex()==5
        if hasattr(self,'fm_panel'):
            self.fm_panel.setVisible(fm_mode)
            self.fm_editor_label.setVisible(fm_mode)
            self.fm_panel.editor_mode.setVisible(fm_mode)
        for widget in (self.generator_offset,self.generator_offset_slider,
                       self._generator_labels[self.generator_amplitude],self._generator_labels[self.generator_offset]):
            widget.show()
        self.generator_offset.hide()
        self.generator_offset_box.setVisible(not fm_mode)
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
        self.wav_amplitude_box.setVisible(not fm_mode)
        self.generator_amplitude.hide()
        self._generator_labels[self.generator_amplitude].setText(
            'Amplitud')
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
            self.generator_enabled.setVisible(mode == 0)
        if hasattr(self, '_wav_labels') and self._generator_layout_wav != wav_mode:
            self._arrange_generator_mode(wav_mode)
        self._arrange_frequency_dials(mode)
        if mode==6:
            self.generator_panel.layout().addWidget(self.generator_mode,1,0)
            for widget in self._generator_controls + self._wav_widgets + list(self._generator_labels.values()) + [self.generator_frequency_dial,self.generator_headroom]:
                if widget is not self.generator_mode:widget.hide()
            self._generator_labels[self.generator_mode].show()
            self.wav_amplitude_box.show();self.generator_offset_box.show()
            self.generator_offset_slider.show()
            self._generator_labels[self.generator_amplitude].show()
            self._generator_labels[self.generator_offset].show()
        elif hasattr(self,'radio_test_panel'):
            self.generator_panel.layout().addWidget(self.generator_mode,1,0)
        if fm_mode:
            for widget in self._generator_controls + self._wav_widgets + list(self._generator_labels.values()) + [self.wav_amplitude_box,self.generator_frequency_dial,self.generator_headroom]:
                if widget is not self.generator_mode: widget.hide()
            self._generator_labels[self.generator_mode].show()
        if mode==7:
            for widget in self._generator_controls + self._wav_widgets + list(self._generator_labels.values()) + [self.wav_amplitude_box,self.generator_offset_box,self.generator_frequency_dial,self.generator_headroom]:
                if widget is not self.generator_mode:widget.hide()
            self._generator_labels[self.generator_mode].show()
        if hasattr(self,'radio_generator_input_label'):
            self.radio_generator_input_label.setVisible(mode==7)
            self.radio_output_panel.input_source.setVisible(mode==7)
        self.generator_panel.layout().activate()
        if getattr(self,'_central_status_ready',False):self._refresh_status_boxes()
        if hasattr(self, '_generator_reserved_height'):
            height=self._generator_reserved_height
            if mode==6:
                height=max(height,self.generator_panel.sizeHint().height())
            self.generator_scroll.setFixedHeight(height)

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
                # Reserve the compact signal-generator layouts. Synth pages
                # scroll internally instead of taking space from Analysis.
                for index in range(min(5, self.generator_mode.count())):
                    self.generator_mode.setCurrentIndex(index)
                    self._generator_availability()
                    self.generator_headroom.show()
                    self.generator_panel.layout().activate()
                    height = max(height, self.generator_panel.sizeHint().height() - 6)
                self.generator_mode.setCurrentIndex(mode)
                self._generator_availability()
                self.generator_duration.setValue(duration)
        finally:
            self.generator_headroom.setVisible(warning_visible)
            self._generator_syncing = syncing
        self._generator_reserved_height = height
        self.generator_scroll.setFixedHeight(height)

    def _arrange_generator_mode(self, wav_mode):
        grid = self.generator_panel.layout()
        self._generator_layout_wav = wav_mode
        shared = [self.generator_offset, self.generator_offset_slider,self.generator_offset_box,
                  self._generator_labels[self.generator_amplitude], self._generator_labels[self.generator_offset],
                  self.wav_amplitude_box, self.generator_headroom]
        for widget in shared + self._wav_widgets:
            grid.removeWidget(widget)
        if wav_mode:
            placements = [(self._wav_labels[0],0,1,1,1),(self.wav_file,1,1,1,1),
                          (self._wav_labels[1],2,0,1,1),(self._wav_labels[2],2,1,1,1),
                          (self.wav_channels,3,0,1,1),(self.wav_rate,3,1,1,1),
                          (self._generator_labels[self.generator_amplitude],4,0,1,1),
                          (self._generator_labels[self.generator_offset],4,1,1,1),
                          (self.generator_offset_box,5,1,2,1),
                          (self.wav_transport,8,0,1,2),
                          (self.wav_info,9,0,1,2),(self.generator_headroom,14,0,1,2)]
            grid.addWidget(self.wav_amplitude_box,5,0,2,1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        else:
            placements = [(self._generator_labels[self.generator_amplitude],7,0,1,1),
                          (self._generator_labels[self.generator_offset],7,1,1,1),
                          (self.generator_offset_box,8,1,2,1),
                          (self.generator_headroom,14,0,1,2)]
            grid.addWidget(self.wav_amplitude_box,8,0,2,1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        for widget,row,col,rows,cols in placements:
            grid.addWidget(widget,row,col,rows,cols)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)

    def _arrange_frequency_dials(self, mode):
        grid=self.generator_panel.layout()
        grid.setRowMinimumHeight(3,0);grid.setRowMinimumHeight(4,0)
        sweep=mode in (1,2)
        self.generator_final_frequency_dial.setVisible(sweep)
        if mode in (4,5):
            return
        widgets=(self._generator_labels[self.generator_frequency],self.generator_frequency,
                 self._generator_labels[self.generator_final_frequency],self.generator_final_frequency,
                 self.generator_frequency_dial,self.generator_final_frequency_dial,
                 self._generator_labels[self.generator_duration],self.generator_duration)
        for widget in widgets:
            grid.removeWidget(widget)
        if sweep:
            for col,control,dial in ((0,self.generator_frequency,self.generator_frequency_dial),
                                     (1,self.generator_final_frequency,self.generator_final_frequency_dial)):
                self._generator_labels[control].setText('Frecuencia inicial' if col==0 else 'Frecuencia final')
                grid.addWidget(self._generator_labels[control],2,col)
                grid.addWidget(dial,3,col,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(control,4,col)
            grid.addWidget(self._generator_labels[self.generator_duration],5,0,1,2)
            grid.addWidget(self.generator_duration,6,0,1,2)
        else:
            self._generator_labels[self.generator_frequency].setText('Frecuencia')
            grid.addWidget(self._generator_labels[self.generator_frequency],2,0,1,2)
            grid.addWidget(self.generator_frequency,3,1,1,1,alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(self.generator_frequency_dial,3,0,2,1,alignment=QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignTop)
            if mode==0:
                grid.setRowMinimumHeight(3,64);grid.setRowMinimumHeight(4,20)
            grid.addWidget(self._generator_labels[self.generator_final_frequency],5,0)
            grid.addWidget(self.generator_final_frequency,6,0)
            grid.addWidget(self._generator_labels[self.generator_duration],5,1)
            grid.addWidget(self.generator_duration,6,1)

    def _generator_mode_changed(self, mode):
        if self._generator_syncing:
            return
        previous = self._previous_generator_mode
        self._previous_generator_mode = mode
        if mode != previous:
            if hasattr(self,'radio_test_play'):
                self._radio_test_update_timer.stop()
                self.radio_test_play.setChecked(False);self.radio_test_play.setText('▶ Play')
            self._generator_timer.stop()
            with QtCore.QSignalBlocker(self.generator_enabled):
                self.generator_enabled.setChecked(False)
            self.generator_enabled.setText('▶ Encender')
            if self.serial_worker is not None:
                try:
                    self.serial_worker.request_generator(replace(self._generator_active, enabled=0))
                except queue.Full:
                    self.generator_status.setText('Generador ocupado: no se pudo apagar la salida.')
                    with QtCore.QSignalBlocker(self.generator_mode):
                        self.generator_mode.setCurrentIndex(previous)
                    self._previous_generator_mode = previous
                    return
        if previous==7 and mode!=previous:self.radio_output_panel.stop()
        if previous in (4,5) and mode != previous:
            self._stop_wav()
            self.fm_panel.source = None
        if mode == 5 and previous != 5:
            selected=self.config_rate_combo.currentData()
            self._synth_previous_adc_rate=selected if selected>40000 else None
        elif previous == 5 and mode != 5:
            saved=getattr(self,'_synth_previous_adc_rate',None)
            self._synth_previous_adc_rate=None
            if saved is not None:
                self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(saved))
        self._destination_changed()
        if (mode==5 or previous==5) and self.config_rate_combo.currentData()!=self.applied_configuration.rate:
            self._schedule_configuration()
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
            self.generator_frequency_dial.setValue(round(1000*math.log(20/.1)/math.log(self.generator_frequency.maximum()/.1)))
            self.generator_final_frequency.setValue(2000)
            self.generator_duration.setValue(2)
            del blockers
        self._schedule_generator()

    def _schedule_generator(self, *args):
        if self._generator_syncing: return
        self._generator_availability()
        if self.generator_mode.currentIndex() == 7:
            self._generator_timer.stop()
            return
        if self.generator_mode.currentIndex() == 6:
            self._generator_timer.stop()
            if self.radio_test_play.isChecked():self._radio_test_update_timer.start()
            return
        if self.generator_mode.currentIndex() == 5:
            self._generator_timer.stop()
            return
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
        if hasattr(self, "wav_amplitude_value"):
            self.wav_amplitude_value.setText(f"{number(value, formats.n_2f)} Vpp")
        with QtCore.QSignalBlocker(self.wav_amplitude_dial):
            self.wav_amplitude_dial.setValue(round(value * 100))

    def _update_wav_levels(self):
        if self.serial_worker is not None:
            amplitude = self.generator_amplitude.value()
            offset = min(3.3 - amplitude / 2, max(amplitude / 2, self.generator_offset.value()))
            self.serial_worker.request_wav_levels(amplitude, offset)

    def _generator_config(self):
        if self.generator_mode.currentIndex()==6:return self._radio_test_config(self.radio_test_play.isChecked())
        amp=self.generator_amplitude.value(); offset=self.generator_offset.value()
        low,high=offset-amp/2,offset+amp/2
        if low < -1e-9 or high > 3.3+1e-9:
            if self.generator_enabled.isChecked():
                raise ValueError('Amplitud y offset deben dejar ambos niveles entre 0 y 3,3 V')
            low=self._generator_active.low*3.3/4095
            high=self._generator_active.high*3.3/4095
        return GeneratorConfig(4 if self.generator_mode.currentIndex() == 3 else self.generator_wave.currentIndex(),int(self.generator_mode.currentIndex() in (1,2,3) or (self.generator_enabled.isChecked() and self.generator_mode.currentIndex()==0)),
            0 if self.generator_mode.currentIndex() in (3,4,5,7) else self.generator_mode.currentIndex(),round(self.generator_frequency.value()*1000),
            round(self.generator_final_frequency.value()*1000),round(max(0,low)*4095/3.3),
            round(min(3.3,high)*4095/3.3),round(self.generator_duration.value()*(1 if self._generator_duration_ms else 1000)), int(self._generator_duration_us),self.generator_duty.value() if self._duty_capable and self.generator_mode.currentIndex()==0 and self.generator_wave.currentIndex()==0 else 50)

    def _apply_generator(self):
        self._generator_timer.stop()
        if self.generator_mode.currentIndex() in (4,5,6,7): return
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
        from monitor.v18.receiver.unoq_switch import Phase
        if (reply.phase==Phase.APPLIED and reply.active!=self._generator_active and
                (self._generator_requested is None or reply.active==self._generator_requested)):
            self.radio_candidates=[];self._radio_scan_generation+=1
            self._update_radio_bandwidth_suggestion()
            self.spectral.refresh_radio_overlay()
            self.radio_frequency_dial.setPeakFrequencies(())
            self._radio_scan_not_before_sample=self.sample_counter
            self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        self.radio_test_play.setEnabled(getattr(reply,'radio_test_hz_capable',False))
        for switch in self.radio_test_switches:switch.setEnabled(getattr(reply,'radio_test_independent_capable',False))
        if self.generator_mode.currentIndex()==7:
            if reply.phase==Phase.APPLIED:
                self._generator_active=reply.active;self._generator_state_known=True
                self._generator_requested=None
            return
        if reply.phase==Phase.APPLIED and reply.active.mode==3:
            if self._generator_requested is not None and reply.active!=self._generator_requested:return
            self._generator_active=reply.active;self._generator_state_known=True
            self._generator_requested=None
            self.radio_test_play.setChecked(reply.running)
            self.radio_test_play.setText('■ Stop' if reply.running else '▶ Play')
            entering=self.generator_mode.currentIndex()!=6
            if reply.running or not entering:
                with QtCore.QSignalBlocker(self.generator_mode):self.generator_mode.setCurrentIndex(6)
                self._previous_generator_mode=6
                for index,frequency in enumerate((reply.active.frequency,reply.active.final_frequency)):
                    with QtCore.QSignalBlocker(self.radio_test_switches[index]):self.radio_test_switches[index].setChecked(bool(frequency))
                    self.radio_test_dials[index].setEnabled(bool(frequency))
                    self.radio_test_values[index].setEnabled(bool(frequency))
                    if entering and frequency:self.radio_test_carriers[index].setValue(frequency//1000)
                if entering:self.radio_test_tone.setValue(reply.active.duration)
                self._generator_availability()

            self.generator_status.setText('Radio Test activo · AM 50 %' if reply.running else 'Radio Test apagado')
            return
        duty_capable=getattr(reply,'duty_capable',False)
        if duty_capable != self._duty_capable:
            self._duty_capable=duty_capable;self._generator_availability()
        capability = getattr(reply, 'pulse_us_capable', False)
        if capability != self._pulse_us_capable:
            self._pulse_us_capable = capability
            self._generator_availability()
        from monitor.v18.receiver.unoq_switch import Phase
        if reply.phase == Phase.APPLIED and (self._generator_requested is None or reply.active == self._generator_requested):
            self._generator_active = reply.active
            self._generator_state_known = True
        self.spectral.bode.confirmed(reply)
        if self.spectral.bode.active:
            state='Activo' if reply.running else ('Finalizado' if reply.active.enabled else 'Apagado')
            self.generator_status.setText(f'{state} · Bode')
            return
        if self.generator_mode.currentIndex() in (4,5): return
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
                self.generator_duty.setValue(c.duty)
                self.generator_duty_dial.setValue(c.duty)
                self.generator_frequency.setValue(c.frequency/1000)
                self.generator_final_frequency.setValue(c.final_frequency/1000)
                self.generator_amplitude.setValue((c.high-c.low)*3.3/4095)
                self.generator_offset.setValue((c.high+c.low)*3.3/8190)
                self._update_generator_offset_bounds()
                self._generator_availability()
                self.generator_duration.setValue(c.duration * (1000 if self._generator_duration_us and not c.duration_us else .001 if c.duration_us and not self._generator_duration_us else 1) if self._generator_duration_ms else c.duration/1000)
                self.generator_enabled.setChecked(bool(c.enabled))
                self.generator_enabled.setText('■ Apagar' if c.enabled else '▶ Encender')
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
        spacing = delta[0] if len(delta) else 0.
        uniform = finite.all() and len(delta) and spacing > 0
        if uniform:
            if np.isfinite(spacing):
                # Same allclose test, reusing the disposable delta array rather
                # than allocating full-size subtraction/absolute/mask arrays.
                np.subtract(delta, spacing, out=delta)
                np.abs(delta, out=delta)
                uniform = np.max(delta) <= 1e-9 + 1e-9 * abs(spacing)
            else:
                uniform = np.allclose(delta, spacing, rtol=1e-9, atol=1e-9)
        if uniform:
            # Uniform hardware samples: block extrema avoid per-point bucket
            # arrays and repeats. Each block is at most one display pixel wide.
            stride = max(1, math.ceil((xmax-xmin)/(pixels*spacing)))
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

    def _last_history_trigger(self, history, start, end, level, rising, hysteresis):
        """Try the recent tail before copying/scanning the whole search window.

        A crossing needs all ten previous samples. Hits in the first ten
        positions of a truncated tail require the full-window fallback too.
        """
        recent_start = max(start, end-2048)
        values = self._window_values(history, recent_start, end)
        index = last_trigger_crossing(values, level, rising, hysteresis)
        if recent_start > start and (index is None or index < 10):
            recent_start = start
            values = self._window_values(history, start, end)
            index = last_trigger_crossing(values, level, rising, hysteresis)
        if index is None:
            return None
        return recent_start+index, values[index-1], values[index]

    def _display_pixels(self, width):
        # Logarithmic range: 0.25 to 8 groups per logical pixel.
        return max(1, int(width * (0.25 * 32 ** (self.detail_slider.value()/99))))

    def _radio_display_values(self, name, values):
        if (name == 'RADIO' and self.generator_mode.currentIndex() == 7
                and hasattr(self, 'radio_output_panel')):
            offset=self.radio_offset.value()
            return 1.65+(np.asarray(values)-offset)*(self.radio_output_panel.volume.value()/100.)
        return values

    def _draw_display_frame(self, x_plot, y_slices, active_columns):
        view = self.plot_widget.getViewBox()
        xmin, xmax = view.viewRange()[0]
        pixels = self._display_pixels(view.width())
        for col, line in self.line_items.items():
            y_vals = y_slices.get(col, [])
            x_values=x_plot.get(col,[]) if isinstance(x_plot,dict) else x_plot
            visible = col in active_columns and len(y_vals) == len(x_values) and len(x_values) > 0
            if visible:
                y_vals=self._radio_display_values(col,y_vals)
                xp, yp = self._display_trace(x_values, y_vals, xmin, xmax, pixels)
                line.setData(xp, yp, connect='finite')
            line.setVisible(visible)
        if hasattr(self,'scope_cursors'):self.scope_cursors.update_frame(x_plot,y_slices,active_columns)

    def _set_temporal_x_label(self, text):
        # Rebuilding an unchanged axis label invalidates its HTML geometry and
        # cached painting on every frame, competing with MIDI delivery in Qt.
        axis=self.plot_widget.getAxis('bottom')
        if axis.labelText!=text or axis.labelStyle.get('color')!='#ffffff':
            self.plot_widget.setLabel('bottom',text,color='#ffffff')

    def _set_temporal_trigger_status(self, text):
        self.trigger_status_label.setText(text)
        style = ('QLabel {background:#171920; border:1px solid #323946; '
                 'border-radius:6px; padding:6px; font-weight:normal; '
                 'font-size:11px; color:#aeb8c8;}')
        if self.trigger_status_label.styleSheet() != style:
            self.trigger_status_label.setStyleSheet(style)

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
        new_cols = [h for h in headers if h in ("CH1", "CH2") and h not in self.known_columns]
        if not new_cols:
            return

        for col in new_cols:
            self.known_columns.append(col)
            if col not in self.series:
                self.series[col] = SampleHistory(self.sample_numbers.maxlen)
            if col not in self.selected_columns:
                self.selected_columns[col] = col in ("CH1", "CH2")

        self._filter_view_changed()

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
            self.spectral._single_snapshot = None
            self.spectral.clear_single_marker()
            self.run_stop_btn.setText("▶ RUN")
            self._set_connection_status("Adquisición en vivo")
            self.status_label.setStyleSheet("""
                QLabel {
                    background:#171920;
                    border:1px solid #323946;
                    border-radius: 6px;
                    padding: 2px 8px;
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
                    padding: 2px 8px;
                    color:#aeb8c8;
                    font-weight:normal;
                    font-size: 11px;
                }
            """)

    def arm_single_shot(self):
        if not hasattr(self, '_trigger_before_single'):
            self._trigger_before_single = self.trigger_checkbox.isChecked()
        self.spectral._single_snapshot = None
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
        if self._analysis_view_active():
            self.spectral.reset_view();self._sync_analysis_controls();return
        self.on_h_scale_changed(VISIBLE_SAMPLES_DEFAULT)
        self.dial_h_pos.setValue(0)
        self.dial_v_scale.setValue(330)
        self.dial_v_pos.setValue(0)
        self.trigger_source_combo.setCurrentText("CH1")
        self.dial_trigger_level.setValue(165)
        self.run_stop_btn.setChecked(True)
        self.toggle_run_stop()

    def _reset_view_dial(self,name):
        if self._analysis_view_active():
            self.spectral.change_view(**{name:1. if name.endswith('scale') else 0.})
            self._sync_analysis_controls()
        elif name=='h_scale':self.on_h_scale_changed(VISIBLE_SAMPLES_DEFAULT)
        elif name=='h_pos':self.dial_h_pos.setValue(0);self.on_h_pos_changed(0)
        elif name=='v_scale':self.dial_v_scale.setValue(330);self.on_v_scale_changed(330)
        elif name=='v_pos':self.dial_v_pos.setValue(0);self.on_v_pos_changed(0)

    def _analysis_view_active(self):
        return hasattr(self,'spectral') and self.spectral.mode!=0

    def _sync_analysis_controls(self):
        if not hasattr(self,'dial_v_pos'):return
        controls=(self.dial_h_scale,self.lbl_h_scale,self.dial_h_pos,self.dial_v_scale,self.lbl_v_scale,self.dial_v_pos)
        blockers=[QtCore.QSignalBlocker(c) for c in controls]
        if self._analysis_view_active():
            view=self.spectral.view_settings()
            self.dial_h_scale.setRange(0,1000)
            fft=self.spectral.mode==1
            self.dial_h_scale.setValue(round((math.log10(view['h_scale'])+2)*1000/(2 if fft else 3)))
            self.lbl_h_scale.setRange(.01,1 if fft else 10);self.lbl_h_scale.setDecimals(2)
            self.lbl_h_scale.setSingleStep(.01);self.lbl_h_scale.setSuffix(' ×')
            self.lbl_h_scale.setValue(view['h_scale'])
            limit=math.floor(max(0.,(1-view['h_scale'])/2)*1000+1e-9) if fft else 1000
            self.dial_h_pos.setRange(-limit,limit);self.dial_h_pos.setValue(round(view['h_pos']*1000))
            self.lbl_h_pos.setText(f'{view["h_pos"]*100:+.1f} %')
            self.dial_v_scale.setRange(1,1000);self.dial_v_scale.setValue(round(view['v_scale']*100))
            self.lbl_v_scale.setRange(.01,10);self.lbl_v_scale.setDecimals(2);self.lbl_v_scale.setSuffix(' ×')
            self.lbl_v_scale.setValue(view['v_scale'])
            self.dial_v_pos.setRange(-1000,1000);self.dial_v_pos.setValue(round(view['v_pos']*1000))
            self.lbl_v_pos.setText(f'{view["v_pos"]*100:+.1f} %')
            self.vertical_scale_title.setText('ESCALA');self.vertical_position_title.setText('POSICIÓN')
            axes=('frecuencia / amplitud, PSD, fase o transferencia','tiempo / frecuencia','frecuencia / ganancia y fase')[self.spectral.mode-1]
            self.dial_h_scale.setToolTip('Ancho relativo del eje horizontal de los gráficos activos: '+axes)
            self.dial_v_scale.setToolTip('Altura relativa del eje vertical; conserva las unidades propias de cada gráfico.')
            self.dial_h_pos.setToolTip('Desplazamiento horizontal como porcentaje del rango completo.')
            self.dial_v_pos.setToolTip('Desplazamiento vertical como porcentaje del rango completo.')
        else:
            self.dial_v_scale.setRange(50,1000);self.dial_v_scale.setValue(round(self.v_scale*100))
            self.lbl_v_scale.setRange(.5,10);self.lbl_v_scale.setSuffix(' V');self.lbl_v_scale.setValue(self.v_scale)
            self.dial_v_pos.setRange(-500,500);self.dial_v_pos.setValue(round(self.v_pos*100))
            self.lbl_v_pos.setText(f'{number(self.v_pos, formats.n_2f)} V')
            self.vertical_scale_title.setText('ESCALA (V)');self.vertical_position_title.setText('POSICIÓN (V)')
            self.dial_h_scale.setToolTip('Ventana temporal visible según FS; recorrido logarítmico.')
            self.dial_v_scale.setToolTip('Altura de la ventana temporal en voltios.')
            self.dial_h_pos.setToolTip('Posición en el historial temporal.')
            self.dial_v_pos.setToolTip('Posición vertical temporal en voltios.')
        for dial in (self.dial_h_scale,self.dial_h_pos,self.dial_v_scale,self.dial_v_pos):
            dial.setToolTip(dial.toolTip()+'\nDoble clic: restablecer este control.')
        del blockers
        if not self._analysis_view_active():self._sync_horizontal_controls()

    def _horizontal_dt_us(self):
        # Prefer sample timestamps; use the confirmed hardware period before DATA.
        return self.current_dt_us if self.current_dt_us > 0 else self.applied_configuration.dt_us

    def _horizontal_sample_limits(self):
        config = getattr(self, 'applied_configuration', Configuration(14,40000))
        return VISIBLE_SAMPLES_MIN, max(VISIBLE_SAMPLES_MAX, math.ceil(4*config.actual_rate))

    def _on_h_scale_dial(self, position):
        if self._analysis_view_active():
            self.spectral.change_view(h_scale=10**(-2+(2 if self.spectral.mode==1 else 3)*position/1000));self._sync_analysis_controls();return
        minimum, maximum = self._horizontal_sample_limits()
        self.on_h_scale_changed(round(minimum*(maximum/minimum)**(position/1000)))

    def _sync_horizontal_controls(self):
        if self._analysis_view_active():self._sync_analysis_controls();return
        dt = self._horizontal_dt_us()
        minimum, maximum = self._horizontal_sample_limits()
        time_mode = self.x_axis_time_mode
        self._horizontal_display_us = time_mode and self.h_scale*dt < 1000
        seconds = time_mode and self.h_scale*dt >= 1000000
        factor = (dt if self._horizontal_display_us else dt/1000000 if seconds else dt/1000) if time_mode else 1
        self._horizontal_display_factor = factor
        with QtCore.QSignalBlocker(self.lbl_h_scale):
            self.lbl_h_scale.setDecimals(3 if seconds else 1 if time_mode else 0)
            self.lbl_h_scale.setRange(minimum * factor, maximum * factor)
            self.lbl_h_scale.setSingleStep(factor)
            self.lbl_h_scale.setSuffix((" µs" if self._horizontal_display_us else " s" if seconds else " ms") if time_mode else " smp")
            self.lbl_h_scale.setValue(self.h_scale * factor)
        with QtCore.QSignalBlocker(self.dial_h_scale):
            position=round(1000*math.log(max(minimum,self.h_scale)/minimum)/math.log(maximum/minimum))
            self.dial_h_scale.setValue(max(0,min(1000,position)))
        with QtCore.QSignalBlocker(self.dial_h_pos):
            self.dial_h_pos.setRange(-maximum,0)
            self.h_pos=max(-maximum,min(0,self.h_pos))
            self.dial_h_pos.setValue(self.h_pos)
        self.on_h_pos_changed(self.h_pos)

    def _on_h_scale_input(self, value):
        if self._analysis_view_active():
            self.spectral.change_view(h_scale=value);self._sync_analysis_controls();return
        samples = round(value / self._horizontal_display_factor) if self.x_axis_time_mode else round(value)
        self.on_h_scale_changed(samples)

    def on_h_scale_changed(self, value: int):
        minimum, maximum = self._horizontal_sample_limits()
        self.h_scale = max(minimum, min(maximum, int(value)))
        self._h_time_ms = self.h_scale * self._horizontal_dt_us() / 1000
        self._sync_horizontal_controls()

    def on_h_pos_changed(self, value: int):
        if self._analysis_view_active():
            self.spectral.change_view(h_pos=value/1000);self._sync_analysis_controls();return
        self.h_pos = int(value)
        if self.x_axis_time_mode:
            text = f"{number(self.h_pos * self._horizontal_dt_us() / 1000, formats.n_1f)} ms"
        else:
            text = f"{self.h_pos} smp"
        self.lbl_h_pos.setText(text + (" (En vivo)" if self.h_pos == 0 else ""))

    def on_v_scale_changed(self, value: int):
        if self._analysis_view_active():
            self.spectral.change_view(v_scale=value/100);self._sync_analysis_controls();return
        self.v_scale = max(0.2, value / 100.0)
        self.lbl_v_scale.setValue(self.v_scale)
        self._apply_vertical_range()

    def on_v_pos_changed(self, value: int):
        if self._analysis_view_active():
            self.spectral.change_view(v_pos=value/1000);self._sync_analysis_controls();return
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
        elif self._is_audio_channel(source):
            self.dial_trigger_level.setRange(-330, 330)
            self.dial_trigger_level.setValue(0)
            self.trigger_level = 0.0
            self.lbl_trigger_level.setText("0.00 V")
            self.trigger_line.setValue(0)
        else:
            self.dial_trigger_level.setRange(0, 330)
            self.dial_trigger_level.setValue(165)
            self.trigger_level = 1.65
            self.lbl_trigger_level.setText("1.65 V")
            self.trigger_line.setValue(self.trigger_level)
        self._updating_trigger_line = False
        self.configure_trigger()

    def _update_trigger_plot_label(self, *args):
        self.trigger_line.label.setFormat('Trig: '+number(self.trigger_line.value(),formats.n_2f)+' V')

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
            self.trigger_level = max(-3.3 if self._is_audio_channel(self.trigger_source) else 0.0, min(3.3, new_val))
            self.lbl_trigger_level.setText(f"{number(self.trigger_level, formats.n_2f)} V")
            self.dial_trigger_level.setValue(int(round(self.trigger_level * 100)))
        self._updating_trigger_line = False

    def auto_center_trigger_level(self):
        """Calcula el punto medio (50%) de la señal activa y centra el nivel de disparo automáticamente."""
        source = self.trigger_source
        audio = self._is_audio_channel(source)
        if audio and self.radio_stream is None:return
        histories = self.radio_stream.series if audio and self.radio_stream is not None else self.series
        src_deque = histories.get(source)
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
            self.trigger_level = max(-3.3 if audio else 0.0, min(3.3, v_mid))
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
        folder = ROOT/'capturas/v18'
        folder.mkdir(parents=True, exist_ok=True)
        rate = f'{self.applied_configuration.rate / 1000:g}kHz'
        stem = datetime.now().strftime('log_%Y%m%d_%H%M%S') + f'_{self.applied_configuration.bits}bit_{rate}'
        candidate = stem
        number = 2
        while any((folder/f'{candidate}.{ext}').exists() for ext in ('csv', 'wav')):
            candidate = f'{stem}_{number}'
            number += 1
        return folder/f'{candidate}.{self.record_format.lower()}'

    def _wav_recording_allowed(self):
        config = self.applied_configuration
        common = config.rate in (1000, 5000, 10000, 20000, 31250, 40000)
        audio = (config.bits == 16 and config._native and
                 ((config._native.get('purpose') == 'audio' and
                   config._native.get('validation') == '60s') or
                  (config.rate == 76226 and config._native.get('headroom'))))
        return not self.demo_mode and bool(common or audio)

    def _sync_record_availability(self):
        if not hasattr(self, 'record_btn'):
            return
        wav = self.record_format_combo.currentText() == 'WAV'
        allowed = not wav or self._wav_recording_allowed()
        self.record_btn.setEnabled(not self.recording and allowed)
        self.record_dc_checkbox.setEnabled(wav and allowed and not self.recording)
        self.record_btn.setToolTip('Iniciar grabación, máximo 30 segundos' if allowed else
                                  'WAV admite FS comunes hasta 40 kHz en todos los bits y ADC16 a 44,1/48/76,226 kHz; para otras FS usá CSV.')

    def _record_format_changed(self, selected):
        self._sync_record_availability()
        if hasattr(self, "record_dc_checkbox"):
            self.record_dc_checkbox.setEnabled(selected == "WAV" and self._wav_recording_allowed() and not self.recording)
        if not self.recording:
            self.record_status_label.setText(f"{selected}: listo | máximo 30.0 s")

    def start_recording(self):
        if self.recording:
            return
        if self.record_format_combo.currentText() == "WAV" and not self._wav_recording_allowed():
            QtWidgets.QMessageBox.warning(self, "Grabación WAV", "WAV admite FS comunes hasta 40 kHz en todos los bits y ADC16 a 44,1/48/76,226 kHz. Para otras FS usá CSV.")
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
                self.record_wave.setparams((self.applied_configuration.channels, 2, self.applied_configuration.rate, 0, "NONE", "not compressed"))
            else:
                self.record_file = path.open("w", encoding="utf-8", newline="", buffering=1024 * 1024)
                self.record_writer = csv.writer(self.record_file, delimiter=",")
                self.record_writer.writerow(["Muestra", "Tiempo_us", "CH1", "FILTER"] if self.applied_configuration.channels==1 else ["Muestra", "Tiempo_us", "CH1", "CH2", "FILTER"])
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
            rows = [[s.get("Muestra", ""), s.get("Tiempo (us)", ""), s.get("CH1", ""), s.get("CH2", ""), s.get("FILTER", "")] for s in batch]
            if self.applied_configuration.channels==1: rows=[row[:3]+row[4:] for row in rows]
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
        data = (np.column_stack([batch.columns[name] for name in ("Muestra","Tiempo (us)","CH1","CH2")])
                if isinstance(batch,NumericBatch) else np.array([[s["Muestra"], s["Tiempo (us)"], s["CH1"], s["CH2"]] for s in batch], dtype=np.float64))
        if self.applied_configuration.channels==1: data=data[:,[0,1,2]]
        integral=data[:,:1] if self.applied_configuration._native else data[:,:2]
        if not np.isfinite(data).all() or not np.equal(integral,np.floor(integral)).all():
            raise ValueError("WAV: muestras o timestamps inválidos")
        if np.any(data[:, 2:] < 0) or np.any(data[:, 2:] > 3.3):
            raise ValueError("WAV: canal fuera del rango de tensión")
        if self.applied_configuration._native:
            positions=data[:,:2].copy()
            if self.record_previous is not None: positions=np.vstack((self.record_previous,positions))
            differences=np.diff(positions,axis=0)
            valid=(np.all((differences[:,0].astype(np.int64)&0xffffffff)==1)
                   and np.all(np.abs(differences[:,1]-self.applied_configuration.dt_us)<1e-6))
        else:
            positions=data[:,:2].astype(np.int64)
            if self.record_previous is not None: positions=np.vstack((self.record_previous,positions))
            differences=np.diff(positions,axis=0)&0xffffffff
            valid=np.all(differences[:,0]==1) and np.all(differences[:,1]==self.applied_configuration.period)
        if not valid: raise ValueError("WAV: discontinuidad de muestras o timestamps")
        audio = data[:, 2:] * (65535.0 / 3.3) - 32768.0
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
        self._sync_record_availability()
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
        duration = self.h_scale * self._horizontal_dt_us() / 1000
        channel_combos=list(dict.fromkeys([
            *self.findChildren(QtWidgets.QComboBox),
            *self.spectral.channels,
            self.spectral.transfer_reference,self.spectral.transfer_response,
        ]))
        was_single=self.applied_configuration.channels==1
        single=config.channels==1
        if single and not was_single:
            self._dual_channel_choices={combo:combo.currentText() for combo in channel_combos if combo.findText("CH2")>=0}
            self._dual_ch2_visible=self.graph_channel_actions["CH2"].isChecked()
        if config != self.applied_configuration:
            if self.recording: self.stop_recording()
            self.clear_data()
            for curve in self.line_items.values(): curve.setData([], [])
            for label in (self.val_vmax,self.val_vmin,self.val_vpp,self.val_vrms,self.val_vavg,self.val_freq): label.setText('--')
        self.applied_configuration = config
        self._sync_radio_input_controls()
        self._sync_record_availability()
        self.current_dt_us = config.dt_us
        self.current_fs_hz = config.actual_rate
        minimum, maximum = self._horizontal_sample_limits()
        capacity=max(MAX_BUFFER_SAMPLES,maximum+260000)
        self.sample_numbers.resize(capacity)
        for history in self.series.values(): history.resize(capacity)
        # Measurement choices are rebuilt for the new profile before restoring
        # selections; CH2 is removed from this combo in single-channel mode.
        self.spectral.refresh_measurement_panel()
        for combo in channel_combos:
            index=combo.findText('CH2')
            if index>=0:
                combo.model().item(index).setEnabled(not single)
                if single and combo.currentText()=='CH2':combo.setCurrentText('CH1')
                elif not single and was_single:combo.setCurrentText(getattr(self,'_dual_channel_choices',{}).get(combo,combo.currentText()))
        if single and not was_single:
            self.spectral.channels[1].setCurrentText('Ninguno')
        action=self.graph_channel_actions.get('CH2')
        if action is not None:
            action.setEnabled(not single)
            if single:action.setChecked(False)
            elif was_single:action.setChecked(getattr(self,"_dual_ch2_visible",True))
        self._filter_changed()
        self.h_scale = max(minimum, min(maximum, round(duration * 1000 / config.dt_us)))
        self._h_time_ms = self.h_scale * config.dt_us / 1000
        self._sync_horizontal_controls()
        self.spectral.bode.update_estimate()
        self.spectral.bode.refresh_reference()
        self.adc_combo.setCurrentText(f'{bits} bits ({(1 << bits)-1})')
        self.adc_summary_label.setText(f'{bits} bits')
        self._refresh_applied_summary()

        worker=self.serial_worker
        if worker is not None and hasattr(worker,'confirm_startup'):
            worker.confirm_startup(bits,rate)

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
        self.confirmed_output_label.setText(f'{name} · '+f'{config.bits} bits' + (' OS ×16' if config.bits == 16 else '') + ' · ' + _rate_label(config.rate) + (' (CH1)' if config.channels==1 else ''))
        self._set_connection_status('Adquisición en vivo' if self.is_running else 'Pantalla congelada (STOP)')

    def _destination_changed(self):
        if hasattr(self, 'config_rate_combo'):
            uart = self.destination_combo.currentData() == int(Mode.UART)
            synth=hasattr(self,'generator_mode') and self.generator_mode.currentIndex()==5
            for i in range(self.config_rate_combo.count()):
                rate = self.config_rate_combo.itemData(i)
                bits = self.config_bits_combo.currentData()
                valid = _configuration_supported(bits, rate)
                allowed = valid and (not uart or rate in UART_RATES) and (not synth or rate<=40000)
                self.config_rate_combo.model().item(i).setEnabled(allowed)
                self.config_rate_combo.view().setRowHidden(i, not allowed)
                label = _rate_label(rate)
                if valid:
                    label += ' · ' + _period_label(Configuration(bits, rate).dt_us)
                if valid:
                    profile = Configuration(bits, rate)
                    acquisition = f'{number(profile.sampling_us, formats.n_1f)}'
                    tooltip = (f'Período entre muestras: {_period_label(profile.dt_us)}.\n'
                               f'Adquisición por canal y subconversión: {acquisition} µs '
                               f'({profile.sampling_cycles} ciclos ADC).\n'
                               + ('16 subconversiones por canal.\n' if bits == 16 else '')
                               + 'Menor tiempo de adquisición exige menor impedancia de fuente.')
                    if profile._native and profile._native.get('purpose'):
                        tooltip += f'\nTasa real: {number(profile.actual_rate, formats.n_2f)} Hz por canal.'
                        tooltip += '\nPerfil adicional: ensayo físico de 60 s; aceptación prolongada y precisión analógica pendientes.' if profile._native.get('validation')=='60s' else '\nPerfil adicional: validación física pendiente.'
                    elif profile._native and profile._native.get('validation')=='isolated_60s_3x120s':
                        tooltip += ('\nCH1: integridad validada en firmware aislado (60 s + 3×120 s). '
                                    + ('Holgura aislada validada.' if profile._native.get('isolated_headroom') else 'Sin holgura aislada validada.')
                                    + '\nValidación integrada y precisión analógica pendientes.')
                    elif profile._native:
                        tooltip += ('\nIntegridad física validada; '
                                    + ('margen validado.' if profile._native['headroom'] else 'sin margen validado.')
                                    + '\nPrecisión analógica pendiente.')
                        if profile._native.get('validation')=='production_60s_3x120s':
                            tooltip += '\nValidación integrada: 60 s + 3×120 s, sin ensayo de 600 s.'
                    elif rate > 125000:
                        tooltip += '\nIntegridad física ensayada; precisión analógica y margen de cola pendientes.'
                    if profile.channels==1:
                        label=_rate_label(rate) + ' (CH1)'
                    if profile._native and profile._native.get('integrity_only'):
                        tooltip += '\nSin holgura validada. Cola de 8 nodos; preparación automática de 2 s.'
                else:
                    tooltip = 'Esta tasa no admite la resolución seleccionada.'
                self.config_rate_combo.setItemText(i, label)
                self.config_rate_combo.setItemData(i, tooltip, QtCore.Qt.ItemDataRole.ToolTipRole)
            if not _configuration_supported(self.config_bits_combo.currentData(), self.config_rate_combo.currentData()):
                fallback = 40000
                self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(fallback))
            if synth and self.config_rate_combo.currentData()>40000:
                self.config_rate_combo.setCurrentIndex(self.config_rate_combo.findData(40000))
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
        if not pending and self.generator_mode.currentIndex()==5 and self.applied_configuration.rate>40000:
            self._schedule_configuration()
        if not pending and self.serial_worker is not None and getattr(self, "confirmed_mode", None) is not None:
            self._refresh_applied_summary()

    def _output_confirmed(self, mode, r4_port):
        self._set_connect_state('connected')
        self.confirmed_mode, self.confirmed_r4 = mode, r4_port
        self.control_summary_label.setText(str(self.port_combo.currentData()))
        self.baud_input.setText('SPI' if mode == int(Mode.SPI) else 'UART 3M')
        self._refresh_applied_summary()

    def _schedule_configuration(self):
        if getattr(getattr(self,'_radio_multiscan',None),'active',False):return
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
        if getattr(getattr(self,'_radio_multiscan',None),'active',False):return
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
        self.connect_button.setIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets' / f'plug_{state}.svg')))
        self.connect_button.setIconSize(QtCore.QSize(18, 18))
        labels = {'disconnected': 'Conectar', 'connecting': 'Conectando…', 'connected': 'Desconectar'}
        self.connect_button.setText('  ' + labels[state])
        self.connect_button.setToolTip('Cancelar conexión' if state == 'connecting' else labels[state])

    def prepare_q(self):
        if self._q_preparation is not None and self._q_preparation.isRunning():
            return
        if self.serial_worker is not None or self.demo_mode:
            self._set_connection_status('Desconectar la adquisición antes de Preparar Q.')
            return
        serial = self.port_combo.currentData()
        if not serial:
            self._set_connection_status('Seleccionar el UNO Q por USB antes de Preparar Q.')
            return
        self._begin_q_preparation(serial)

    def _begin_q_preparation(self, serial):
        self._q_preparation = QPreparationThread(serial, self)
        for widget in (self.connect_button, self.demo_button, self.port_combo,
                       self.refresh_button, self.prepare_q_button):
            widget.setEnabled(False)
        self._q_preparation.progress.connect(self._set_connection_status)
        self._q_preparation.result.connect(self._q_prepared)
        self._q_preparation.finished.connect(self._q_preparation_finished)
        self._set_connection_status('Verificando Scope V18…')
        self._q_preparation.start()

    def _q_prepared(self, success, text):
        self._set_connection_status(text)

    def _q_preparation_finished(self):
        thread, self._q_preparation = self._q_preparation, None
        for widget in (self.connect_button, self.demo_button, self.port_combo, self.refresh_button):
            widget.setEnabled(True)
        self.prepare_q_button.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

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
        self._shutdown_status = None
        self.serial_thread = QtCore.QThread()
        self.serial_worker = OutputWorker(port, mode, r4_port, Configuration(
            self.config_bits_combo.currentData(), self.config_rate_combo.currentData()),
            autoload=True,
            initial_generator=self._generator_config() if self.generator_mode.currentIndex() == 0 else None,
            processing_settings=self._processing_settings(), startup_gui_ack=True, processing_backend='process')
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        worker = self.serial_worker
        self.serial_worker.batch_ready.connect(lambda batch: self._deliver_worker_batch(worker,batch))
        self.serial_worker.headers_detected.connect(lambda headers: self._from_worker(worker, self.on_headers_detected, headers))
        self.serial_worker.status_changed.connect(lambda text: self._from_worker(worker, self._set_connection_status, text))
        self.serial_worker.output_confirmed.connect(lambda mode, r4: self._from_worker(worker, self._output_confirmed, mode, r4))
        self.serial_worker.acquisition_confirmed.connect(lambda bits, rate: self._from_worker(worker, self._acquisition_confirmed, bits, rate))
        self.serial_worker.trace_configuration_ready.connect(lambda event: self._from_worker(worker,self._trace_configuration_installed,worker,event))
        self.serial_worker.generator_confirmed.connect(lambda reply: self._from_worker(worker, self._generator_confirmed, reply))
        self.serial_worker.instrument_confirmed.connect(lambda identity: self._from_worker(worker, self.spectral.bode.set_instrument, identity))
        self.serial_worker.wav_confirmed.connect(lambda reply: self._from_worker(worker, self._wav_confirmed, reply))
        self.serial_worker.switching.connect(lambda pending: self._from_worker(worker, self._set_output_pending, pending))
        self.serial_worker.error_occurred.connect(lambda text: self._from_worker(worker, self._on_worker_error, text))
        self.serial_worker.shutdown_confirmed.connect(lambda ok, text: self._from_worker(worker, self._output_shutdown_result, ok, text))
        self.serial_worker.finished.connect(self.serial_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        # Keep references until the asynchronous shutdown has finished.
        self.port_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self._set_output_pending(True)
        self._set_connect_state('connecting')
        self.serial_thread.start()
        self.connect_button.setEnabled(True)
        self.demo_button.setEnabled(False)

    def _from_worker(self, worker, callback, *args):
        # Qt may deliver queued signals after the old worker finished.
        if worker is self.serial_worker:
            callback(*args)

    def _trace_configuration_installed(self,worker,event):
        generation,bits,rate=event
        if (self.applied_configuration.bits,self.applied_configuration.rate)==(bits,rate):
            worker.trace.record(generation,'gui_configuration_installed',once=True)

    def _note_gui_callback(self, name, began):
        elapsed=time.perf_counter()-began
        if elapsed>=.02:
            ring=getattr(self,'_gui_slow_callbacks',None)
            if ring is not None:ring.append((name,time.monotonic(),elapsed*1000))

    def _render_with_diagnostics(self):
        handle=self.windowHandle()
        if handle is not None and not handle.isExposed() and not self.single_shot_armed:
            # Acquisition/history delivery has its own callbacks. Avoid copying
            # and drawing unseen traces; SINGLE still runs its capture path.
            return
        worker=getattr(self,'serial_worker',None)
        if worker is not None and not self.single_shot_armed and worker.ready_gui_batches()>=2:
            # Drain queued complete histories before copying them for another
            # paint. Acquisition/DSP and SINGLE remain independent of painting.
            return
        self.radio_output_panel.refresh_meter(time.monotonic())
        began=time.perf_counter()
        try:self.render_frame()
        finally:self._note_gui_callback('render_frame',began)
        began=time.perf_counter()
        try:self.spectral.render()
        finally:self._note_gui_callback('spectral.render',began)
        if hasattr(self,'scope_cursors') and self.spectral.mode!=0 and any(s.enabled for s in self.scope_cursors.states):self.scope_cursors.analysis_changed()

    def _deliver_worker_batch(self,worker,batch):
        started=time.perf_counter()
        try:
            if worker is self.serial_worker:
                self.batch_pending_peak=max(getattr(self,'batch_pending_peak',0),getattr(batch,'pending_batches',0))
                self._from_worker(worker,self.handle_batch,batch)
                trace=getattr(worker,'trace',None)
                if (trace is not None and trace.enabled and
                        getattr(batch,'acquisition',None)==getattr(self,'applied_configuration',None)):
                    trace.record(getattr(batch,'startup_trace_generation',None),'first_gui_batch_accepted',once=True)
        finally:
            worker.batch_consumed(batch)
            SerialMonitorWindow._note_gui_callback(self,'handle_batch',started)
        elapsed=(time.perf_counter()-started)*1000
        self.batch_processing_peak_ms=max(getattr(self,'batch_processing_peak_ms',0),elapsed)
        self.batch_processing_total_ms=getattr(self,'batch_processing_total_ms',0)+elapsed
        self.batch_processing_count=getattr(self,'batch_processing_count',0)+1

    def _output_shutdown_result(self, success, text):
        self._shutdown_status = (success, text)
        if not success:
            self._set_connection_status(text)
            print(text, file=sys.stderr)

    def _save_delivery_failure(self, message):
        if 'atrasad' not in message.lower():
            return None
        import json
        worker=self.serial_worker
        snapshot=dict(getattr(worker,'delivery_failure_snapshot',None) or {})
        scan=getattr(self,'_radio_multiscan',None)
        snapshot.update(error=message,time=datetime.now().isoformat(),
            bits=self.applied_configuration.bits,rate=self.applied_configuration.rate,
            radio_playing=self.radio_enabled.isChecked(),us=self.radio_us.isChecked(),
            scan_pending=self._radio_scan_future is not None,multiscan_active=bool(scan and scan.active),
            scan_status=self.radio_status.text(),a0_active=self._wav_active,
            analysis_mode=self.spectral.mode,fft_mode=self.spectral.fft_mode.currentText(),
            fft_size=self.spectral.size.currentText(),heatmap_size=self.spectral.heatmap_size.currentText(),
            filter_source=self.filter_source.currentText(),gui_delay_max_ms=self.batch_queue_delay_max_ms,
            window_visible=self.isVisible(),window_minimized=self.isMinimized(),
            wav_path=self.wav_path,wav_rate=self.wav_rate.currentData(),
            wav_preparing=self._wav_preparing,wav_active=self._wav_active,
            wav_dialog_open=getattr(self,'_wav_file_dialog',None) is not None,
            slow_gui_callbacks=list(getattr(self,'_gui_slow_callbacks',())),
            selected_columns=dict(self.selected_columns),horizontal_samples=self.h_scale,
            trigger_enabled=self.trigger_enabled,trigger_source=self.trigger_source,
            detail=self.detail_slider.value(),trace_style=self.trace_style_combo.currentText())
        path=ROOT/'diagnosticos/resultados_v18'/('gui_overload_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(snapshot,indent=2)+'\n')
        except OSError as exc:
            print(f'No se pudo guardar diagnóstico GUI: {exc}',file=sys.stderr)
            return None
        return path

    def _on_worker_error(self, message: str):
        self._save_delivery_failure(message)
        self._finish_radio_scan_a0(False)
        scan=getattr(self,'_radio_multiscan',None)
        if scan is not None and scan.active:
            scan.error=f'Flujo interrumpido: {message}; restauración no confirmada'
            scan.timer.stop();scan.active=False;scan.future=None
            for widget,enabled in zip(scan.widgets,scan.enabled):widget.setEnabled(enabled)
            self.radio_status.setText(scan.error)
        self.stop_input()
        self._set_connection_status(f"Error: {message}")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 2px 8px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)
        QtWidgets.QMessageBox.critical(self, "Error de conexión", message)

    def start_demo(self):
        if self.stop_input() is False:
            QtCore.QTimer.singleShot(100, self.start_demo)
            return
        self.clear_data()
        self.demo_mode = True
        self._sync_record_availability()
        self._filter_changed()
        self.start_time = time.perf_counter()
        self.demo_ch2_prev = 0.0
        self._set_connection_status("Demo activo · CH1 cuadrada / CH2 filtro RC")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 2px 8px;
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
        """Genera simulación de 2 canales: CH1 (Generador) y CH2 (Respuesta de circuito RC)."""
        batch = []
        dt = 0.0004  # 2.5 kHz
        t_base = self.sample_counter * dt
        tau = 0.035  # Constante de tiempo RC (35 ms)

        for i in range(50):
            t = t_base + i * dt
            period = 0.4  # 2.5 Hz onda cuadrada
            phase = (t % period) / period

            # CH1: Señal cuadrada limpia entre 0.1V y 3.2V
            ch1 = 3.2 if phase < 0.5 else 0.1

            # CH2: Respuesta analógica exponencial del condensador RC
            alpha = dt / (tau + dt)
            self.demo_ch2_prev += alpha * (ch1 - self.demo_ch2_prev)
            ch2 = max(0.0, min(3.3, self.demo_ch2_prev))

            sample = {
                "Muestra": float(self.sample_counter + i + 1),
                "Tiempo (us)": float(int(t * 1_000_000)),
                "CH1": ch1,
                "CH2": ch2,
            }
            batch.append(sample)

        self.handle_batch(batch)

    def stop_input(self, wait=True):
        self._finish_radio_scan_a0(False)
        scan=getattr(self,'_radio_multiscan',None)
        if scan is not None and scan.active:
            scan.error='Scan cancelado para cerrar; restaurando adquisición'
            if not scan.restoring:scan.restore()
            return False
        if hasattr(self,'radio_output_panel'):self.radio_output_panel.stop()
        self.spectral.bode.cancel('Control desconectado: no se pudo restaurar el generador', restore=False)
        self._generator_state_known=False
        self._wav_capable=False
        self._wav_active=False
        if hasattr(self,'fm_panel'):
            self.fm_panel.source=None
            self.fm_panel.play.setText('Play')
        self._wav_cancelled=True
        self._sync_wav_transport()
        self._auto_apply_timer.stop()
        self._generator_timer.stop()
        self._generator_requested=None
        self.generator_status.setText("Control Q desconectado")
        if self.recording:
            self.stop_recording()
        self.demo_mode = False
        self._sync_record_availability()
        if self.demo_timer is not None and self.demo_timer.isActive():
            self.demo_timer.stop()
        if self.serial_worker is not None:
            self.serial_worker.stop()
        if self.serial_thread is not None and self.serial_thread.isRunning():
            self.serial_thread.quit()
            self.connect_button.setEnabled(False)
            self.demo_button.setEnabled(False)
            if not hasattr(self, '_disconnect_started'):
                self._disconnect_started = time.monotonic()
            self._set_connection_status('Desconexión demorada; estado del Q sin confirmar. Esperando worker…'
                if time.monotonic()-self._disconnect_started > 15 else
                'Desconectando Q; esperando apagado de salida…')
            if wait and not getattr(self, '_disconnect_retry_pending', False):
                self._disconnect_retry_pending = True
                def finish_disconnect():
                    self._disconnect_retry_pending = False
                    if self.stop_input() is not False and getattr(self, '_close_pending', False):
                        self.close()
                QtCore.QTimer.singleShot(100, finish_disconnect)
            return False
        if self.serial_thread is not None:
            self.serial_thread.deleteLater()
            self.serial_thread = None

        if hasattr(self, '_disconnect_started'): del self._disconnect_started
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
        shutdown = getattr(self, '_shutdown_status', None)
        self._set_connection_status(shutdown[1] if shutdown and not shutdown[0] else "Detenido")
        self.status_label.setStyleSheet("""
            QLabel {
                background:#171920;
                border:1px solid #323946;
                border-radius: 6px;
                padding: 2px 8px;
                color:#aeb8c8;
                font-weight:normal;
                font-size: 11px;
            }
        """)

    def clear_data(self):
        self._reset_processing_settings()
        self.digital_filter.reset()
        if hasattr(self,'radio_candidates'):
            self.radio_candidates=[];self._radio_scan_generation+=1
            self._update_radio_bandwidth_suggestion()
            self.spectral.refresh_radio_overlay()
            self.radio_frequency_dial.setPeakFrequencies(())
            self._radio_scan_not_before_sample=-1
            self.radio_peak_previous.setEnabled(False);self.radio_peak_next.setEnabled(False)
        self.radio_stream=None;self.radio_key=None;self.radio_filter.reset()
        self.spectral.bode.cancel('Adquisición reiniciada')
        self.spectral._single_snapshot = None
        self.spectral.reset()
        self._last_display_frame = None
        if hasattr(self,"scope_cursors"):self.scope_cursors.invalidate()
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
                self.h_scale = max(VISIBLE_SAMPLES_MIN, min(self._horizontal_sample_limits()[1], round(duration * 1000 / self._horizontal_dt_us())))
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
        # Convert once; hardware batches already contain contiguous numeric columns.
        size=len(batch)
        if isinstance(batch,NumericBatch):
            columns=batch.columns
        else:
            names=set().union(*(sample.keys() for sample in batch))
            columns={name:np.fromiter((sample.get(name,0.0) for sample in batch),dtype=float,count=size) for name in names}
        rate=2500 if self.demo_mode else self.applied_configuration.actual_rate
        result=getattr(batch,'processing',None)
        if result is not None:
            if result['generation']==self._processing_generation:
                self._accept_processed_radio(result)
                self.dsp_timings=result['timings']
            else:
                # Preserve raw acquisition/recording; obsolete derived data cannot
                # repopulate a timeline after controls or acquisition reset it.
                columns.pop('FILTER',None)
                if self.filter_config.source in ('CH1','CH2'):
                    columns['FILTER']=np.full(size,np.nan)
        else:
            self._process_radio(columns)
            if self.filter_config.source in ('CH1','CH2'):
                columns['FILTER']=self.digital_filter.process(columns[self.filter_config.source],rate,self.filter_config,
                    columns.get('Muestra'),columns.get('Tiempo (us)'))
            else:columns.pop('FILTER',None)
        if isinstance(batch,NumericBatch):
            derived=batch
        else:
            derived=([dict(sample,FILTER=float(value)) for sample,value in zip(batch,columns['FILTER'])]
                     if 'FILTER' in columns else batch)
        self._write_record_batch(derived)
        self.sample_numbers.extend(np.arange(self.sample_counter+1,self.sample_counter+size+1,dtype=float))
        self.sample_counter+=size
        for name in columns:
            if name not in self.series:self.series[name]=SampleHistory(self.sample_numbers.maxlen)
        for name,history in self.series.items():
            if name=='FILTER' and name not in columns:continue
            history.extend(columns[name] if name in columns else np.zeros(size))
        if self.spectral.bode.active:self.spectral.bode.batch(derived)

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

    def _is_audio_channel(self, name):
        return name == 'RADIO' or (name == 'FILTER' and self.filter_source.currentText() == 'RADIO')

    def _render_mixed_temporal(self,channels,audio_names):
        stream=self.radio_stream
        rf_times=self.series.get('Tiempo (us)')
        if stream is None or len(stream.sample_numbers)<2 or rf_times is None or len(rf_times)<2:
            # Keep acquired RF visible while audio is preparing/unavailable.
            if rf_times is not None and len(rf_times)>1:
                total=len(rf_times);end=max(2,min(total,total+self.h_pos));start=max(0,end-self.h_scale)
                times=rf_times.window(start,end)
                x=(times-times[0]) if self.x_axis_time_mode else np.arange(len(times),dtype=float)
                values={name:self.series[name].window(start,end) for name in channels if name not in audio_names and name in self.series and len(self.series[name])==total}
                if self.selection_dirty:self._update_curve_items(channels)
                self.plot_widget.setXRange(float(x[0]),max(float(x[-1]),1.),padding=0)
                self._last_display_frame=(x,values,tuple(channels));self._draw_display_frame(*self._last_display_frame)
                self.lbl_top_fs.setText('RF activa · preparando RADIO')
            return
        config=self.applied_configuration
        duration=self.h_scale*1e6/config.actual_rate
        audio_times=stream.series['Tiempo (us)']
        common_end=min(float(rf_times[-1]),float(audio_times[-1]))
        common_start=max(float(rf_times[0]),float(audio_times[0]))
        right=common_end+self.h_pos*1e6/config.actual_rate
        left=right-duration
        trigger_time=None
        domains={name:(stream.series,stream.rate) if name in audio_names else (self.series,config.actual_rate) for name in channels}
        if self.trigger_enabled or self.single_shot_armed:
            source=self.trigger_source
            histories,rate=(stream.series,stream.rate) if source in audio_names else (self.series,config.actual_rate)
            history=histories.get(source);clock=histories.get('Tiempo (us)')
            pre=duration*.1
            post=duration-pre
            if history is not None and clock is not None and len(history)==len(clock):
                count=min(len(clock),max(3000,int(rate*(duration*4+.05))))
                times=clock.window(len(clock)-count,len(clock))
                values=history.window(len(history)-count,len(history))
                rising=self.trigger_edge=='Ascendente';level=self.trigger_level
                # Tiny noise can cross the level thousands of times without ever
                # reaching the trigger hysteresis. Reject that case in one pass.
                reaches_hysteresis=(np.min(values)<=level-.015 if rising else np.max(values)>=level+.015)
                crosses=(np.flatnonzero(((values[1:]>=level)&(values[:-1]<level)) if rising else ((values[1:]<=level)&(values[:-1]>level)))+1) if reaches_hysteresis else np.empty(0,dtype=int)
                if len(crosses):
                    fractions=(level-values[crosses-1])/(values[crosses]-values[crosses-1])
                    crossings=times[crosses-1]+fractions*(times[crosses]-times[crosses-1])
                    eligible=(crossings>=common_start+pre)&(crossings<=common_end-post)
                    candidates=crosses[eligible]
                    # Each prior sample belongs to at most ten crossing windows.
                    # Avoid a Python loop even when isolated outliers enable noise crossings.
                    hysteresis=np.zeros(len(candidates),dtype=bool)
                    for back in range(1,11):
                        indices=candidates-back
                        valid=indices>=0
                        prior=values[np.maximum(indices,0)]
                        hysteresis |= valid & ((prior<=level-.015) if rising else (prior>=level+.015))
                    accepted=np.flatnonzero(hysteresis)
                    if len(accepted):
                        trigger_time=float(crossings[eligible][accepted[-1]])
                        left=trigger_time-pre;right=trigger_time+post
            if trigger_time is None and (self.trigger_mode=='Normal' or self.single_shot_armed):
                self.trigger_status_label.setText('● Esperando disparo · vista RF/audio')
                return
            self.trigger_status_label.setText('⚡ Disparo · vista RF/audio' if trigger_time is not None else '● Auto · buscando disparo RF/audio')
        origin=trigger_time if trigger_time is not None else left
        factor=1. if self.x_axis_time_mode else config.actual_rate/1e6
        x_values={};y_values={};measurement=None;clock_windows={}
        for name,(histories,rate) in domains.items():
            clock=histories.get('Tiempo (us)');history=histories.get(name)
            if clock is None or history is None or len(clock)!=len(history):continue
            key=id(clock)
            if key not in clock_windows:
                a=clock.searchsorted(left,'left');b=clock.searchsorted(right,'right')
                selected=clock.window(a,b)
                clock_windows[key]=(a,b,selected,(selected-origin)*factor)
            a,b,selected,x=clock_windows[key]
            values=history.window(a,b)
            x_values[name]=x;y_values[name]=values
            if name==self.active_meas_channel:measurement=(values,selected,rate)
        if self.selection_dirty:self._update_curve_items(channels)
        self.plot_widget.setXRange((left-origin)*factor,(right-origin)*factor,padding=0)
        self._set_temporal_x_label('Tiempo común RF/audio (µs)' if self.x_axis_time_mode else 'Muestras equivalentes CH1 · RF/audio')
        self.trigger_t_marker.setValue(0);self.trigger_t_marker.setVisible(trigger_time is not None)
        self._last_display_frame=(x_values,y_values,tuple(channels))
        self._draw_display_frame(*self._last_display_frame)
        self.lbl_top_fs.setText(f'RF {config.actual_rate/1e6:.4f} MHz · RADIO {stream.rate/1000:g} kS/s')
        if measurement is not None:
            values,times,rate=measurement
            self._update_live_measurements({self.active_meas_channel:values,'Tiempo (us)':times},[self.active_meas_channel],sample_rate=rate)
        if trigger_time is not None and self.single_shot_armed:
            self.frozen_frame=(x_values,y_values);self.single_shot_armed=False
            self._set_single_state('captured');self.is_running=False
            self.run_stop_btn.setChecked(False);self.run_stop_btn.setText('⏹ STOP')

    def _render_radio_audio(self,channels,audio_names):
        stream=self.radio_stream
        if set(channels)-audio_names or stream is None or stream.counter<2:
            for curve in self.line_items.values():curve.setData([],[])
            self.lbl_top_fs.setText('RADIO: seleccionar sólo canales audio' if set(channels)-audio_names else 'RADIO sin muestras')
            return
        context=(id(stream),tuple(channels),self.trigger_source,self.h_scale,self.h_pos)
        if context!=getattr(self,'_radio_display_context',None):
            self.frozen_frame=None
            self._radio_display_context=context
        if self.selection_dirty:self._update_curve_items(channels)
        count=min(len(stream.sample_numbers),self.h_scale)
        total=len(stream.sample_numbers)
        end=max(count,min(total,total+self.h_pos))
        start=end-count
        pre=max(0,min(count-1,int(count*.1)-self.h_pos))
        found=None
        trigger_shift=0.0
        if self.trigger_enabled or self.single_shot_armed:
            if self.trigger_source not in audio_names:
                self.trigger_status_label.setText('RADIO: elegir trigger RADIO o FILTER audio')
                for curve in self.line_items.values():curve.setData([],[])
                return
            source=stream.series[self.trigger_source]
            required_post=count-pre
            if self.single_shot_armed and self.spectral.mode in (1,2):
                nfft=int(self.spectral.size.currentText())
                required_post=max(required_post,nfft-nfft//10)
            last=total-required_post
            first=max(1,pre,last-max(3000,count*4))
            if last>first and first>=1:
                rising=self.trigger_edge=='Ascendente'
                level=self.trigger_level
                crossing=self._last_history_trigger(source,first-1,last+1,level,rising,.015)
                if crossing is not None:
                    found,before,after=crossing
                    fraction=(level-before)/(after-before)
                    trigger_shift=1-float(fraction)
            if found is not None:
                start=found-pre;end=start+count
                self.trigger_status_label.setText(f'● Disparo ({self.trigger_source} {self.trigger_edge} @ {self.trigger_level:.2f} V)')
                self.last_trigger_time=time.perf_counter()
            elif self.trigger_mode=='Normal' or self.single_shot_armed:
                self.trigger_status_label.setText('● Esperando disparo de audio…')
                if self.frozen_frame is not None:
                    self._draw_display_frame(*self._last_display_frame)
                else:
                    for curve in self.line_items.values():curve.setData([],[])
                return
            else:
                self.trigger_status_label.setText('● Auto: buscando disparo de audio · ajustar nivel')
        x=np.arange(count,dtype=float)-(pre if found is not None else 0)+trigger_shift
        if self.x_axis_time_mode:x*=1e6/stream.rate
        values={name:stream.series[name].window(start,end) for name in channels}
        self.plot_widget.setXRange(x[0],max(x[0]+1,x[-1]),padding=.02)
        self._set_temporal_x_label('Tiempo audio (µs, T=0 trigger)' if self.x_axis_time_mode and found is not None else
                                  'Tiempo audio (µs)' if self.x_axis_time_mode else 'Muestras audio')
        self.trigger_t_marker.setValue(0)
        self.trigger_t_marker.setVisible(found is not None)
        self._last_display_frame=(x,values,tuple(channels))
        self._draw_display_frame(*self._last_display_frame)
        self.lbl_top_fs.setText(f'RADIO {stream.rate/1000:g} kS/s')
        measurements=dict(values)
        meas=self.active_meas_channel
        if meas in audio_names:
            measurements[meas]=stream.series[meas].window(start,end)
        measurements['Tiempo (us)']=stream.series['Tiempo (us)'].window(start,end)
        self._update_live_measurements(measurements,list(measurements),sample_rate=stream.rate)
        if found is not None:
            self.frozen_frame=(x,values)
            if self.single_shot_armed:
                if self.spectral.mode in (1,2) and not self.spectral.capture_single(found):return
                self.single_shot_armed=False
                self._set_single_state('captured')
                self.is_running=False
                self.run_stop_btn.setChecked(False)
                self.run_stop_btn.setText('⏹ STOP')
                self._set_connection_status('Pantalla congelada (SINGLE audio capturado)')

    def render_frame(self):
        if not self.is_running:
            return

        active_columns = [col for col, checked in self.selected_columns.items() if checked]
        audio_names={'RADIO'}
        if self.filter_source.currentText()=='RADIO':audio_names.add('FILTER')
        if self.spectral.mode==0 and set(active_columns)&audio_names and set(active_columns)-audio_names:
            self._render_mixed_temporal(active_columns,audio_names);return
        if self.spectral.mode==0 and (set(active_columns)&audio_names or
                                      self.trigger_enabled and self._is_audio_channel(self.trigger_source)):
            self._render_radio_audio(active_columns,audio_names)
            return
        if self.single_shot_armed and self.spectral.mode in (1,2) and self._is_audio_channel(self.trigger_source):
            selected=self.spectral.transfer_pair() if self.spectral.mode==1 and self.spectral.fft_mode.currentText()=='Transfer' else tuple(c.currentText() for c in self.spectral.channels)
            self._render_radio_audio([c for c in selected if c!='Ninguno'],audio_names)
            return
        total_samples = len(self.sample_numbers)
        if total_samples < 2:
            return
        if not active_columns and self.spectral.mode==0:
            for curve in self.line_items.values():curve.setVisible(False)
            return

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
                meas_col = self.active_meas_channel if self.active_meas_channel in active_columns or not active_columns else active_columns[0]
                slices = {name:self._window_values(self.series[name], start, end)
                          for name in (meas_col, 'Tiempo (us)') if name in self.series and len(self.series[name])>=end}
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
                    self._set_temporal_x_label("Tiempo relativo en ventana (µs)")
                else:
                    # Sin timestamps: fallback a muestras silenciosamente
                    x_plot = np.arange(count, dtype=float) - fraction
                    self.plot_widget.setXRange(0, w, padding=0.0)
                    self._set_temporal_x_label("Muestras en ventana (sin timestamps)")
            else:
                x_plot = np.arange(count, dtype=float) - fraction
                self.plot_widget.setXRange(0, w, padding=0.0)
                self._set_temporal_x_label("Muestras en ventana")

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
                    level = self.trigger_level
                    is_rising = (self.trigger_edge == "Ascendente")
                    is_adc = "ADC" in source
                    hysteresis = 20.0 if is_adc else 0.015
                    crossing = self._last_history_trigger(src_deque, start_search-1,
                        end_search+1, level, is_rising, hysteresis)
                    if crossing is not None:
                        found_t_idx = crossing[0]

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
                self._set_temporal_trigger_status(
                    f"● Disparo ({source} {self.trigger_edge} @ {lvl_str}{unit})"
                )
                if self.x_axis_time_mode and self.current_dt_us > 0:
                    self._set_temporal_x_label("Tiempo relativo al Trigger (µs, T=0)")
                else:
                    self._set_temporal_x_label("Muestras relativas al Trigger (T=0)")

                if self.single_shot_armed:
                    if self.spectral.mode in (1, 2) and not self.spectral.capture_single(found_t_idx):
                        self.spectral.info.setText('SINGLE · esperando un bloque espectral válido.')
                        return
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
                            padding: 2px 8px;
                            color:#aeb8c8;
                            font-weight:normal;
                            font-size: 11px;
                        }
                    """)

            elif self.frozen_frame is not None and (self.trigger_mode == "Normal" or (now - self.last_trigger_time) < 0.3):
                _, y_slices = self.frozen_frame
                if self.trigger_mode == "Normal":
                    self._set_temporal_trigger_status("● Esperando disparo (Normal)…")
            else:
                # Timeout en Auto mode (fallback continuo)
                end_pos = max(w, total_samples + self.h_pos)
                end_pos = min(end_pos, total_samples)
                start_pos = max(0, end_pos - w)
                y_slices = {
                    col: self._window_values(self.series[col], start_pos, end_pos)
                    for col in active_columns if col in self.series and len(self.series[col])>=end_pos
                }
                self._set_temporal_trigger_status("● Auto: buscando disparo · ajustar nivel")
                if self.x_axis_time_mode:
                    self._set_temporal_x_label("Tiempo en ventana (µs, Buscando Trigger)")
                else:
                    self._set_temporal_x_label("Muestras en ventana (Buscando Trigger)")

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
                f"SCOPE V18 [{mode_str}] | Muestras: {number(self.sample_counter, formats.n_)} | "
                f"Ventana: {number(self.h_scale, formats.n_)} | Fs: {fs_text} | FPS: {number(self.current_fps, formats.n_1f)}"
            )

    def _update_live_measurements(self, y_slices, active_columns, sample_rate=None):
        if self.spectral.mode == 1:
            self._last_measurement_update = time.perf_counter()
            self.spectral.refresh_measurement_panel()
            return
        if sample_rate is None and self._is_audio_channel(self.active_meas_channel):
            stream=self.radio_stream
            if stream is None or stream.counter<10:
                for label in (self.val_vmax,self.val_vmin,self.val_vpp,self.val_vrms,self.val_vavg,self.val_freq):label.setText('--')
                return
            end=len(stream.sample_numbers)
            start=max(0,end-self.h_scale)
            y_slices={name:stream.series[name].window(start,end)
                      for name in (self.active_meas_channel,'Tiempo (us)')}
            active_columns=[self.active_meas_channel]
            sample_rate=stream.rate
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
            values = np.asarray(self._radio_display_values(meas_col,meas_vals), dtype=float)
            v_max = float(np.max(values))
            v_min = float(np.min(values))
            v_pp = v_max - v_min
            v_avg = float(np.mean(values))
            v_rms = float(np.sqrt(np.mean(values * values)))

            is_adc = "ADC" in meas_col
            unit = "" if is_adc else "V"
            dec = 0 if is_adc else 2

            self.val_vmax.setText(number(v_max, f'.{dec}f') + unit)
            self.val_vmin.setText(number(v_min, f'.{dec}f') + unit)
            self.val_vpp.setText(number(v_pp, f'.{dec}f') + unit)
            self.val_vrms.setText(number(v_rms, f'.{dec}f') + unit)
            self.val_vavg.setText(number(v_avg, f'.{dec}f') + unit)

            # Estimación de frecuencia física basada en timestamps o cruces
            freq_text = "--"
            if len(meas_vals) >= 50 and v_pp > (0.1 if unit == "V" else 50):
                cross_indices = np.flatnonzero((values[:-1] < v_avg) & (values[1:] >= v_avg)) + 1

                if len(cross_indices) >= 2:
                    left=cross_indices-1
                    crossing_positions=left+(v_avg-values[left])/(values[cross_indices]-values[left])
                    delta_samples = (crossing_positions[-1] - crossing_positions[0]) / (len(cross_indices) - 1)
                    t_slice = y_slices.get("Tiempo (us)", [])
                    if len(t_slice) == len(meas_vals):
                        crossing_times=np.interp(crossing_positions,np.arange(len(values)),t_slice)
                        t_delta_us = (crossing_times[-1] - crossing_times[0]) / (len(cross_indices) - 1)
                        if t_delta_us > 0:
                            freq_hz = 1_000_000.0 / t_delta_us
                            if freq_hz < 1000:
                                freq_text = f"{number(freq_hz, formats.n_1f)} Hz"
                            else:
                                freq_text = f"{number(freq_hz/1000.0, formats.n_2f)} kHz"

                    # Fallback si no hay timestamps
                    rate = self.current_fs_hz if sample_rate is None else sample_rate
                    if freq_text == "--" and delta_samples > 0 and rate > 0:
                        freq_est = rate / delta_samples
                        freq_text = (f"{number(freq_est, formats.n_1f)} Hz" if freq_est < 1000
                                     else f"{number(freq_est/1000.0, formats.n_2f)} kHz")

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
                sample,label=self.legend.items[-1]
                sample.setToolTip('Clic para mostrar u ocultar '+col)
                label.setToolTip('Clic para mostrar u ocultar '+col)
                if hasattr(sample, 'sigClicked'):
                    sample.sigClicked.connect(lambda item,name=col:self._legend_channel_clicked(name,item))
                else:
                    # Older pyqtgraph has no signal; route the click through
                    # the same channel action as the legend label.
                    sample.mouseClickEvent=lambda event,name=col:self._legend_label_clicked(event,name)
                label.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)
                label.mouseClickEvent=lambda event,name=col:self._legend_label_clicked(event,name)
            self.line_items[col].setVisible(col in active_columns)

        self.selection_dirty = False

    def closeEvent(self, event):
        if getattr(self,'_preparing_disconnect',False) or (self._q_preparation is not None and self._q_preparation.isRunning()):
            self._set_connection_status('Esperar a que termine la carga del Q antes de cerrar')
            event.ignore()
            return
        if not getattr(self,'_close_pending',False):
            self._close_pending=True
            self.render_timer.stop()
            # Close the visible UI immediately; Qt stays alive until Q confirms
            # restoration and the acquisition/loader workers have released I/O.
            self.hide()
            self.fm_panel.close_backend()
        self._wav_cancelled = True
        if hasattr(self, "_wav_thread") and self._wav_thread.isRunning():
            self._wav_thread.quit()
            self._close_pending = True
            event.ignore()
            QtCore.QTimer.singleShot(100, self.close)
            return
        if self.stop_input() is False:
            self._close_pending = True
            event.ignore()
            return
        self._close_pending = False
        self.stop_recording()
        self.render_timer.stop()
        self.spectral.close()
        self.scope_cursors.detach()
        self._radio_scan_timer.stop()
        self._radio_test_update_timer.stop()
        if self._radio_scan_executor is not None:
            self._radio_scan_executor.shutdown(wait=False,cancel_futures=True)
        self.fm_panel.close_backend()
        self.stop_input()
        event.accept()
        app=QtWidgets.QApplication.instance()
        # The primary window was hidden while cleanup ran, so Qt may no longer
        # emit lastWindowClosed for it. Quit only after all workers released Q.
        if app is not None and app.quitOnLastWindowClosed() and not any(
                window is not self and window.isVisible() for window in app.topLevelWidgets()):
            QtCore.QTimer.singleShot(0,app.quit)


def main():
    prepare_platform_plugins()
    app = QtWidgets.QApplication([])
    app.setWindowIcon(QtGui.QIcon(str(ROOT / 'monitor/v18/assets/scope_app.svg')))
    app.setStyle("Fusion")
    app.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.GeneralFont))
    window = SerialMonitorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
