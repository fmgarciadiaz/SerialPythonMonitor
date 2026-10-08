from monitor.number_format import number, formats
"""Stepped sine sweep and synchronous two-channel transfer measurement."""
import time
import numpy as np
from PyQt5 import QtWidgets, QtGui
import pyqtgraph as pg
from monitor.v12.receiver.unoq_generator import GeneratorConfig
from monitor.v12.receiver.unoq_switch import Phase
from monitor.v12.bode_calibration import load_reference, correct_transfer
from monitor.v12.plot_fill import area_polygons


def tone_transfer(t, vin, vout, frequency):
    t = np.asarray(t, dtype=float)
    vin, vout = np.asarray(vin), np.asarray(vout)
    if len(t) < 16 or not np.all(np.isfinite([t, vin, vout])):
        raise ValueError('Bloque inválido')
    angle = 2*np.pi*frequency*(t-t[0])
    basis = np.column_stack((np.cos(angle), np.sin(angle), np.ones(len(t))))
    a = np.linalg.lstsq(basis, vin, rcond=None)[0]
    b = np.linalg.lstsq(basis, vout, rcond=None)[0]
    x, y = complex(a[0], -a[1]), complex(b[0], -b[1])
    if abs(x) < .001:
        raise ValueError('Referencia de entrada insuficiente en A2')
    if np.std(vin-basis@a) > abs(x)*.3:
        raise ValueError('Entrada sin estabilizar o demasiado ruido')
    if np.ptp(vout) == 0:
        return float('-inf'), float('nan')
    ratio = y/x
    residual = vout-basis@b
    variance = float(residual@residual)/max(1, len(t)-3)
    covariance = np.linalg.pinv(basis.T@basis)*variance
    uncertainty = np.sqrt(max(covariance[0,0], covariance[1,1], 0))
    gain = 20*np.log10(abs(ratio)) if abs(ratio) > 0 else float('-inf')
    phase = np.angle(ratio, deg=True) if abs(y) > max(3*uncertainty, 1e-14) else float('nan')
    return gain, phase


def decade_frequencies(start, end, points_per_decade):
    logs = np.arange(0, np.log10(end/start), 1/points_per_decade)
    frequencies = np.append(start*10**logs, end)
    return np.unique(np.round(frequencies*1000)/1000)


class BodeFrequencySpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setGroupSeparatorShown(True)
        self.setDecimals(3)
        self.setKeyboardTracking(False)

    def textFromValue(self, value):
        return self.locale().toString(float(value), 'f', 3).rstrip('0').rstrip(self.locale().decimalPoint())


