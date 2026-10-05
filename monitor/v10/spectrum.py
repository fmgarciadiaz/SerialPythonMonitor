"""Live one-sided spectra and bounded scrolling spectrograms."""
from collections import deque
import numpy as np
import time
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
from monitor.v10.bode import BodeSweep
from monitor.v10.plot_fill import area_polygons


WINDOWS = {'Hann': np.hanning, 'Hamming': np.hamming,
           'Blackman': np.blackman, 'Rectangular': np.ones}


def spectrum(values, fs, window='Hann', remove_dc=True):
    """Return Hz and peak volts, corrected for window coherent gain."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or fs <= 0 or not np.all(np.isfinite(values)):
        raise ValueError('Muestras o frecuencia de adquisición inválidas')
    weights = WINDOWS[window](len(values))
    centered = values - values.mean() if remove_dc else values
    amplitude = np.abs(np.fft.rfft(centered * weights)) / weights.sum()
    amplitude[1:] *= 2
    if len(values) % 2 == 0:
        amplitude[-1] /= 2
    return np.fft.rfftfreq(len(values), 1 / fs), amplitude


class FrequencyAxis(pg.AxisItem):
    """Keep logarithmic labels readable while retaining minor grid lines."""
    def __init__(self, orientation):
        super().__init__(orientation)
        self.setStyle(maxTextLevel=0)

    def logTickValues(self, minVal, maxVal, size, stdTicks):
        major, minor = [], []
        factors = (1, 2, 5) if size >= 300 else (1,)
        for decade in range(int(np.floor(minVal)), int(np.ceil(maxVal))+1):
            for multiplier in range(1, 10):
                value = decade + np.log10(multiplier)
                if minVal <= value <= maxVal:
                    (major if multiplier in factors else minor).append(value)
        return [(1, major), (None, minor)]

    def logTickStrings(self, values, scale, spacing):
        return [f'{10**value*scale:.4g}' for value in values]


class SpectralDisplay:
    def __init__(self, owner, layout, stack):
        self.owner, self.stack = owner, stack
        self.mode = 0
        self.last_end = None
        self.context = None
        self.frames = deque(maxlen=512)
        self.widget = pg.GraphicsLayoutWidget()
        stack.addWidget(self.widget)
        self.plots, self.curves, self.images, self.bars = [], [], [], []
        self.attached = {0, 1}
        self.fft_fills = []
        for row in range(2):
            plot = self.widget.addPlot(row=row, col=0, axisItems={
                'bottom':FrequencyAxis('bottom'), 'left':FrequencyAxis('left')})
            plot.showGrid(x=True, y=True, alpha=.2)
            curve = plot.plot(pen=pg.mkPen('#00e5ff', width=1))
            fill = plot.plot(pen=None)
            fill.setZValue(-5)
            self.fft_fills.append(fill)
            image = pg.ImageItem(axisOrder='row-major')
            image.setLookupTable(pg.colormap.get('viridis').getLookupTable())
            plot.addItem(image)
            bar = pg.ColorBarItem(values=(-100, 10), colorMap=pg.colormap.get('viridis'),
                                  interactive=False)
            bar.setImageItem(image, insert_in=plot)
            self.plots.append(plot); self.curves.append(curve)
            self.images.append(image); self.bars.append(bar)
        group = QtWidgets.QGroupBox('MODOS · ANÁLISIS')
        box = QtWidgets.QVBoxLayout(group)
        buttons = QtWidgets.QHBoxLayout()
        self.buttons = QtWidgets.QButtonGroup(group)
        for i, text in enumerate(('V/t', 'FFT', 'Heatmap', 'Bode')):
            button = QtWidgets.QPushButton(text)
            button.setCheckable(True); button.setFixedHeight(34)
            button.setStyleSheet("QPushButton {padding:4px 2px; font-size:11px; background:#21252f;} QPushButton:checked {background:#006879; border:1px solid #00e5ff; color:white;}")
            self.buttons.addButton(button, i); buttons.addWidget(button)
            button.clicked.connect(lambda checked, mode=i: self.set_mode(mode))
            if i == 0: button.setChecked(True)
        # Use the same neutral tick asset as the channel controls.
        from pathlib import Path
        check_icon = (Path(__file__).parent / 'assets/check_neutral.svg').as_posix()
        group.setStyleSheet(f"""QCheckBox {{background:transparent; border:none; padding:2px;}}
            QCheckBox::indicator {{width:14px; height:14px; border:1px solid #737d8d;
                border-radius:3px; background:#171920;}}
            QCheckBox::indicator:checked {{image:url("{check_icon}");}}
            QCheckBox::indicator:unchecked {{image:none;}}""")
        box.addLayout(buttons)
        self.settings = QtWidgets.QWidget()
        grid = QtWidgets.QFormLayout(self.settings)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(2)
        self.size = QtWidgets.QComboBox(); self.size.addItems(['256','512','1024','2048','4096','8192']); self.size.setCurrentText('2048')
        self.window = QtWidgets.QComboBox(); self.window.addItems(list(WINDOWS))
        self.overlap = QtWidgets.QComboBox(); self.overlap.addItems(['0 %','50 %','75 %']); self.overlap.setCurrentIndex(1)
        self.scale = QtWidgets.QComboBox(); self.scale.addItems(['dBV', 'V pico'])
        self.channels = []
        for index in range(2):
            combo = QtWidgets.QComboBox(); combo.addItems(['Ninguno', 'V_IN', 'V_OUT']); combo.setCurrentIndex(index + 1)
            self.channels.append(combo)
        self.seconds = QtWidgets.QSpinBox(); self.seconds.setRange(2, 60); self.seconds.setValue(10); self.seconds.setSuffix(' s')
        self.remove_dc = QtWidgets.QCheckBox('Quitar componente DC'); self.remove_dc.setChecked(True)
        for label, control in [('Muestras',self.size), ('Ventana',self.window), ('Solapamiento',self.overlap),
                               ('Escala',self.scale), ('Canal arriba',self.channels[0]), ('Canal abajo',self.channels[1]),
                               ('Historia',self.seconds)]:
            grid.addRow(label, control)
            signal = control.valueChanged if isinstance(control, QtWidgets.QSpinBox) else control.currentIndexChanged
            signal.connect(self.reset)
        grid.addRow(self.remove_dc); self.remove_dc.toggled.connect(self.reset)
        self.log_frequency = QtWidgets.QCheckBox('Frecuencia logarítmica')
        self.log_frequency.toggled.connect(self.reset)
        grid.insertRow(0, self.log_frequency)
        self.lock_axes = QtWidgets.QCheckBox('Misma escala en ambos canales')
        self.lock_axes.toggled.connect(self.reset)
        grid.insertRow(0, self.lock_axes)
        self.info = QtWidgets.QLabel(''); self.info.setWordWrap(True)
        grid.addRow(self.info)
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        options = QtWidgets.QWidget()
        options_layout = QtWidgets.QVBoxLayout(options)
        options_layout.setContentsMargins(0,0,0,0)
        self.temporal_settings = owner.temporal_settings
        options_layout.addWidget(self.temporal_settings)
        options_layout.addWidget(self.settings)
        self.bode_settings = QtWidgets.QWidget()
        bode_form = QtWidgets.QFormLayout(self.bode_settings)
        bode_form.setContentsMargins(0,0,0,0)
        bode_form.setVerticalSpacing(2)
        self.bode = BodeSweep(self, bode_form)
        options_layout.addWidget(self.bode_settings)
        options_layout.addStretch()
        scroll.setWidget(options)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        box.addWidget(scroll, 1)
        self.group = group
        layout.addWidget(group, 1)
        self.set_mode(0)

    def reset(self, *args):
        self.last_end = None; self.context = None; self.frames.clear()
        self.y_ranges = {}
        self.shrink_since = {}
        for curve, image in zip(self.curves, self.images):
            curve.setData([], []); image.clear()
        for fill in self.fft_fills: fill.setData([], [])

    def set_mode(self, mode):
        if self.bode.active: self.bode.cancel('Cambio de modo')
        self.mode = mode
        self.buttons.button(mode).setChecked(True)
        self.stack.setCurrentIndex(0 if mode == 0 else 1)
        self.settings.setEnabled(mode in (1,2))
        self.settings.setVisible(mode in (1,2))
        self.temporal_settings.setVisible(mode == 0)
        self.bode_settings.setVisible(mode == 3)
        self.reset()
        self.configure_plots()
        if mode == 3: self.bode.begin()

    def configure_plots(self):
        heat = self.mode == 2
        for fill in self.fft_fills: fill.setVisible(self.mode == 1)
        for curves in self.bode.curve_sets[1:] + self.bode.shadows:
            for curve in curves: curve.setVisible(self.mode == 3)
        for i, plot in enumerate(self.plots):
            channel = self.channels[i].currentText()
            if self.mode == 3: channel = ('Ganancia V_OUT / V_IN', 'Fase V_OUT / V_IN')[i]
            visible = channel != 'Ninguno'
            if not visible and i in self.attached:
                self.widget.ci.removeItem(plot)
                self.attached.remove(i)
            elif visible and i not in self.attached:
                self.widget.ci.addItem(plot, row=i, col=0)
                self.attached.add(i)
            plot.setVisible(visible)
            self.widget.ci.layout.setRowStretchFactor(i, 1 if visible else 0)
            self.curves[i].setVisible(not heat); self.images[i].setVisible(heat)
            self.curves[i].setFillLevel(None)
            self.curves[i].setSymbol('o' if self.mode == 3 else None)
            self.bars[i].setVisible(heat)
            plot.setTitle(channel + (' · evolución espectral' if heat else ' · espectro actual'))
            plot.setLabel('bottom', 'Tiempo relativo al último bloque' if heat else 'Frecuencia', units='s' if heat else 'Hz')
            plot.setLabel('left', 'Frecuencia' if heat else 'Amplitud', units='Hz' if heat else self.scale.currentText())
            x_log = (self.mode == 3 and self.bode.log_frequency.isChecked()) or (self.mode == 1 and self.log_frequency.isChecked())
            y_log = heat and self.log_frequency.isChecked()
            # AxisItem treats its range as exponents as soon as log mode is enabled.
            if x_log and not plot.getAxis('bottom').logMode:
                plot.setXRange(0, 1, padding=0)
            if y_log and not plot.getAxis('left').logMode:
                plot.setYRange(0, 1, padding=0)
            plot.setLogMode(x=x_log, y=y_log)
            if self.mode == 3:
                plot.setTitle(channel)
                plot.setLabel('bottom', 'Frecuencia', units='Hz')
                plot.setLabel('left', 'Ganancia' if i == 0 else 'Fase', units='dB' if i == 0 else '°')
            plot.setXLink(None); plot.setYLink(None)
            if self.mode == 1:
                plot.disableAutoRange()
            elif self.mode == 3:
                plot.disableAutoRange(axis=pg.ViewBox.XAxis)
                plot.enableAutoRange(axis=pg.ViewBox.YAxis)
                if self.bode.end.value() > self.bode.start.value():
                    log = self.bode.log_frequency.isChecked()
                    plot.setXRange(np.log10(self.bode.start.value()) if log else self.bode.start.value(),
                                   np.log10(self.bode.end.value()) if log else self.bode.end.value(), padding=0)
            else:
                plot.enableAutoRange()
        if self.mode == 1 and self.lock_axes.isChecked() and self.attached == {0, 1}:
            self.plots[1].setXLink(self.plots[0]); self.plots[1].setYLink(self.plots[0])

    def stable_range(self, key, arrays):
        values = np.concatenate([np.asarray(a)[np.isfinite(a)] for a in arrays if a is not None])
        if not len(values): return None
        low, high = float(values.min()), float(values.max())
        minimum = 10 if self.scale.currentIndex() == 0 else .05
        span = max(high-low, minimum)
        margin = max(span*.15, 3 if self.scale.currentIndex() == 0 else .005)
        desired = (low-margin, high+margin)
        old = self.y_ranges.get(key)
        now = time.monotonic()
        if old is None or low < old[0]+margin*.25 or high > old[1]-margin*.25:
            self.y_ranges[key] = desired if old is None else (min(old[0],desired[0]), max(old[1],desired[1]))
            self.shrink_since.pop(key, None)
        elif desired[1]-desired[0] < (old[1]-old[0])*.6:
            since = self.shrink_since.setdefault(key, now)
            if now-since >= 3:
                self.y_ranges[key] = desired; self.shrink_since.pop(key, None)
        else:
            self.shrink_since.pop(key, None)
        return self.y_ranges[key]

    def render(self):
        if self.mode == 3:
            self.bode.tick()
            return
        if self.mode == 0 or not self.owner.is_running:
            return
        n = int(self.size.currentText())
        owner = self.owner
        if len(owner.sample_numbers) < n:
            self.info.setText(f'Esperando {n:,} muestras…'); return
        timestamps = owner.series.get('Tiempo (us)')
        if timestamps is not None and len(timestamps) >= n:
            dt = np.diff(timestamps[-n:])
            nominal = np.median(dt)
            if nominal <= 0 or np.any(dt <= 0) or np.any(np.abs(dt - nominal) > max(1.1, nominal * .25)):
                self.reset(); self.info.setText('Discontinuidad temporal: esperando un bloque completo.'); return
            fs = 1e6 / np.mean(dt)
        else:
            fs = owner.current_fs_hz
        if fs <= 0:
            self.info.setText('Esperando frecuencia de adquisición…'); return
        channels = tuple(c.currentText() for c in self.channels)
        context = (n, self.window.currentText(), channels, round(fs, 1), self.mode,
                   self.remove_dc.isChecked(), self.scale.currentText(), self.seconds.value(), self.overlap.currentIndex(), self.log_frequency.isChecked(), self.lock_axes.isChecked())
        if context != self.context:
            self.reset(); self.context = context; self.configure_plots()
        overlap = (0, .5, .75)[self.overlap.currentIndex()]
        hop = max(int(n * (1 - overlap)), int(np.ceil(fs * self.seconds.value() / 512)), int(np.ceil(fs / 30)))
        end = owner.sample_counter
        if self.last_end is not None and end - self.last_end < (hop if self.mode == 2 else 1): return
        oldest = end - len(owner.sample_numbers)
        first = end if self.last_end is None or self.mode == 1 else self.last_end + hop
        # Bound per-frame processing; leave NaN gaps rather than stretching time when behind.
        if first < max(oldest + n, end - 15 * hop):
            first += int(np.ceil((max(oldest + n, end - 15 * hop) - first) / hop)) * hop
        for block_end in range(first, end + 1, hop):
            spectra = []
            start = block_end - oldest - n
            valid_time = True
            if timestamps is not None and len(timestamps) >= start + n:
                differences = np.diff(timestamps.window(start, start + n))
                valid_time = bool(np.all(differences > 0) and
                    np.all(np.abs(differences - 1e6/fs) <= max(1.1, 1e6/fs * .25)))
            for channel in channels:
                history = owner.series.get(channel)
                if channel == 'Ninguno' or history is None or len(history) != len(owner.sample_numbers) or not valid_time:
                    spectra.append(None); continue
                start = block_end - oldest - n
                values = history.window(start, start + n)
                if not np.all(np.isfinite(values)):
                    spectra.append(None); continue
                frequencies, amplitudes = spectrum(values, fs, self.window.currentText(), self.remove_dc.isChecked())
                spectra.append(20 * np.log10(np.maximum(amplitudes, 1e-12)) if self.scale.currentIndex() == 0 else amplitudes)
            self.frames.append((block_end, spectra)); self.last_end = block_end
        if not self.frames: return
        self.info.setText(f'Fs {fs:,.0f} Hz · Δf {fs/n:.2f} Hz\nVentana {n/fs*1000:.1f} ms · paso {hop/fs*1000:.1f} ms\nColor/amplitud: {self.scale.currentText()}')
        latest_values = self.frames[-1][1]
        shared_range = None
        if self.mode == 1 and self.lock_axes.isChecked():
            selected = [a[1:] if self.log_frequency.isChecked() else a for a in latest_values if a is not None]
            if selected: shared_range = self.stable_range('shared', selected)
        for i, channel in enumerate(channels):
            values = latest_values[i]
            if values is None:
                self.curves[i].setData([], [])
                self.fft_fills[i].setData([], [])
                if self.mode == 1: continue
            color = owner.channel_colors.get(channel, '#00e5ff')
            self.curves[i].setPen(pg.mkPen(color, width=1))
            if self.mode == 1:
                frequencies = np.fft.rfftfreq(n, 1/fs)
                log = self.log_frequency.isChecked()
                self.curves[i].setData(frequencies[1:] if log else frequencies, values[1:] if log else values)
                yrange = shared_range or self.stable_range(i, [values[1:] if log else values])
                if yrange is not None:
                    fill = pg.mkColor(color); fill.setAlpha(38)
                    baseline = yrange[0] if self.scale.currentIndex() == 0 else 0
                    xfill, yfill = area_polygons(frequencies[1:] if log else frequencies,
                                               values[1:] if log else values, baseline)
                    self.fft_fills[i].setData(xfill, yfill, pen=None, fillLevel='enclosed',
                                            fillBrush=pg.mkBrush(fill), connect='finite')
                if yrange is not None and not (i == 1 and self.lock_axes.isChecked() and self.attached == {0, 1}):
                    self.plots[i].setYRange(*yrange, padding=0)
                self.plots[i].setXRange(np.log10(fs/n) if log else 0,
                                       np.log10(fs/2) if log else fs/2, padding=0)
            else:
                count = min(512, int(np.ceil(self.seconds.value() * fs / hop)))
                raster = np.full((n//2+1, count), np.nan, dtype=np.float32)
                latest = self.last_end
                for frame_end, spectra in self.frames:
                    col = count - 1 - round((latest - frame_end)/hop)
                    if 0 <= col < count and spectra[i] is not None: raster[:, col] = spectra[i]
                levels = (-100, 10) if self.scale.currentIndex() == 0 else (0, 3.3)
                log = self.log_frequency.isChecked()
                if log:
                    low, high = np.log10(fs/n), np.log10(fs/2)
                    rows = min(512, n//2)
                    edges = np.linspace(low, high, rows+1)
                    centers = 10**((edges[:-1]+edges[1:])/2)
                    source = centers/(fs/n)
                    below = np.floor(source).astype(int)
                    above = np.minimum(below+1, n//2)
                    weight = (source-below).astype(np.float32)[:,None]
                    raster = raster[below]*(1-weight)+raster[above]*weight
                else:
                    low, high = -fs/n/2, fs/2+fs/n/2
                self.images[i].setImage(raster, autoLevels=False, levels=levels)
                self.images[i].setRect(QtCore.QRectF(-count*hop/fs, low, count*hop/fs, high-low))
                self.bars[i].setLevels(levels)
                self.bars[i].getAxis('left').setLabel(self.scale.currentText())
                self.plots[i].setXRange(-count*hop/fs, 0, padding=0)
                self.plots[i].setYRange(np.log10(fs/n) if log else 0, np.log10(fs/2) if log else fs/2, padding=0)