class BodeSweep:
    def __init__(self, spectral, form):
        self.spectral, self.owner = spectral, spectral.owner
        self.active = False
        self.waiting = False
        self.config = None
        self.previous = None
        self.result = []
        self.history = []
        self.history_profiles = []
        self.result_profile = None
        self.reference = load_reference()
        self.curve_sets = [spectral.curves]
        for _ in range(4):
            self.curve_sets.append([plot.plot() for plot in spectral.plots])
        self.shadows = []
        for _ in range(5):
            pair = [plot.plot() for plot in spectral.plots]
            for curve in pair: curve.setZValue(-5)
            self.shadows.append(pair)
        self.buffer = []
        self.anchor = None
        self.deadline = 0
        self.locked = []
        self.start = BodeFrequencySpinBox(); self.start.setRange(.1,20000); self.start.setValue(20); self.start.setSuffix(' Hz')
        self.end = BodeFrequencySpinBox(); self.end.setRange(.1,20000); self.end.setValue(10000); self.end.setSuffix(' Hz')
        self.points = QtWidgets.QSpinBox(); self.points.setRange(1,100); self.points.setValue(10)
        self.points.setToolTip('Puntos espaciados uniformemente en log10(f). Cada década completa tiene la misma densidad; incluye el extremo final.')
        self.settle = QtWidgets.QSpinBox(); self.settle.setRange(0,60000); self.settle.setValue(200); self.settle.setSuffix(' ms')
        self.cycles = QtWidgets.QSpinBox(); self.cycles.setRange(1,64); self.cycles.setValue(3)
        self.settle.setToolTip('Espera fija después del cambio de frecuencia. No depende del período de la onda.')
        self.cycles.setToolTip('Ciclos estables usados para medir amplitud y fase; más ciclos permiten promediar más ruido.')
        for text, widget in [('Desde',self.start),('Hasta',self.end),('Puntos / década',self.points),('Asentamiento',self.settle),('Ciclos a medir',self.cycles)]: form.addRow(text,widget)
        self.estimate = QtWidgets.QLabel()
        self.estimate.setWordWrap(True)
        form.addRow(self.estimate)
        for spin in (self.start,self.end,self.points,self.settle,self.cycles):
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(self.update_estimate)
        self.update_estimate()
        self.coverage = QtWidgets.QLabel()
        self.coverage.setWordWrap(True)
        form.addRow(self.coverage)
        self.curve_labels = QtWidgets.QLabel()
        self.curve_labels.setWordWrap(True)
        form.addRow(self.curve_labels)
        self.calibrated = QtWidgets.QCheckBox('Corregir con calibración')
        self.calibrated.setChecked(self.reference is not None)
        self.calibrated.setEnabled(self.reference is not None)
        self.calibrated.setToolTip('Referencia A0 → A2 y A3. Sólo corrige el mismo perfil ADC y dentro del rango medido.')
        self.calibrated.toggled.connect(self.draw)
        form.addRow(self.calibrated)
        self.log_frequency = QtWidgets.QCheckBox('Eje X logarítmico')
        self.log_frequency.setChecked(True)
        self.log_frequency.toggled.connect(self.change_axis)
        form.addRow(self.log_frequency)
        self.button = QtWidgets.QPushButton('Repetir')
        self.button.clicked.connect(lambda:self.cancel('Cancelado') if self.active else self.begin())
        self.add_button = QtWidgets.QPushButton('Agregar')
        self.add_button.clicked.connect(lambda:self.begin(add=True))
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.add_button); buttons.addWidget(self.button)
        form.addRow(buttons)
        self.status = QtWidgets.QLabel('A2 = entrada · A3 = salida\nGanancia y fase: V_OUT / V_IN')
        self.status.setWordWrap(True); form.addRow(self.status)

    def timing(self, frequency, fs):
        return self.settle.value()/1000, max(self.cycles.value()/frequency, 32/fs)

    def update_estimate(self, *args):
        if self.end.value() <= self.start.value():
            self.estimate.setText('Elegir inicio menor que final.'); return
        config = getattr(self.owner, 'applied_configuration', None)
        fs = config.rate if config is not None else 31250
        frequencies = decade_frequencies(self.start.value(),self.end.value(),self.points.value())
        seconds = sum(sum(self.timing(frequency,fs)) for frequency in frequencies)
        duration = f'{number(seconds, formats.n_1f)} s' if seconds < 60 else f'{number(seconds/60, formats.n_1f)} min'
        self.estimate.setText(f'{len(frequencies)} puntos · mínimo {duration}\n+ comunicación y entrega de muestras')

    def change_axis(self):
        if self.spectral.mode == 3:
            self.spectral.configure_plots()
            self.draw()

    def begin(self, add=False):
        if self.active: return
        if add and self.result and len(self.history) >= 4:
            self.status.setText('Máximo de cinco curvas. Repetir inicia una nueva comparación.'); return
        owner = self.owner
        if owner.serial_worker is None or not owner.is_running:
            self.status.setText('Conectar el Q y activar RUN para medir Bode.'); return
        if owner._auto_apply_timer.isActive() or not owner.config_rate_combo.isEnabled():
            self.status.setText('Esperar la confirmación de adquisición antes de iniciar Bode.'); return
        for spin in (self.start,self.end,self.points,self.settle,self.cycles): spin.interpretText()
        fs = owner.applied_configuration.rate
        if self.start.value() >= self.end.value() or self.end.value() >= .45*fs:
            self.status.setText(f'Rango inválido: inicio < final < {number(fs*.45, formats.n__0f)} Hz (0,45 Fs).'); return
        if not owner._generator_state_known or owner._generator_requested is not None:
            self.status.setText('Esperar confirmación del generador antes de iniciar Bode.'); return
        try:
            self.stimulus = owner._generator_config()
            self.previous = owner._generator_active
            if self.stimulus.high-self.stimulus.low < 10:
                raise ValueError('Elegir una amplitud mayor en el generador.')
        except ValueError as exc:
            self.status.setText(str(exc)); return
        self.frequencies = decade_frequencies(self.start.value(), self.end.value(), self.points.value())
        if add:
            if self.result:
                self.history.append(list(self.result))
                self.history_profiles.append(self.result_profile)
        else:
            self.history.clear()
            self.history_profiles.clear()
        self.result_profile = owner.applied_configuration
        self.index = 0; self.result.clear(); self.invalid_points = []; self.active = True
        self.add_button.setEnabled(False)
        self.coverage.clear()
        owner._generator_timer.stop()
        owner._generator_dirty = False
        owner.single_shot_armed = False
        controls = owner._generator_controls + [owner.generator_frequency_dial, owner.config_bits_combo,
            owner.config_rate_combo, owner.destination_combo, self.start,self.end,self.points,self.settle,self.cycles,
            owner.single_btn]
        self.locked = [(control, control.isEnabled()) for control in controls]
        for control, _ in self.locked: control.setEnabled(False)
        self.button.setText('Cancelar barrido')
        self.spectral.reset(); self.spectral.configure_plots()
        self.draw()
        self.next_tone()

    def next_tone(self):
        frequency = round(self.frequencies[self.index]*1000)
        self.config = GeneratorConfig(1,1,0,frequency,frequency,self.stimulus.low,self.stimulus.high,1000)
        self.frequency = frequency/1000
        self.waiting = True; self.anchor = None; self.buffer.clear()
        self.last_timestamp = None
        self.seen = 0
        self.stride = max(1, int(self.owner.applied_configuration.rate / max(500, self.frequency*32)))
        self.deadline = time.monotonic()+10
        self.owner._generator_requested = self.config
        try:
            self.owner.serial_worker.request_generator(self.config)
        except Exception as exc:
            self.cancel(f'No se pudo iniciar el tono: {exc}'); return
        self.status.setText(f'{self.index+1}/{len(self.frequencies)} · {number(self.frequency, formats.ng)} Hz · esperando Q…')

    def confirmed(self, reply):
        if not self.active: return
        if reply.phase == Phase.REJECTED and reply.requested != self.config: return
        if reply.phase == Phase.APPLIED and reply.active != self.config: return
        if reply.phase == Phase.REJECTED:
            self.cancel(f'Q rechazó el tono: {reply.reason.name}')
        elif reply.phase == Phase.APPLIED and reply.active == self.config:
            self.waiting = False
            settle, duration = self.timing(self.frequency,self.owner.applied_configuration.rate)
            self.deadline = time.monotonic()+settle+duration+max(10, (settle+duration)*.2)
            self.status.setText(f'{self.index+1}/{len(self.frequencies)} · {number(self.frequency, formats.ng)} Hz · midiendo…')

    def batch(self, batch):
        if not self.active or self.waiting: return
        settle, duration = self.timing(self.frequency,self.owner.applied_configuration.rate)
        for sample in batch:
            if not all(key in sample for key in ('Tiempo (us)','V_IN','V_OUT')):
                self.cancel('Bode requiere timestamps y los dos canales.'); return
            t = sample['Tiempo (us)']*1e-6
            nominal = 1/self.owner.applied_configuration.rate
            if self.last_timestamp is not None:
                delta = t-self.last_timestamp
                if delta <= 0 or abs(delta-nominal)>max(1.1e-6, nominal*.25):
                    self.cancel('Discontinuidad de adquisición'); return
            self.last_timestamp = t
            if self.anchor is None: self.anchor = t
            if t-self.anchor < settle: continue
            self.seen += 1
            if self.seen % self.stride: continue
            self.buffer.append((t,sample['V_IN'],sample['V_OUT']))
            if len(self.buffer) > 2000000:
                self.cancel('Bloque demasiado grande: aumentar frecuencia inicial.'); return
            if t-self.anchor >= settle+duration:
                data = np.asarray(self.buffer)
                dt = np.diff(data[:,0]); nominal = self.stride/self.owner.applied_configuration.rate
                try:
                    if np.any(dt<=0) or np.any(np.abs(dt-nominal)>max(1.1e-6, nominal*.25)):
                        raise ValueError('Discontinuidad de adquisición')
                    gain, phase = tone_transfer(data[:,0],data[:,1],data[:,2],self.frequency)
                    self.result.append((self.frequency,gain,phase))
                except ValueError as exc:
                    if 'Discontinuidad' in str(exc):
                        self.cancel(str(exc)); return
                    self.result.append((self.frequency,float('nan'),float('nan')))
                    self.invalid_points.append((self.frequency,str(exc)))
                self.draw()
                self.index += 1
                if self.index == len(self.frequencies):
                    undefined = sum(np.isnan(p) and not np.isnan(g) for _,g,p in self.result)
                    self.cancel(f'Barrido terminado · {number(self.frequencies[0], formats.ng)}–{number(self.frequencies[-1], formats.ng)} Hz · {len(self.invalid_points)} referencias inválidas · {undefined} fases indeterminadas'); return
                self.next_tone()
                return  # Discard the rest of the batch from the previous tone.

    def draw(self):
        for curves in self.curve_sets + self.shadows:
            for curve in curves: curve.setData([], [])
        for index, result in enumerate(self.history + [self.result]):
            self.draw_curve(result, index)
        self.curve_labels.setText(' &nbsp; '.join(
            f'<span style="color:{self.owner.channel_palette[index]}">● {index+1}</span>'
            for index, result in enumerate(self.history + [self.result]) if result))
        if not self.result: return
        data = np.asarray(self.result)
        target = len(self.frequencies) if hasattr(self, 'frequencies') else len(data)
        gains = int(np.count_nonzero(~np.isnan(data[:,1])))
        phases = int(np.count_nonzero(np.isfinite(data[:,2])))
        self.coverage.setText(f'Ganancia: {gains}/{target} · Fase: {phases}/{target}')
        if self.calibrated.isChecked() and self.result_profile is not None:
            _, corrected = correct_transfer(data, self.reference, self.result_profile)
            self.coverage.setText(self.coverage.text()+f'\nCalibración: {int(corrected.sum())}/{len(data)} puntos')
        self.coverage.setToolTip('Cada marcador es una frecuencia medida. La fase se omite cuando no se puede resolver, sin descartar la ganancia.')

    def draw_curve(self, result, index):
        if not result: return
        data = np.asarray(result)
        profiles = self.history_profiles + [self.result_profile]
        profile = profiles[index] if index < len(profiles) else None
        if self.calibrated.isChecked() and profile is not None:
            data, _ = correct_transfer(data, self.reference, profile)
        color = self.owner.channel_palette[index]
        for i in range(2):
            values = data[:,1].copy() if i == 0 else data[:,2].copy()
            if i == 0:
                zero = np.isneginf(values)
                finite = values[np.isfinite(values)]
                floor = min(-160, float(finite.min())-20) if len(finite) else -160
                values[zero] = floor
                suffix = f' · cero: −∞ dB (piso visual {number(floor, formats.ng)} dB)' if np.any(zero) else ''
                self.spectral.plots[0].setTitle('Ganancia V_OUT / V_IN'+suffix)
            if i == 1:
                valid = np.isfinite(values)
                starts = np.flatnonzero(valid & ~np.r_[False, valid[:-1]])
                ends = np.flatnonzero(valid & ~np.r_[valid[1:], False])+1
                for start, end in zip(starts, ends):
                    values[start:end] = np.rad2deg(np.unwrap(np.deg2rad(values[start:end])))
            self.curve_sets[index][i].setData(data[:,0],values, pen=color, symbol='o', symbolSize=4, symbolPen=None, symbolBrush=color)
            shadow = QtGui.QColor(color)
            shadow.setAlpha(38)
            finite = values[np.isfinite(values)]
            bottom = float(finite.min()-max(3, np.ptp(finite)*.1)) if len(finite) else -160
            xfill, yfill = area_polygons(data[:,0], values, bottom)
            self.shadows[index][i].setData(xfill, yfill,
                pen=None, fillLevel='enclosed', fillBrush=pg.mkBrush(shadow), connect='finite')

    def tick(self):
        if self.active and (not self.owner.is_running or self.owner.serial_worker is None):
            self.cancel('Barrido detenido')
        elif self.active and time.monotonic()>self.deadline:
            self.cancel('Sin confirmación o sin suficientes muestras del Q')

    def cancel(self, text='Cancelado', restore=True):
        if not self.active: return
        self.active = False; self.waiting = False; self.buffer.clear()
        for control, enabled in self.locked: control.setEnabled(enabled)
        self.locked.clear(); self.button.setText('Repetir'); self.status.setText(text)
        self.add_button.setEnabled(len(self.history) < 4 or not self.result)
        if restore and self.owner.serial_worker is not None and self.previous is not None:
            self.owner._generator_requested = self.previous
            try: self.owner.serial_worker.request_generator(self.previous)
            except Exception as exc: self.status.setText(f'{text}. No se pudo restaurar generador: {exc}')
