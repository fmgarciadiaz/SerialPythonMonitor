from monitor.number_format import number, formats
from monitor.locale_axis import LocaleAxis
"""Live one-sided spectra and bounded scrolling spectrograms."""
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import time
from monitor.v17.qt_environment import prepare_platform_plugins
prepare_platform_plugins()
from PyQt6 import QtCore, QtWidgets, QtGui
from monitor.v17.status_widgets import StatusLabel
import pyqtgraph as pg
if pg.Qt.QT_LIB != "PyQt6":
    raise RuntimeError("V17 requiere pyqtgraph con PyQt6; iniciar en un proceso separado de V12.")
from monitor.v17.bode import BodeSweep
from monitor.v17.bode_pulse import BodePanels
from monitor.v17 import spectral_analysis as analysis


class RadioTuneDrag(QtCore.QObject):
    """Preview tuning on press/drag; commit once on release."""
    def __init__(self,display):
        super().__init__(display.widget)
        self.display=display;self.plot=None;self.items=[]
        display.widget.viewport().installEventFilter(self)

    def clear(self):
        if self.plot is not None:
            for item in self.items:self.plot.removeItem(item)
        self.plot=None;self.items=[]

    def preview(self,point):
        d=self.display
        x=self.plot.getViewBox().mapSceneToView(point).x()
        self.frequency=10**np.clip(x,-20,20) if d.log_frequency.isChecked() else x
        rate=d.owner.applied_configuration.actual_rate
        frequency=np.clip(self.frequency,1,rate/2-1)
        position=lambda value:np.log10(max(1,value)) if d.log_frequency.isChecked() else value
        half=d.owner.radio_bandwidth.currentData()/2
        self.items[0].setValue(position(frequency))
        self.items[1].setRegion((position(max(1,frequency-half)),position(min(rate/2,frequency+half))))

    def eventFilter(self,watched,event):
        d=self.display;kind=event.type()
        if kind==QtCore.QEvent.Type.KeyPress and event.key()==QtCore.Qt.Key.Key_Escape and self.plot is not None:
            self.clear();return True
        if kind not in (QtCore.QEvent.Type.MouseButtonPress,QtCore.QEvent.Type.MouseMove,QtCore.QEvent.Type.MouseButtonRelease):return False
        enabled=(d.mode==1 and d.radio_fft_view and not getattr(getattr(d.owner,'_radio_multiscan',None),'active',False))
        if not enabled:
            self.clear();return False
        point=d.widget.mapToScene(event.position().toPoint())
        if kind==QtCore.QEvent.Type.MouseButtonPress and event.button()==QtCore.Qt.MouseButton.LeftButton:
            for i,plot in enumerate(d.plots):
                if i not in d.attached or d.channels[i].currentText()!='CH1' or not plot.getViewBox().sceneBoundingRect().contains(point):continue
                self.clear();self.plot=plot
                line=pg.InfiniteLine(angle=90,movable=False,pen=pg.mkPen('#ffbd66',width=2))
                band=pg.LinearRegionItem(movable=False,brush=pg.mkBrush(255,189,102,35),pen=pg.mkPen(None))
                line.setZValue(100);band.setZValue(90)
                self.items=[line,band]
                for item in self.items:plot.addItem(item,ignoreBounds=True)
                self.preview(point);return True
        if self.plot is not None:
            if kind==QtCore.QEvent.Type.MouseMove:
                self.preview(point);return True
            if kind==QtCore.QEvent.Type.MouseButtonRelease and event.button()==QtCore.Qt.MouseButton.LeftButton:
                self.preview(point);frequency=self.frequency;self.clear()
                d._tune_radio_fft_frequency(frequency);return True
        return False


def _fit_distortion_batch(signals, fs, options):
    return {name: analysis.distortion(data,fs[name] if isinstance(fs,dict) else fs,**options) for name,data in signals.items()}


WINDOWS = {'Hann': np.hanning, 'Hamming': np.hamming,
           'Blackman': np.blackman, 'Rectangular': np.ones}


def spectrum(values, fs, window='Hann', remove_dc=True):
    """Return Hz and peak volts, corrected for window coherent gain."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or fs <= 0 or not np.all(np.isfinite(values)):
        raise ValueError('Muestras o frecuencia de adquisición inválidas')
    weights = WINDOWS[window](len(values))
    return np.fft.rfftfreq(len(values), 1 / fs), _amplitudes(values, weights, remove_dc)


def _amplitudes(values, weights, remove_dc):
    centered = values - values.mean() if remove_dc else values
    amplitude = np.abs(np.fft.rfft(centered * weights)) / weights.sum()
    amplitude[1:] *= 2
    if len(values) % 2 == 0:
        amplitude[-1] /= 2
    return amplitude


class FrequencyAxis(LocaleAxis):
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
        return [f'{number(10**value*scale, formats.n_4g)}' for value in values]


class SpectralDisplay:
    def __init__(self, owner, layout, stack):
        self.owner, self.stack = owner, stack
        self.mode = 0
        self.radio_fft_view = False
        self.radio_overlay_items = []
        self.last_end = None
        self.last_fast_render = 0.0
        self.deferred_live_timer_calls = 0
        self.context = None
        self.frames = deque(maxlen=512)
        self._single_snapshot = None
        self._distortion_executor = None
        self._distortion_future = None
        self._distortion_generation = 0
        self._distortion_cache = {}
        self._distortion_submitted = -float('inf')
        self.widget = pg.GraphicsLayoutWidget()
        stack.addWidget(self.widget)
        self.plots, self.curves, self.images, self.bars = [], [], [], []
        self.attached = {0, 1}
        self.fft_fills = []
        self.single_markers = []
        self.summary_labels = []
        self.harmonic_labels = []
        self.harmonic_points = []
        self.power_annotations = []
        for row in range(2):
            plot = self.widget.addPlot(row=2*row+1, col=0, axisItems={
                'bottom':FrequencyAxis('bottom'), 'left':FrequencyAxis('left')})
            plot.showGrid(x=True, y=True, alpha=.2)
            plot.getViewBox().sigXRangeChanged.connect(lambda *args,index=row:self._redraw_fft_trace(index))
            plot.getViewBox().sigResized.connect(lambda *args,index=row:self._redraw_fft_trace(index))
            points = plot.plot(pen=None,symbol='o',symbolSize=6,symbolBrush='#ff9f43',symbolPen=None)
            points.setZValue(80)
            labels = []
            for _ in range(10):
                label = pg.TextItem('',color='#ffbd80',anchor=(0,1),fill=pg.mkBrush(23,28,36,150))
                font = QtGui.QFont(QtWidgets.QApplication.font())
                font.setPointSizeF(9.0)
                label.setFont(font)
                label.setZValue(70);plot.addItem(label,ignoreBounds=True);label.hide()
                labels.append(label)
            self.harmonic_points.append(points);self.harmonic_labels.append(labels)
            band = pg.LinearRegionItem(movable=True, brush=pg.mkBrush(0,229,255,18),
                                       pen=pg.mkPen(0,229,255,65))
            band.setZValue(-10)
            floor = pg.InfiniteLine(angle=0, movable=False,
                                    pen=pg.mkPen('#8996a4',style=QtCore.Qt.PenStyle.DashLine))
            caption = pg.TextItem('',color='#b9c7d3',anchor=(1,0),fill=pg.mkBrush(23,28,36,150))
            caption.setFont(font)
            caption.setZValue(70)
            for item in (band,floor,caption):
                plot.addItem(item,ignoreBounds=True);item.hide()
            self.power_annotations.append((band,floor,caption))
            band.sigRegionChanged.connect(self._power_band_dragged)
            band.sigRegionChangeFinished.connect(self._power_band_finished)
            marker = pg.TextItem('SINGLE', color='#ff9f43', anchor=(1,0), fill=pg.mkBrush('#24201b'))
            marker.setZValue(100)
            plot.addItem(marker, ignoreBounds=True)
            def position_marker(view, ranges, *args, item=marker):
                item.setPos(ranges[0][1], ranges[1][1])
            plot.getViewBox().sigRangeChanged.connect(position_marker)
            marker.hide()
            self.single_markers.append(marker)
            summary = pg.TextItem('',color='#d8e5ef',anchor=(0,0),fill=pg.mkBrush('#171c24'))
            summary.setZValue(90); plot.addItem(summary,ignoreBounds=True)
            def position_summary(view,ranges,*args,item=summary):
                item.setPos(ranges[0][0],ranges[1][1])
            plot.getViewBox().sigRangeChanged.connect(position_summary)
            summary.hide(); self.summary_labels.append(summary)
            curve = plot.plot(pen=pg.mkPen('#00e5ff', width=1))
            fill = plot.plot(pen=None)
            fill.setZValue(-5)
            self.fft_fills.append(fill)
            image = pg.ImageItem(axisOrder='row-major')
            image.setLookupTable(pg.colormap.get('viridis').getLookupTable())
            plot.addItem(image)
            bar = pg.ColorBarItem(values=(-100, 10), colorMap=pg.colormap.get('viridis'),
                                  interactive=False)
            bar.axis.tickStrings = lambda values,scale,spacing: [number(value*scale,formats.n_4g) for value in values]
            bar.setImageItem(image, insert_in=plot)
            self.plots.append(plot); self.curves.append(curve)
            self.images.append(image); self.bars.append(bar)
        group = QtWidgets.QGroupBox('ANÁLISIS')
        box = QtWidgets.QVBoxLayout(group)
        self.buttons = QtWidgets.QButtonGroup(group)
        for i, text in enumerate(('V/t', 'FFT', 'Heatmap', 'Bode')):
            button = QtWidgets.QPushButton(text, group)
            button.setCheckable(True); button.setFixedHeight(34)
            button.setStyleSheet("QPushButton {padding:2px; font-size:11px; background:#21252f; border:1px solid #323946; border-radius:6px;} QPushButton:checked {background:#006879; border:1px solid #00e5ff; color:white;}")
            self.buttons.addButton(button, i); button.hide()
            if i != 3:
                button.clicked.connect(lambda checked, mode=i: self.set_mode(mode))
            else:
                self.bode_menu = QtWidgets.QMenu(button)
                self.bode_menu.setStyleSheet('QMenu {background:#1a1d24; color:#e6eaf0; '
                    'border:1px solid #323946; padding:4px;} '
                    'QMenu::item {padding:7px 18px;} '
                    'QMenu::item:selected {background:#323946;}')
                self.bode_actions = []
                from PyQt6.QtGui import QActionGroup
                methods = QActionGroup(self.bode_menu)
                methods.setExclusive(True)
                for index, title in enumerate(('Bode tono','Bode pulso','Bode sweep')):
                    action = self.bode_menu.addAction(title)
                    action.setCheckable(True); methods.addAction(action)
                    action.setChecked(index == 0)
                    action.triggered.connect(lambda checked, method=index: self.select_bode(method))
                    self.bode_actions.append(action)
                button.setMenu(self.bode_menu)
            if i == 0: button.setChecked(True)
        # Use the same neutral tick asset as the channel controls.
        from pathlib import Path
        check_icon = (Path(__file__).parent / 'assets/check_neutral.svg').as_posix()
        group.setStyleSheet(f"""QCheckBox {{background:transparent; border:none; padding:2px;}}
            QCheckBox::indicator {{width:14px; height:14px; border:1px solid #737d8d;
                border-radius:3px; background:#171920;}}
            QCheckBox::indicator:checked {{image:url("{check_icon}");}}
            QCheckBox::indicator:unchecked {{image:none;}}""")
        from monitor.v17.app import GeneratorComboBox
        self.mode_combo = GeneratorComboBox()
        names = ('V(t)', 'FFT', 'Heatmap', 'Bode')
        icons = ('analysis_time', 'analysis_fft', 'analysis_heatmap',
                 'analysis_tone')
        for name, icon in zip(names, icons):
            self.mode_combo.addItem(QtGui.QIcon(str(Path(__file__).parent / f'assets/{icon}.svg')), name)
        self.mode_combo.setIconSize(QtCore.QSize(18,18))
        self.mode_combo.setFixedHeight(28)
        self.mode_combo.setMinimumWidth(0)
        self.mode_combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.mode_combo.currentIndexChanged.connect(
            self.set_mode)
        mode_row = QtWidgets.QGridLayout()
        mode_row.setContentsMargins(0,0,0,0)
        mode_label = QtWidgets.QLabel('Modo')
        mode_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        mode_row.setColumnStretch(0,1); mode_row.setColumnStretch(1,1)
        mode_row.setHorizontalSpacing(4)
        self.mode_combo.setStyleSheet("QComboBox {padding: 2px 2px;} QComboBox::drop-down {width: 10px; border: none;}")
        mode_row.addWidget(mode_label,0,0)
        mode_row.addWidget(self.mode_combo,1,0)
        self.secondary_label = QtWidgets.QLabel('Eje horizontal')
        self.secondary_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.secondary_stack = QtWidgets.QStackedWidget()
        self.secondary_stack.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.secondary_stack.setFixedHeight(28)
        mode_row.addWidget(self.secondary_label,0,1)
        mode_row.addWidget(self.secondary_stack,1,1)
        box.addLayout(mode_row)
        self.settings = QtWidgets.QWidget()
        grid = QtWidgets.QFormLayout(self.settings)
        self.settings_form = grid
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(2)
        self.size = GeneratorComboBox(); self.size.addItems(['256','512','1024','2048','4096','8192','16384','32768','65536']); self.size.setCurrentText('2048')
        self.fft_mode = GeneratorComboBox()
        for name, icon in (('Spectre','spectrum'), ('Power','power'), ('Distort','distortion'), ('Transfer','transfer'), ('Radio','spectrum')):
            self.fft_mode.addItem(QtGui.QIcon(str(Path(__file__).parent / f'assets/fft_{icon}.svg')), name)
        self.fft_mode.setIconSize(QtCore.QSize(18,18))
        self.fft_mode.setToolTip('Spectre: magnitud y fase. Power: densidad y bandas. Distort: armónicos. Transfer: respuesta Y / referencia X.')
        self.heatmap_size = GeneratorComboBox(); self.heatmap_size.addItems(['256','512','1024','2048','4096','8192','16384','32768','65536']); self.heatmap_size.setCurrentText('2048')
        def sync_size(source, target):
            target.blockSignals(True); target.setCurrentText(source.currentText()); target.blockSignals(False)
            self.reset()
        self.heatmap_size.currentIndexChanged.connect(lambda: sync_size(self.heatmap_size, self.size))
        self.size.currentIndexChanged.connect(lambda: sync_size(self.size, self.heatmap_size))
        self.averages = QtWidgets.QComboBox(); self.averages.addItems(['1', '2', '4', '8', '16']); self.averages.setCurrentText('4')
        self.spectrum_view = QtWidgets.QComboBox(); self.spectrum_view.addItems(['Magnitud', 'Fase'])
        self.power_scale = QtWidgets.QComboBox(); self.power_scale.addItems(['dB re 1 V²/Hz', 'V²/Hz'])
        self.transfer_view = QtWidgets.QComboBox(); self.transfer_view.addItems(['Fase', 'Coherencia', 'Retardo de grupo'])
        self.band_low = QtWidgets.QDoubleSpinBox(); self.band_high = QtWidgets.QDoubleSpinBox()
        self.signal_low = QtWidgets.QDoubleSpinBox(); self.signal_high = QtWidgets.QDoubleSpinBox()
        for control in (self.band_low, self.band_high, self.signal_low, self.signal_high):
            control.setRange(0, 1000000); control.setDecimals(2); control.setSuffix(' Hz')
        self.band_high.setSpecialValueText('Nyquist'); self.band_high.setValue(0)
        self._band_by_mode = {'Power': (100.0,500.0), 'Distort': (0.0,0.0)}
        self._band_mode = self._fft_kind()
        self._syncing_power_band = False
        self.signal_high.setSpecialValueText('Auto'); self.signal_high.setValue(0)
        self.fundamental = QtWidgets.QDoubleSpinBox(); self.fundamental.setRange(0,1000000); self.fundamental.setDecimals(2); self.fundamental.setSuffix(' Hz'); self.fundamental.setSpecialValueText('Auto')
        self.harmonics = QtWidgets.QSpinBox(); self.harmonics.setRange(2,10); self.harmonics.setValue(10)
        self.window = QtWidgets.QComboBox(); self.window.addItems(list(WINDOWS))
        self.overlap = QtWidgets.QComboBox(); self.overlap.addItems(['0 %','50 %','75 %']); self.overlap.setCurrentIndex(1)
        self.scale = QtWidgets.QComboBox(); self.scale.addItems(['dBV', 'V pico'])
        self.channels = []
        for index in range(2):
            combo = GeneratorComboBox(); combo.addItems(['Ninguno', 'CH1', 'CH2', 'FILTER', 'RADIO']); combo.setCurrentIndex(index + 1)
            self.channels.append(combo)
        self.seconds = QtWidgets.QSpinBox(); self.seconds.setRange(2, 60); self.seconds.setValue(10); self.seconds.setSuffix(' s')
        self.remove_dc = QtWidgets.QCheckBox('Quitar componente DC'); self.remove_dc.setChecked(True)
        self.fft_option_controls = [self.size, self.averages, self.spectrum_view, self.power_scale,
            self.band_low, self.band_high, self.signal_low, self.signal_high, self.fundamental, self.harmonics, self.transfer_view]
        for label, control in [('Muestras',self.size), ('Promedios', self.averages), ('Vista Spectre',self.spectrum_view),
            ('Escala PSD',self.power_scale), ('Banda desde',self.band_low), ('Banda hasta',self.band_high),
            ('Señal desde',self.signal_low), ('Señal hasta',self.signal_high), ('Fundamental',self.fundamental),
            ('Armónicos hasta',self.harmonics), ('Vista Transfer',self.transfer_view)]:
            grid.addRow(label, control)
            signal = control.valueChanged if isinstance(control, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)) else control.currentIndexChanged
            signal.connect(self.reset)
        self.fft_mode.currentIndexChanged.connect(self._fft_mode_changed)
        for label, control in [('Ventana',self.window), ('Solapamiento',self.overlap),
                               ('Escala',self.scale),
                               ('Historia',self.seconds)]:
            grid.addRow(label, control)
            signal = control.valueChanged if isinstance(control, QtWidgets.QSpinBox) else control.currentIndexChanged
            signal.connect(self.reset)
        self.transfer_reference = GeneratorComboBox()
        self.transfer_response = GeneratorComboBox()
        for combo,default in ((self.transfer_reference,'CH1'),(self.transfer_response,'CH2')):
            combo.addItems(['CH1','CH2','FILTER','RADIO']);combo.setCurrentText(default)
            combo.currentIndexChanged.connect(self._transfer_pair_changed)
        grid.addRow('Referencia X',self.transfer_reference)
        grid.addRow('Respuesta Y',self.transfer_response)
        self.plot_headers = []
        self.header_widgets = []
        self.header_labels = []
        self.header_attached = set()
        for index, combo in enumerate(self.channels):
            # Embed the existing selector in the graphics layout: it stays
            # reachable even when its trace is set to Ninguno.
            control = combo
            control.setProperty('centerInWholeBox',True)
            control.setFixedSize(110,26)
            control.setToolTip('Entrada del gráfico; Ninguno oculta la curva.')
            header = QtWidgets.QWidget()
            header.setFixedHeight(38)
            header.setStyleSheet('QWidget {background:transparent; border:none;} QComboBox {background:#1a1d24; color:#e6eaf0; border:1px solid #323946; border-radius:5px; padding:2px 6px;} QComboBox QAbstractItemView {background:#1a1d24; color:#e6eaf0; selection-background-color:#323946;}')
            row = QtWidgets.QHBoxLayout(header)
            row.setContentsMargins(4,6,4,6);row.setSpacing(8)
            row.addStretch();row.addWidget(control)
            label = QtWidgets.QLabel('');label.setStyleSheet('color:#aeb8c8; background:transparent;')
            row.addWidget(label);row.addStretch()
            # Native widgets keep combo popups outside the graphics scene.
            # Reserve a scene row, then position its native header above it.
            proxy = QtWidgets.QGraphicsWidget()
            proxy.setMinimumHeight(38);proxy.setMaximumHeight(38)
            header.setParent(self.widget.viewport())
            self.header_widgets.append(header)
            self.plot_headers.append(proxy);self.header_labels.append(label)
            control.currentIndexChanged.connect(self.reset)
            control.currentIndexChanged.connect(lambda: self.configure_plots())
        self.widget.scene().changed.connect(self._position_headers)
        self.widget.scene().sigMouseClicked.connect(self._radio_fft_clicked)
        self.radio_tune_drag=RadioTuneDrag(self)
        self.size.currentIndexChanged.connect(self.reset)
        grid.addRow(self.remove_dc); self.remove_dc.toggled.connect(self.reset)
        self.log_frequency = QtWidgets.QCheckBox('Frecuencia logarítmica')
        self.log_frequency.toggled.connect(self.reset)
        grid.insertRow(0, self.log_frequency)
        self.lock_axes = QtWidgets.QCheckBox('Compartir escala')
        self.lock_axes.toggled.connect(self.reset)
        grid.insertRow(0, self.lock_axes)
        self.info = StatusLabel(''); self.info.setWordWrap(True)
        self.info.setStyleSheet('color:#aeb8c8; background:transparent; border:none; margin-top:10px;')
        grid.addRow(self.info)
        self.metrics = QtWidgets.QLabel(''); self.metrics.setWordWrap(True); self.metrics.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.metrics.setStyleSheet('color:#d3dfed; background:transparent; border:none; margin-top:6px;')
        grid.addRow(self.metrics)
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        options = QtWidgets.QWidget()
        options_layout = QtWidgets.QVBoxLayout(options)
        options_layout.setContentsMargins(0,0,0,0)
        self.temporal_settings = owner.temporal_settings
        temporal_form = self.temporal_settings.layout()
        axis_row = temporal_form.takeRow(owner.btn_xaxis_toggle)
        if axis_row.labelItem: axis_row.labelItem.widget().deleteLater()
        self.bode_method_combo = GeneratorComboBox()
        for title,icon in zip(('Tono','Pulso','Sweep'),('analysis_tone','mode_pulse','mode_sweep')):
            self.bode_method_combo.addItem(QtGui.QIcon(str(Path(__file__).parent / f'assets/{icon}.svg')),title)
        self.bode_method_combo.currentIndexChanged.connect(self.select_bode)
        for control in (owner.btn_xaxis_toggle,self.fft_mode,self.heatmap_size,self.bode_method_combo):
            control.setFixedHeight(28); control.setMinimumWidth(0)
            control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            self.secondary_stack.addWidget(control)
        options_layout.addWidget(self.temporal_settings)
        options_layout.addWidget(self.settings)
        self.bode_settings = QtWidgets.QWidget()
        bode_form = QtWidgets.QFormLayout(self.bode_settings)
        bode_form.setContentsMargins(0,0,0,0)
        bode_form.setVerticalSpacing(2)
        self.bode = BodePanels(self, bode_form)
        options_layout.addWidget(self.bode_settings)
        options_layout.addStretch()
        scroll.setWidget(options)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        box.addWidget(scroll, 1)
        self.group = group
        layout.addWidget(group, 1)
        self.set_mode(0)

    def clear_single_marker(self, clear_snapshot=True):
        for marker in self.single_markers:
            marker.hide()
        if clear_snapshot: self._single_snapshot = None

    def reset(self, *args):
        self._fft_trace_cache = {}
        self._distortion_generation += 1
        self._distortion_cache = {}
        self._distortion_submitted = -float('inf')
        self.clear_single_marker(clear_snapshot=False)
        self.last_end = None; self.context = None; self.frames.clear()
        self._view_base_ranges={}
        self.y_ranges = {}
        self.shrink_since = {}
        for curve, image in zip(self.curves, self.images):
            curve.setData([], []); image.clear()
        for fill in self.fft_fills: fill.setData([], [])
        self.analysis_result = None
        self.statistics_by_channel = {}
        self._power_fit_cache = {}
        if hasattr(self, 'metrics'): self.metrics.clear()
        for points, labels in zip(self.harmonic_points,self.harmonic_labels):
            points.setData([],[])
            for label in labels: label.hide()
        for label in self.summary_labels: label.setText('')
        for items in self.power_annotations:
            for item in items: item.hide()
        self.refresh_measurement_panel()
        if args and self._single_snapshot is not None:
            QtCore.QTimer.singleShot(0, self._render_frozen)

    def transfer_pair(self):
        return self.transfer_reference.currentText(),self.transfer_response.currentText()

    def transfer_label(self):
        x,y=self.transfer_pair()
        return f'{y} / {x}'

    def _transfer_pair_changed(self):
        self.reset(True)
        self.configure_plots()
        self.refresh_measurement_panel()

    def measurement_channel_changed(self):
        if getattr(self, '_updating_measurements', False):
            return
        self.refresh_measurement_panel()
        if self.owner.active_meas_channel not in self.statistics_by_channel and self._fft_kind() != 'Transfer':
            self.reset(0)

    def refresh_measurement_panel(self):
        owner = self.owner
        if not hasattr(owner, '_measurement_cards') or getattr(self, '_updating_measurements', False):
            return
        self._updating_measurements = True
        try:
            combo = owner.meas_channel_combo
            fft = self.mode == 1
            was_fft = getattr(self, '_measurement_fft_active', False)
            self._measurement_fft_active = fft
            if fft and not was_fft:
                self._temporal_meas_channel = combo.currentText()
                self._fft_meas_channel = 'CH2' if combo.currentText() == 'CH2' else 'CH1'
            if fft and combo.currentText() in ('CH1', 'CH2', 'FILTER', 'RADIO'):
                self._fft_meas_channel = combo.currentText()
            kind = self._fft_kind()
            available=['CH1','FILTER','RADIO'] if getattr(owner,'applied_configuration',None) is not None and owner.applied_configuration.channels==1 else ['CH1','CH2','FILTER','RADIO']
            choices = [self.transfer_label()] if fft and kind == 'Transfer' else available
            desired = choices[0] if fft and kind == 'Transfer' else getattr(self, '_fft_meas_channel', 'CH1') if fft else getattr(self, '_temporal_meas_channel', combo.currentText())
            if desired not in choices: desired=choices[0]
            if [combo.itemText(i) for i in range(combo.count())] != choices:
                combo.blockSignals(True); combo.clear(); combo.addItems(choices)
                combo.setCurrentText(desired); combo.blockSignals(False)
                owner._on_meas_channel_changed(combo.currentText())
            combo.setEnabled(not (fft and kind == 'Transfer'))
            combo.setToolTip('Respuesta Y / referencia X; señales alineadas en el tiempo.' if fft and kind == 'Transfer' else 'Entrada para las estadísticas del panel.')
            if not fft:
                titles = ['V MAX','V MIN','V P-P','V RMS','V MEDIA','F SEÑAL']
                for i,(card,value) in enumerate(zip(owner._measurement_cards,owner._measurement_values)):
                    card.setVisible(i < 6)
                    if i < 6:
                        card.layout().itemAt(0).widget().setText(titles[i])
                        if was_fft: value.setText('--')
                        card.setToolTip('')
                return
            name = self.transfer_label() if kind == 'Transfer' else combo.currentText()
            result = self.statistics_by_channel.get(name)
            def f(value, unit='', precision=3):
                if kind == 'Power' and np.isfinite(value):
                    return number(value, '.3f') + (' '+unit if unit else '')
                if unit == 'Hz' and np.isfinite(value) and abs(value) >= 1000:
                    return self._metric(value/1000, 'kHz', precision)
                return self._metric(value, unit, precision)
            tooltip = self.metrics.text() + '\n' + self.metrics.toolTip()
            if kind == 'Power': tooltip += '\nPiso de ruido: dB re 1 V²/Hz.'
            if kind == 'Spectre':
                titles = ['F DOMINANTE','AMPLITUD PICO','FASE','PICOS','Δf','ENBW']
                rows = ['N/A']*6
                if result is not None:
                    peak = result.peaks[0] if result.peaks else None
                    rows = [f(peak['frequency'],'Hz') if peak else 'N/A', f(peak['amplitude'],'V') if peak else 'N/A',
                        f(result.phase[peak['bin']],'°') if peak else 'N/A',str(len(result.peaks)),f(result.df,'Hz'),f(result.enbw,'Hz')]
                    tooltip = 'Picos '+ ' · '.join(f(p['frequency'],'Hz') for p in result.peaks)+'\nFase del último bloque, respecto de su inicio.'
            elif kind == 'Power':
                titles = ['V RMS','P BANDA','PISO RUIDO','SNR','20-200Hz','200Hz-2kHz','2kHz-Nq']
                rows = ['N/A']*7
                if result is not None and hasattr(result,'power_metrics'):
                    m = result.power_metrics; nyquist = result.frequencies[-1]
                    bands = [(20,200),(200,2000),(2000,nyquist)]
                    rows = [f(m['rms'],'V'),f(m['power'],'V²'),f(10*np.log10(m['noise_floor']),'dB') if m['noise_floor'] > 0 else 'N/A',f(m['snr_db'],'dB')]
                    rows += [f(analysis.band_power(result,lo,np.nextafter(min(hi,nyquist),-np.inf) if hi < nyquist else nyquist),'V²') if lo < nyquist else 'N/A' for lo,hi in bands]
            elif kind == 'Distort':
                titles = ['F FUNDAMENTAL','THD','THD+N','SINAD','SNR','ARMÓNICOS']
                rows = ['N/A']*6
                if result is not None and hasattr(result,'distortion'):
                    d = result.distortion
                    if d['valid']:
                        rows = [f(d['fundamental'],'Hz'),f(d['thd']*100,'%'),f(d['thdn']*100,'%'),f(d['sinad_db'],'dB'),f(d['snr_db'],'dB'),str(max(0,len(d['harmonics'])-1))]
                        tooltip = name+' · '+ ' · '.join('H'+str(h['order'])+' '+f(h['rms'],'V RMS') for h in d['harmonics'])
                    else: tooltip = d['reason']
            else:
                titles = ['F REFERENCIA','GANANCIA','FASE','COHERENCIA','RETARDO','SEGMENTOS']
                rows = ['N/A']*6
                if result is not None:
                    peak = 1+int(np.argmax(result['pxx'][1:]))
                    delay = result['group_delay_s']; finite = delay[np.isfinite(delay)]
                    rows = [f(result['frequencies'][peak],'Hz'),f(result['gain_db'][peak],'dB'),f(result['phase_deg'][peak],'°'),
                        f(result['coherence'][peak]),f(np.median(finite)*1e6,'µs') if len(finite) else 'N/A',str(result['segments'])]
                    tooltip += '\nGanancia, fase y coherencia en el pico de referencia; retardo mediano de bins coherentes.'
            for i,(card,value) in enumerate(zip(owner._measurement_cards,owner._measurement_values)):
                card.setVisible(i < len(titles))
                if i < len(titles):
                    card.layout().itemAt(0).widget().setText(titles[i])
                    value.setText(rows[i].replace(' (numérico)', '').replace(' (salida cero)', ''))
                    if kind == 'Power':
                        descriptions = [
                            'Valor RMS de la banda seleccionada, en V.',
                            'Potencia integrada de la banda seleccionada, en V².',
                            'Piso ruido: densidad media de la banda excluyendo los picos, en dB re 1 V²/Hz.',
                            'Relación señal/ruido del ajuste tonal, excluyendo los armónicos, en dB.',
                            'Potencia integrada entre 20 y 200 Hz, en V².',
                            'Potencia integrada entre 200 Hz y 2 kHz, en V².',
                            'Potencia integrada entre 2 kHz y Nyquist, en V².',
                        ]
                        card.setToolTip(descriptions[i])
                    else: card.setToolTip(tooltip)
        finally:
            self._updating_measurements = False

    def _render_frozen(self):
        if self._single_snapshot is not None and not self.owner.is_running and self.mode in (1,2):
            self.render(single_owner=self._single_snapshot)
            self._show_single_markers()

    def _show_single_markers(self):
        for plot, marker in zip(self.plots, self.single_markers):
            ranges = plot.getViewBox().viewRange()
            marker.setPos(ranges[0][1], ranges[1][1]); marker.show()

    def _fft_kind(self):
        return 'Spectre' if self.fft_mode.currentText()=='Radio' else self.fft_mode.currentText()

    def _fft_mode_changed(self, *args):
        if hasattr(self,'radio_tune_drag'):self.radio_tune_drag.clear()
        self.radio_fft_view=self.fft_mode.currentText()=='Radio'
        if self._band_mode in self._band_by_mode:
            self._band_by_mode[self._band_mode] = (self.band_low.value(),self.band_high.value())
        self._band_mode = self._fft_kind()
        if self._band_mode in self._band_by_mode:
            low,high = self._band_by_mode[self._band_mode]
            for control,value in ((self.band_low,low),(self.band_high,high)):
                blocker = QtCore.QSignalBlocker(control)
                control.setValue(value)
                del blocker
        self.reset()
        if hasattr(self, 'bode'): self.configure_plots()
        self._configure_fft_options()
        self._render_frozen()

    def _power_band_dragged(self, region):
        if self._syncing_power_band or self.mode != 1 or self._fft_kind() != 'Power': return
        low,high = region.getRegion()
        if self.log_frequency.isChecked(): low,high = 10**low,10**high
        nyquist = self.owner.current_fs_hz/2
        low,high = max(0,min(low,nyquist)),max(0,min(high,nyquist))
        for control,value in ((self.band_low,low),(self.band_high,high)):
            blocker = QtCore.QSignalBlocker(control)
            control.setValue(value)
            del blocker
        self._band_by_mode['Power'] = (self.band_low.value(),self.band_high.value())

    def _power_band_finished(self, region):
        if self._syncing_power_band: return
        self._power_band_dragged(region)
        self.reset(True)

    def _configure_fft_options(self):
        kind = self._fft_kind()
        for control in (self.transfer_reference,self.transfer_response):
            self.settings_form.setRowVisible(control,self.mode == 1 and kind == 'Transfer')
        shown = {self.size, self.averages}
        if kind == 'Spectre': shown.add(self.spectrum_view)
        if kind == 'Power': shown.update((self.power_scale,self.band_low,self.band_high))
        if kind == 'Distort': shown.update((self.fundamental,self.harmonics,self.band_low,self.band_high))
        if kind == 'Transfer': shown.add(self.transfer_view)
        for control in self.fft_option_controls:
            self.settings_form.setRowVisible(control, self.mode == 1 and control in shown)
        for control in (self.scale,self.lock_axes):
            self.settings_form.setRowVisible(control, self.mode == 2 or (self.mode == 1 and kind != 'Transfer' and (control != self.scale or kind in ('Spectre','Distort'))))
        self.settings_form.setRowVisible(self.seconds, self.mode == 2)
        self.settings_form.setRowVisible(self.metrics, False)

    def select_bode(self, method):
        self.bode.tabs.setCurrentIndex(method)
        self.bode_actions[method].setChecked(True)
        self.bode_method_combo.blockSignals(True)
        self.bode_method_combo.setCurrentIndex(method)
        self.bode_method_combo.blockSignals(False)
        self.buttons.button(3).setToolTip(self.bode_actions[method].text())
        self.set_mode(3)

    def view_settings(self):
        key=(self.mode,self._fft_kind(),self.scale.currentIndex(),
             self.spectrum_view.currentIndex(),self.transfer_view.currentIndex(),
             self.power_scale.currentIndex(),self.log_frequency.isChecked(),
             self.bode.log_frequency.isChecked(),self.bode.tabs.currentIndex())
        if not hasattr(self,'_view_settings'):self._view_settings={}
        settings=self._view_settings.setdefault(key,dict(h_scale=1.,h_pos=0.,v_scale=1.,v_pos=0.))
        if self.mode==1:
            settings['h_scale']=min(1.,settings['h_scale'])
            limit=max(0.,(1-settings['h_scale'])/2)
            settings['h_pos']=max(-limit,min(limit,settings['h_pos']))
        return settings

    def _set_view_range(self,index,axis,low,high,padding=0):
        if not np.isfinite([low,high]).all() or high<=low:return
        if not hasattr(self,'_view_base_ranges'):self._view_base_ranges={}
        # Store unmodified bounds, so repeated frames never compound zoom/pan.
        span=high-low
        low-=span*padding;high+=span*padding
        self._view_base_ranges[index,axis]=(low,high)
        self._apply_view_range(index,axis)

    def _apply_view_range(self,index,axis):
        low,high=self._view_base_ranges[index,axis]
        params=self.view_settings();prefix='h' if axis=='x' else 'v'
        span=high-low;center=(low+high)/2+span*params[prefix+'_pos']
        half=span*params[prefix+'_scale']/2
        plot=self.plots[index]
        plot.disableAutoRange(axis=pg.ViewBox.XAxis if axis=='x' else pg.ViewBox.YAxis)
        setter=plot.setXRange if axis=='x' else plot.setYRange
        if self.mode==1 and axis=='x':
            setter(max(low,center-half),min(high,center+half),padding=0)
        else:setter(center-half,center+half,padding=0)

    def change_view(self,**changes):
        self.view_settings().update(changes)
        for (index,axis) in list(getattr(self,'_view_base_ranges',{})):
            self._apply_view_range(index,axis)

    def reset_view(self):
        self.view_settings().update(h_scale=1.,h_pos=0.,v_scale=1.,v_pos=0.)
        self.change_view()

    def refresh_bode_view(self):
        if self.mode!=3:return
        log=self.bode.log_frequency.isChecked()
        low,high=self.bode.start.value(),self.bode.end.value()
        if high>low:
            for index in range(2):self._set_view_range(index,'x',np.log10(low) if log else low,np.log10(high) if log else high)
        for index in range(2):
            arrays=[]
            for curves in self.bode.curve_sets:
                _,values=curves[index].getData()
                if values is not None:
                    finite=np.asarray(values)[np.isfinite(values)]
                    if len(finite):arrays.append(finite)
            if arrays:
                data=np.concatenate(arrays);low=float(data.min());high=float(data.max())
                if high==low:low-=1;high+=1
                self._set_view_range(index,'y',low,high,padding=.05)

    def set_mode(self, mode):
        if hasattr(self,'radio_tune_drag'):self.radio_tune_drag.clear()
        if self.bode.active: self.bode.cancel('Cambio de modo')
        if mode==4:  # Compatibility for saved callers; Radio lives inside FFT.
            mode=1
            self.fft_mode.setCurrentText('Radio')
        self.radio_fft_view=self.fft_mode.currentText()=='Radio'
        selected_mode=mode
        self.mode=mode
        self.buttons.button(mode).setChecked(True)
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(selected_mode)
        self.mode_combo.blockSignals(False)
        self.secondary_label.setText(('Eje horizontal','Modo FFT','Muestras','Método')[mode])
        self.secondary_stack.setCurrentIndex(mode)
        self.stack.setCurrentIndex(0 if mode == 0 else 1)
        self.settings.setEnabled(mode in (1,2))
        self.settings.setVisible(mode in (1,2))
        self.temporal_settings.setVisible(mode == 0)
        self.bode_settings.setVisible(mode == 3)
        self.reset()
        self._configure_fft_options()
        self.configure_plots()
        if mode == 3:
            self.bode.draw()
            if not self.bode.result:
                self.bode.status.setText('Listo · pulsar Repetir o Agregar para iniciar el barrido.')
        if getattr(self.owner,'_central_status_ready',False):self.owner._refresh_status_boxes()
        self._render_frozen()

    def _position_headers(self, *args):
        for i, spacer in enumerate(self.plot_headers):
            header=self.header_widgets[i]
            visible=i in self.header_attached and self.mode in (1,2)
            header.setVisible(visible)
            if visible:
                rect=self.widget.mapFromScene(spacer.sceneBoundingRect()).boundingRect()
                header.setGeometry(rect.x(),rect.y(),max(1,rect.width()),header.height())
                header.raise_()

    def configure_plots(self):
        heat = self.mode == 2
        kind = self._fft_kind()
        for points, labels in zip(self.harmonic_points,self.harmonic_labels):
            points.setVisible(self.mode == 1 and kind in ('Distort','Spectre'))
            for label in labels: label.hide()
        for label in self.summary_labels: label.hide()
        for items in self.power_annotations:
            for item in items: item.hide()
        for fill in self.fft_fills: fill.setVisible(False)
        for curves in self.bode.curve_sets[1:] + self.bode.shadows:
            for curve in curves: curve.setVisible(self.mode == 3)
        for i, plot in enumerate(self.plots):
            channel = self.channels[i].currentText()
            if self.mode == 3: channel = ('Ganancia '+self.bode.pair_label(), 'Fase '+self.bode.pair_label())[i]
            if self.mode == 1 and kind == 'Transfer': channel = ('Ganancia '+self.transfer_label(), self.transfer_view.currentText()+' '+self.transfer_label())[i]
            visible = channel != 'Ninguno'
            if not visible and i in self.attached:
                self.widget.ci.removeItem(plot)
                self.attached.remove(i)
            elif visible and i not in self.attached:
                self.widget.ci.addItem(plot, row=2*i+1, col=0)
                self.attached.add(i)
            plot.setVisible(visible)
            self.widget.ci.layout.setRowStretchFactor(2*i+1, 1 if visible else 0)
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
            if self.mode == 1:
                if kind == 'Transfer':
                    label, unit = ('Ganancia','dB') if i == 0 else {'Fase':('Fase','°'),'Coherencia':('Coherencia',''),'Retardo de grupo':('Retardo de grupo','s')}[self.transfer_view.currentText()]
                elif kind == 'Power': label,unit = 'PSD',self.power_scale.currentText()
                elif kind == 'Spectre' and self.spectrum_view.currentIndex() == 1: label,unit = 'Fase (inicio del último bloque)','°'
                else: label,unit = 'Amplitud pico',('dB re 1 V pico' if self.scale.currentIndex()==0 else 'V pico')
                plot.setTitle(channel+' · '+kind); plot.setLabel('left',label,units=unit)
            header_visible = self.mode in (1,2) and not (self.mode == 1 and kind == 'Transfer')
            header = self.plot_headers[i]
            if header_visible and i not in self.header_attached:
                self.widget.ci.addItem(header,row=2*i,col=0);self.header_attached.add(i)
            elif not header_visible and i in self.header_attached:
                self.widget.ci.removeItem(header);self.header_attached.remove(i)
            header.setVisible(header_visible)
            if header_visible:
                plot.setTitle(None)
                self.header_labels[i].setText('· '+('Heatmap' if heat else kind))
                self.channels[i].setProperty('selectedTextColor',self.owner.channel_colors.get(self.channels[i].currentText(),'#aeb8c8'))
                self.channels[i].update()
            plot.setXLink(None); plot.setYLink(None)
            if self.mode == 1:
                plot.disableAutoRange()
            elif self.mode == 3:
                plot.disableAutoRange(axis=pg.ViewBox.XAxis)
                plot.enableAutoRange(axis=pg.ViewBox.YAxis)
                if self.bode.end.value() > self.bode.start.value():
                    log = self.bode.log_frequency.isChecked()
                    self._set_view_range(i,'x',np.log10(self.bode.start.value()) if log else self.bode.start.value(),
                                   np.log10(self.bode.end.value()) if log else self.bode.end.value())
            else:
                plot.enableAutoRange()
        audio_names={'RADIO'}
        filter_source=getattr(self.owner,'filter_source',None)
        if filter_source is not None and filter_source.currentText()=='RADIO':audio_names.add('FILTER')
        mixed_domains=bool({c.currentText() for c in self.channels}&audio_names) and bool(
            {c.currentText() for c in self.channels}-audio_names-{'Ninguno'})
        if self.mode == 1 and kind != 'Transfer' and self.lock_axes.isChecked() and self.attached == {0, 1} and not mixed_domains:
            self.plots[1].setXLink(self.plots[0]); self.plots[1].setYLink(self.plots[0])

        self.refresh_radio_overlay()
        self._position_headers()
        if hasattr(self.owner,'_sync_analysis_controls'):self.owner._sync_analysis_controls()

    def _radio_fft_clicked(self,event):
        if self.mode!=1 or not self.radio_fft_view or event.button()!=QtCore.Qt.MouseButton.LeftButton:
            return
        if getattr(getattr(self.owner,'_radio_multiscan',None),'active',False):return
        for i,plot in enumerate(self.plots):
            view=plot.getViewBox()
            if i not in self.attached or self.channels[i].currentText()!='CH1' or not view.sceneBoundingRect().contains(event.scenePos()):
                continue
            x=view.mapSceneToView(event.scenePos()).x()
            frequency=10**x if self.log_frequency.isChecked() else x
            if self._tune_radio_fft_frequency(frequency):event.accept()
            return

    def _tune_radio_fft_frequency(self,frequency):
        from monitor.v17.radio_tuning import alias_frequency
        owner=self.owner;rate=owner.applied_configuration.actual_rate
        if not np.isfinite(frequency) or not 0<frequency<rate/2:return False
        us=owner.radio_us.isChecked()
        rf=rate-frequency if us and owner.radio_frequency.value()*1000>rate/2 else frequency
        if us:
            # A scanned RF hypothesis takes priority close to its alias marker.
            tolerance=max(1,2*rate/65536)
            nearby=[p['frequency'] for p in owner.radio_candidates
                    if abs(abs((p['frequency']+rate/2)%rate-rate/2)-frequency)<=tolerance]
            if nearby:
                rf=min(nearby,key=lambda f:abs(f-owner.radio_frequency.value()*1000))
        try:alias_frequency(rate,rf,owner.radio_bandwidth.currentData(),us)
        except ValueError:
            owner.radio_status.setText('Sintonía fuera de banda: el canal cruza DC o Nyquist.')
            return False
        owner.radio_frequency.setValue(rf/1000)
        return True

    def refresh_radio_overlay(self):
        """RF carriers and channel sidebands; never mix these with demodulated audio."""
        for plot, item in self.radio_overlay_items:
            plot.removeItem(item)
        self.radio_overlay_items.clear()
        if not self.radio_fft_view or self.mode != 1 or self._fft_kind() != 'Spectre':
            return
        owner = self.owner
        from monitor.v17.radio_tuning import rf_frequency
        us = owner.radio_us.isChecked()
        selected = owner.radio_frequency.value()*1000
        half_width = owner.radio_bandwidth.currentData()/2
        nyquist = owner.applied_configuration.actual_rate/2
        tolerance = max(1, nyquist/65536)
        frequencies = [(p['frequency'], False) for p in getattr(owner, 'radio_candidates', [])
                       if abs(p['frequency']-selected) > tolerance]
        frequencies.append((selected, True))
        logarithmic = self.log_frequency.isChecked()
        def position(value):
            return np.log10(max(value, 1)) if logarithmic else value
        for i, plot in enumerate(self.plots):
            if self.channels[i].currentText() != 'CH1':
                continue
            self.header_labels[i].setText('· FFT Radio · alias / CH1' if us else '· FFT Radio · RF / CH1')
            for frequency, tuned in frequencies:
                frequency=abs((frequency+nyquist)%(2*nyquist)-nyquist) if us else frequency
                if not 0 < frequency < nyquist:
                    continue
                color = (0, 229, 255) if tuned else (255, 255, 255)
                for low, high in ((frequency-half_width, frequency), (frequency, frequency+half_width)):
                    band = pg.LinearRegionItem((position(max(1, low)), position(min(nyquist, high))),
                        movable=False, brush=pg.mkBrush(*color, 22 if tuned else 10),
                        pen=pg.mkPen(None))
                    band.setZValue(-5)
                    plot.addItem(band, ignoreBounds=True)
                    self.radio_overlay_items.append((plot, band))
                line = pg.InfiniteLine(position(frequency), angle=90, movable=False,
                    pen=pg.mkPen(*color, 190 if tuned else 90, width=1.5 if tuned else 1))
                line.setZValue(5)
                plot.addItem(line, ignoreBounds=True)
                self.radio_overlay_items.append((plot, line))

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

    def capture_single(self, trigger_index):
        from types import SimpleNamespace
        from monitor.v17.history import SampleHistory
        n = int(self.size.currentText())
        channels = {control.currentText() for control in self.channels} - {'Ninguno'}
        if self.mode == 1 and self._fft_kind() == 'Transfer': channels = set(self.transfer_pair())
        if self.mode == 1 and not channels and self.owner.active_meas_channel in ('CH1','CH2','FILTER','RADIO'):
            channels = {self.owner.active_meas_channel}
        owner = self.owner
        audio_names = {'RADIO'}
        if self.owner.filter_source.currentText()=='RADIO':audio_names.add('FILTER')
        if channels & audio_names:
            stream = self.owner.radio_stream
            if channels-audio_names or stream is None:
                self.info.setText('SINGLE: seleccionar canales de la misma FS y activar RADIO.')
                return False
            owner = stream.analysis_owner(self.owner)
        total = len(owner.sample_numbers)
        first = max(0, trigger_index - n + 1)
        last = min(trigger_index, total - n)
        if last < first:
            return False
        candidates = sorted(set([first, last] + list(range(first, last + 1, max(1,n // 32)))))
        weights = WINDOWS[self.window.currentText()](n)
        def energy(start):
            score = 0.0
            for name in channels:
                history = owner.series.get(name)
                if history is not None and len(history) == total:
                    values = history.window(start, start + n)
                    if np.all(np.isfinite(values)):
                        score += float(np.sum(((values-values.mean())*weights)**2))
            return score
        start = max(candidates, key=energy)
        self.single_capture_start = start
        end = start + n
        histories = {}
        for name, history in owner.series.items():
            if len(history) == len(owner.sample_numbers):
                copy = SampleHistory(n)
                copy.extend(history.window(start, end))
                histories[name] = copy
        snapshot = SimpleNamespace(is_running=True, series=histories,
                                   sample_numbers=range(n), sample_counter=n,
                                   current_fs_hz=owner.current_fs_hz,
                                   channel_colors=self.owner.channel_colors,
                                   _reduce_trace_for_display=self.owner._reduce_trace_for_display)
        self.reset()
        self._single_snapshot = snapshot
        self.render(single_owner=snapshot)
        self._show_single_markers()
        valid = self.last_end is not None and (self.mode != 1 or any(item is not None for item in self.analysis_result or []))
        if not valid:
            self._single_snapshot = None; self.clear_single_marker()
        return valid

    @staticmethod
    def _metric(value, unit='', precision=3):
        if unit == 'Hz' and np.isfinite(value) and abs(value) >= 1000:
            value, unit = value / 1000, 'kHz'
        if np.isneginf(value) and unit == 'dB': return '−∞ dB (salida cero)'
        if np.isfinite(value) and unit == 'dB' and value > 120: return '>120 dB (numérico)'
        if np.isfinite(value) and unit == '%' and 0 <= value < 1e-8: return '<1e-8 % (numérico)'
        return ('N/A' if not np.isfinite(value) else number(value, f'.{precision}g') + (' '+unit if unit else ''))

    def close(self):
        if self._distortion_executor is not None:
            self._distortion_executor.shutdown(wait=False,cancel_futures=True)
            self._distortion_executor = None

    def _live_distortion(self, signals, fs, options, single):
        if single: return _fit_distortion_batch(signals,fs,options)
        future = self._distortion_future
        if future is not None and future.done():
            try: fitted = future.result()
            except (ValueError,np.linalg.LinAlgError): fitted = {}
            if self._distortion_job_generation == self._distortion_generation:
                self._distortion_cache = fitted
            self._distortion_future = None
        now = time.monotonic()
        if self._distortion_future is None and now-self._distortion_submitted >= .2:
            if self._distortion_executor is None:
                self._distortion_executor = ThreadPoolExecutor(max_workers=1,thread_name_prefix='fft-distortion')
            self._distortion_job_generation = self._distortion_generation
            self._distortion_submitted = now
            self._distortion_future = self._distortion_executor.submit(
                _fit_distortion_batch,{name:np.array(data[-options['n']:],copy=True) for name,data in signals.items()},fs,options)
        return self._distortion_cache

    def _render_fft_analysis(self, owner, fs, n, single=False, domains=None):
        kind = self._fft_kind()
        overlap = (0,.5,.75)[self.overlap.currentIndex()]
        maximum = 1 if single else int(self.averages.currentText())
        hop = max(1,round(n*(1-overlap)))
        count = min(len(owner.sample_numbers),n+(maximum-1)*hop)
        end = owner.sample_counter
        domain_key=tuple((name,id(source.series) if source is not None else None,rate)
                         for name,(source,rate) in sorted(domains.items())) if domains else ()
        if domains:
            end=tuple((name,source.sample_counter if source is not None else 0,identity,rate)
                      for (name,identity,rate) in domain_key for source in (domains[name][0],))
        if self.last_end == end and self.analysis_result is not None and kind not in ('Distort','Power'): return
        context = (n,self.window.currentText(),self.remove_dc.isChecked(),round(fs,1),kind,
            self.averages.currentText(),overlap,self.channels[0].currentText(),self.channels[1].currentText(),
            self.scale.currentIndex(),self.power_scale.currentIndex(),self.spectrum_view.currentIndex(),
            self.transfer_view.currentIndex(),self.transfer_pair(),self.band_low.value(),self.band_high.value(),
            self.signal_low.value(),self.signal_high.value(),self.fundamental.value(),self.harmonics.value(),self.log_frequency.isChecked(),self.lock_axes.isChecked(),domain_key)
        if context != self.context:
            self.reset(); self.context = context; self.configure_plots()
        times = owner.series.get('Tiempo (us)')
        if not domains and times is not None and len(times) >= count:
            dt = np.diff(times[-count:])
            gaps = np.flatnonzero((dt <= 0)|(np.abs(dt-1e6/fs)>max(1.1,1e6/fs*.25)))
            if len(gaps):
                gap_marker = end-count+int(gaps[-1])+1
                count -= int(gaps[-1])+1
                if count < n:
                    self.reset(); self.info.setText('Discontinuidad temporal: esperando bloques completos.'); return
                if getattr(self,'_analysis_gap_marker',None) != gap_marker:
                    self._power_fit_cache = {}; self.frames.clear()
                    self._distortion_generation += 1
                    self._distortion_cache = {}
                    self._distortion_submitted = -float('inf')
                    self._analysis_gap_marker = gap_marker
        kwargs = dict(n=n,window=self.window.currentText(),remove_dc=self.remove_dc.isChecked(),overlap=overlap,maximum=maximum)
        channels = tuple(c.currentText() for c in self.channels)
        selected = self.owner.active_meas_channel
        if kind != 'Transfer' and selected in ('CH1', 'CH2', 'FILTER', 'RADIO') and selected not in channels:
            channels += (selected,)
        value_cache={}
        analysis_cache={}
        rates={name:rate for name,(_,rate) in domains.items()} if domains else {}
        def values(name):
            if name not in value_cache:
                source,rate=domains.get(name,(None,fs)) if domains else (owner,fs)
                history = source.series.get(name) if source is not None else None
                needed=(min(len(source.sample_numbers),n+(maximum-1)*hop) if domains else count) if source is not None else 0
                data=history[-needed:] if history is not None and needed>=n and len(history)==len(source.sample_numbers) else None
                if domains and data is not None:
                    clock=source.series.get('Tiempo (us)')
                    if clock is not None and len(clock)==len(history):
                        delta=np.diff(clock[-needed:])
                        gaps=np.flatnonzero((delta<=0)|(np.abs(delta-1e6/rate)>max(1.1,1e6/rate*.25)))
                        if len(gaps):
                            marker=(id(clock),source.sample_counter-needed+int(gaps[-1])+1)
                            markers=getattr(self,'_mixed_gap_markers',{})
                            if markers.get(name)!=marker:
                                markers[name]=marker;self._mixed_gap_markers=markers
                                self._distortion_generation+=1;self._distortion_cache={}
                                self._distortion_submitted=-float('inf')
                            data=data[int(gaps[-1])+1:]
                    if len(data)<n:data=None
                value_cache[name]=data if data is not None and np.all(np.isfinite(data)) else None
            return value_cache[name]
        arrays = [None]*max(2,len(channels)); reports = []; results = []; extra = []; summaries = ['']*max(2,len(channels))
        self.statistics_by_channel = {}
        try:
            distortion_results = {}
            if kind in ('Distort','Power'):
                signals = {name:data for name in set(channels) if name != 'Ninguno' and (data := values(name)) is not None}
                options=dict(n=n,window=self.window.currentText(),low=self.band_low.value(),high=self.band_high.value())
                if kind == 'Distort':options.update(fundamental=self.fundamental.value(),harmonics=self.harmonics.value())
                distortion_results = self._live_distortion(signals,rates or fs,options,single)
            if kind == 'Transfer':
                reference,response=self.transfer_pair()
                x,y = values(reference),values(response)
                if x is None or y is None: raise ValueError('Transfer requiere referencia y respuesta alineadas')
                result = analysis.transfer(x,y,fs,**kwargs); results = [result]
                self.statistics_by_channel[self.transfer_label()] = result
                frequency = result['frequencies']; segments = result['segments']
                key = ('phase_deg','coherence','group_delay_s')[self.transfer_view.currentIndex()]
                arrays = [result['gain_db'],result[key]]
                peak = 1+int(np.argmax(result['pxx'][1:]))
                gain = result['gain_db'][peak]
                coh = result['coherence']; delay = result['group_delay_s']
                reports.append(self.transfer_label()+' · H1 · pico referencia '+self._metric(frequency[peak],'Hz')+'\nGanancia '+self._metric(gain,'dB')+' · coherencia '+self._metric(coh[peak]))
                reports.append('Retardo mediano (bins coherentes) '+self._metric(np.nanmedian(delay)*1e6 if np.any(np.isfinite(delay)) else np.nan,'µs'))
                if segments == 1: reports.append('Coherencia y retardo N/A: un segmento.')
                summaries = [reports[0],reports[1]+ (' · coherencia N/A (un segmento)' if segments==1 else '')]
                extra.append('Sin calibración Bode aplicada. Fase/retardo por tramos con soporte; retardo: coherencia ≥ 0,8 y cinco bins.')
            else:
                segments = 0; frequency = np.fft.rfftfreq(n,1/fs)
                for i,name in enumerate(channels):
                    channel_fs=rates.get(name,fs)
                    report_start = len(reports)
                    data = values(name) if name != 'Ninguno' else None
                    if data is None:
                        results.append(None); continue
                    if name not in analysis_cache:analysis_cache[name]=analysis.analyze(data,channel_fs,**kwargs)
                    result = analysis_cache[name]; results.append(result); segments = result.segments
                    self.statistics_by_channel[name] = result
                    if kind == 'Power':
                        arrays[i] = 10*np.log10(np.maximum(result.psd,1e-300)) if self.power_scale.currentIndex()==0 else result.psd
                        m = analysis.power_metrics(result,self.band_low.value(),self.band_high.value(),self.signal_low.value(),self.signal_high.value())
                        d = distortion_results.get(name,{'valid':False,'reason':'Calculando distorsión…'})
                        m['snr_db'] = d['snr_db'] if d['valid'] else np.nan
                        result.power_metrics = m
                        reports.append(name+' · banda '+self._metric(m['power'],'V²')+' · RMS '+self._metric(m['rms'],'V')+'\nPiso '+self._metric(m['noise_floor'],'V²/Hz')+' · SNR '+self._metric(m['snr_db'],'dB'))
                        bands = [(20,200),(200,2000),(2000,channel_fs/2)]
                        reports.append('Bandas fijas '+ ' · '.join(f'{int(low)}–{int(min(high,channel_fs/2))} Hz: '+self._metric(analysis.band_power(result,low,np.nextafter(min(high,channel_fs/2),-np.inf) if high<channel_fs/2 else channel_fs/2),'V²') for low,high in bands if low<channel_fs/2))
                        extra.append(name+' · S/(N+D) PSD: '+self._metric(m['snd_db'],'dB')+'; SNR: residual del ajuste tonal H1–H10; piso: media PSD fuera de cinco picos ±3 bins.')
                    elif kind == 'Distort':
                        arrays[i] = 20*np.log10(np.maximum(result.amplitude,1e-12)) if self.scale.currentIndex()==0 else result.amplitude
                        d = distortion_results.get(name,{'valid':False,'reason':'Calculando distorsión…'})
                        if d['valid']:
                            reports.append(name+' · f₀ '+self._metric(d['fundamental'],'Hz')+'\nTHD '+self._metric(d['thd']*100,'%')+' · THD+N '+self._metric(d['thdn']*100,'%')+'\nSINAD '+self._metric(d['sinad_db'],'dB')+' · SNR '+self._metric(d['snr_db'],'dB'))
                            summary = ' · '.join('H'+str(h['order'])+' '+self._metric(h['rms'],'V RMS') for h in d['harmonics'][:5])
                            if len(d['harmonics'])>5: summary += ' · … (detalle al pasar el cursor)'
                            reports.append(summary)
                            extra.append(name+' · '+'; '.join('H'+str(h['order'])+' '+self._metric(h['rms'],'V RMS')+' '+self._metric(h['dbc'],'dBc') for h in d['harmonics']))
                            extra.append(name+' · armónicos '+str(len(d['harmonics']))+'; banda '+str(self.band_low.value())+'–'+str(self.band_high.value() or fs/2)+' Hz. Residual incluye espurios y órdenes omitidos.')
                        else: reports.append(name+' · N/A: '+d['reason'])
                        result.distortion = d
                    else:
                        arrays[i] = result.phase if self.spectrum_view.currentIndex()==1 else (20*np.log10(np.maximum(result.amplitude,1e-12)) if self.scale.currentIndex()==0 else result.amplitude)
                        if result.peaks:
                            p = result.peaks[0]
                            reports.append(name+' · dominante '+self._metric(p['frequency'],'Hz')+' · '+self._metric(p['amplitude'],'V pico'))
                            reports.append('Picos '+ ' · '.join(self._metric(p['frequency'],'Hz') for p in result.peaks))
                        else: reports.append(name+' · sin pico no DC')
                        extra.append('Fase instantánea del último bloque respecto de su inicio, sin promedio de ángulos. Magnitud RMS de amplitudes pico entre segmentos; picos interpolados aproximados.')
                    summaries[i] = reports[report_start]
        except (ValueError,np.linalg.LinAlgError) as error:
            self.reset(); self.info.setText(str(error)); return
        self.analysis_result = results; self.fft_frequencies = frequency
        self.frames.append((end,arrays)); self.last_end = end
        detail = ' · ajuste del último bloque' if kind == 'Distort' else ''
        self.info.setText(f'Fs {number(fs, formats.n__0f)} Hz · Δf {number(fs/n, formats.n_2f)} Hz\n{kind} · {segments}/{maximum} segmentos reales · ventana {number(n/fs*1000, formats.n_1f)} ms'+detail)
        if domains:
            self.info.setText('\n'.join(f'{name} · Fs {number(rates[name],formats.n__0f)} Hz · Δf {number(rates[name]/n,formats.n_2f)} Hz'
                + (' · esperando muestras' if values(name) is None else '') for name in channels[:2] if name!='Ninguno'))
        self.metrics.setText('\n'.join(reports)); self.metrics.setToolTip('\n'.join(extra))
        self.refresh_measurement_panel()
        for label,summary in zip(self.summary_labels,summaries): label.setText(summary)
        panel_rates=[rates.get(name,fs) for name in channels[:2]] if domains else fs
        panel_frequencies=[result.frequencies if result is not None else np.fft.rfftfreq(n,1/panel_rates[i])
                           for i,result in enumerate(results[:2])] if domains else frequency
        self._draw_fft_arrays(owner,panel_rates,arrays[:2],panel_frequencies,kind)
        if kind == 'Distort': self._draw_harmonics(n)
        elif kind in ('Spectre','Power'): self._draw_spectral_annotations(kind,panel_rates)

    def _color_annotations(self, index, channel):
        color = pg.mkColor(self.owner.channel_colors.get(channel,'#00e5ff')).darker(115)
        self.harmonic_points[index].setSymbolBrush(pg.mkBrush(color))
        self.harmonic_points[index].setSymbolPen(pg.mkPen('#171c24',width=.8))
        for label in self.harmonic_labels[index]: label.setColor(color)
        self.power_annotations[index][2].setColor(color)

    def _draw_spectral_annotations(self, kind, fs):
        log = self.log_frequency.isChecked()
        for i,control in enumerate(self.channels):
            panel_fs=fs[i] if isinstance(fs,list) else fs
            self._color_annotations(i,control.currentText())
            result = self.statistics_by_channel.get(control.currentText())
            label = self.harmonic_labels[i][0]
            label.hide();self.harmonic_points[i].setData([],[])
            band,floor,caption = self.power_annotations[i]
            for item in (band,floor,caption): item.hide()
            if result is None: continue
            view = self.plots[i].getViewBox()
            xr,yr = view.viewRange()
            if kind == 'Spectre':
                if not result.peaks: continue
                peak = result.peaks[0]
                frequency = peak['frequency']
                y = (result.phase[peak['bin']] if self.spectrum_view.currentIndex()==1 else
                     20*np.log10(max(peak['amplitude'],1e-12)) if self.scale.currentIndex()==0 else peak['amplitude'])
                self.harmonic_points[i].setData([frequency],[y])
                label.setText('f pico · '+self._metric(frequency,'Hz'))
                x = np.log10(frequency) if log else frequency
                bounds = label.boundingRect()
                x = min(max(x,xr[0]),xr[1]-bounds.width()*(xr[1]-xr[0])/max(view.width(),1))
                height = bounds.height()*(yr[1]-yr[0])/max(view.height(),1)
                label.setPos(x,min(max(y,yr[0]+height),yr[1]));label.show()
            else:
                metrics = result.power_metrics
                low = max(self.band_low.value(),result.df if log else 0)
                high = min(self.band_high.value() or panel_fs/2,panel_fs/2)
                if high > low:
                    self._syncing_power_band = True
                    try:
                        band.setBounds((np.log10(result.df),np.log10(panel_fs/2)) if log else (0,panel_fs/2))
                        band.setRegion((np.log10(low),np.log10(high)) if log else (low,high))
                    finally: self._syncing_power_band = False
                    band.show()
                noise = metrics['noise_floor']
                if np.isfinite(noise) and noise > 0:
                    floor.setValue(10*np.log10(noise) if self.power_scale.currentIndex()==0 else noise);floor.show()
                caption.setText('Banda · '+self._metric(metrics['rms'],'V RMS'))
                caption.setToolTip('La línea discontinua indica el piso medio de ruido de la banda, excluyendo los picos.')
                caption.setPos(xr[1],yr[1]);caption.show()

    def _draw_harmonics(self, n):
        log = self.log_frequency.isChecked()
        for i, control in enumerate(self.channels):
            self._color_annotations(i,control.currentText())
            labels = self.harmonic_labels[i]
            for label in labels: label.hide()
            result = self.statistics_by_channel.get(control.currentText())
            fit = getattr(result,'distortion',None)
            points = self.harmonic_points[i]
            if fit is None or not fit['valid']:
                points.setData([],[]);continue
            threshold = max(fit['fundamental_power']*1e-12,25*fit['noise_power']/n)
            harmonics = [h for h in fit['harmonics'] if h['order']==1 or h['power'] > threshold]
            frequencies = [h['frequency'] for h in harmonics]
            peaks = [h['rms']*np.sqrt(2) for h in harmonics]
            levels = [20*np.log10(max(v,1e-12)) if self.scale.currentIndex()==0 else v for v in peaks]
            points.setData(frequencies,levels)
            points.setToolTip('Amplitudes del ajuste sinusoidal; dBc respecto de la fundamental.\n'+
                '\n'.join(('f₀' if h['order']==1 else 'H'+str(h['order']))+' · '+self._metric(h['frequency'],'Hz')+' · '+self._metric(h['dbc'],'dBc') for h in harmonics))
            view = self.plots[i].getViewBox()
            limits = view.viewRange()[0]; span = max(limits[1]-limits[0],1e-12)
            ylimits = view.viewRange()[1]
            yspan = max(ylimits[1]-ylimits[0],1e-12)
            occupied = []
            for label,h,y in zip(labels,harmonics,levels):
                x = np.log10(h['frequency']) if log else h['frequency']
                pixel = (x-limits[0])/span*view.width()
                caption = 'f₀ · 0 dBc' if h['order']==1 else 'H'+str(h['order'])+' · '+self._metric(h['dbc'],'dBc')
                label.setText(caption);label.setToolTip(points.toolTip())
                bounds = label.boundingRect()
                ypixel = (ylimits[1]-y)/yspan*view.height()
                pixel = max(0,min(pixel,max(0,view.width()-bounds.width()-6)))
                for offset in (max(0,bounds.height()-ypixel),bounds.height()+6):
                    rectangle = QtCore.QRectF(pixel,ypixel+offset-bounds.height(),bounds.width()+6,bounds.height()+4)
                    if rectangle.top() < -1e-6 or rectangle.bottom() > view.height(): continue
                    if any(rectangle.intersects(other) for other in occupied): continue
                    occupied.append(rectangle)
                    label.setPos(limits[0]+pixel*span/max(view.width(),1),y-offset*yspan/max(view.height(),1))
                    label.show();break

    def _fft_style(self,index,color):
        cache=getattr(self,'_fft_style_cache',{})
        cached=cache.get(index)
        if cached is None or cached[0]!=color:
            brush=pg.mkColor(color);brush.setAlpha(38)
            cached=(color,pg.mkPen(color,width=1),pg.mkBrush(brush))
            cache[index]=cached;self._fft_style_cache=cache
        if self.curves[index].opts.get('pen')!=cached[1]:self.curves[index].setPen(cached[1])
        return cached[2]

    def _redraw_fft_trace(self,index):
        cached=getattr(self,'_fft_trace_cache',{}).get(index)
        if cached is None or self.mode!=1 or getattr(self,'_redrawing_fft',False):return
        self._redrawing_fft=True
        try:
            owner,frequency,values,options=cached
            log=self.log_frequency.isChecked()
            x=frequency[1:] if log else frequency
            y=values[1:] if log else values
            axis_x=np.log10(x) if log else x
            view=self.plots[index].getViewBox()
            low,high=view.viewRange()[0]
            # Keep one neighbour at either edge for continuous lines/fills.
            left=max(0,int(np.searchsorted(axis_x,low,'left'))-1)
            right=min(len(x),int(np.searchsorted(axis_x,high,'right'))+1)
            visible_x,visible_y=axis_x[left:right],y[left:right]
            width=max(32,int(view.width()/2))
            reduced_x,reduced_y=owner._reduce_trace_for_display(visible_x,visible_y,low,high,width)
            self.curves[index].setData(10**reduced_x if log else reduced_x,reduced_y,**options)
        finally:self._redrawing_fft=False

    def _draw_fft_arrays(self,owner,fs,arrays,frequency,kind):
        log = self.log_frequency.isChecked()
        share = self.lock_axes.isChecked() and kind != 'Transfer'
        selected = [a[1:] if log else a for a in arrays if a is not None]
        shared = self.stable_range('shared',selected) if share and selected else None
        for i,values in enumerate(arrays):
            panel_frequency=frequency[i] if isinstance(frequency,list) else frequency
            panel_fs=fs[i] if isinstance(fs,list) else fs
            if values is None:
                getattr(self,'_fft_trace_cache',{}).pop(i,None)
                self.curves[i].setData([],[]); continue
            channel = self.transfer_pair()[i] if kind=='Transfer' else self.channels[i].currentText()
            color = owner.channel_colors.get(channel,'#00e5ff')
            brush=self._fft_style(i,color)
            yrange = shared or self.stable_range(i,[values[1:] if log else values])
            fill = kind in ('Spectre','Distort') and not (kind=='Spectre' and self.spectrum_view.currentIndex()==1)
            if not hasattr(self,'_fft_trace_cache'):self._fft_trace_cache={}
            self._fft_trace_cache[i]=(owner,panel_frequency,values,dict(connect='finite',
                fillLevel=(yrange[0] if self.scale.currentIndex()==0 else 0) if fill and yrange else None,fillBrush=brush))
            if yrange:self._set_view_range(i,'y',*yrange)
            if kind=='Transfer' and i==1 and self.transfer_view.currentIndex()==1:self._set_view_range(i,'y',0,1,padding=.02)
            self._set_view_range(i,'x',np.log10(panel_fs/(2*(len(panel_frequency)-1))) if log else 0,np.log10(panel_fs/2) if log else panel_fs/2)
            self._redraw_fft_trace(i)

    def _sync_available_channels(self):
        single=getattr(self.owner,'applied_configuration',None) is not None and self.owner.applied_configuration.channels==1
        for control in (*self.channels,self.transfer_reference,self.transfer_response):
            index=control.findText('CH2')
            if index>=0:
                control.model().item(index).setEnabled(not single)
                if single and control.currentText()=='CH2':
                    control.setCurrentText('Ninguno' if control in self.channels else 'FILTER' if control is self.transfer_response else 'CH1')

    def render(self, single_owner=None):
        self._sync_available_channels()
        if self.mode == 3:
            self.bode.tick()
            return
        if self.mode == 0 or (single_owner is None and not self.owner.is_running):
            return
        if single_owner is None and int(self.size.currentText())>=16384:
            worker=getattr(self.owner,'serial_worker',None)
            if worker is not None and getattr(worker,'pending_batches',0)>1:
                # Coalesce visual analysis only. The bounded DSP/GUI queue
                # keeps every acquired batch; explicit SINGLE still renders.
                self.deferred_live_timer_calls+=1
                return
        if single_owner is None: self._single_snapshot = None
        owner = single_owner or self.owner
        domains=None
        if single_owner is None:
            selected = self.transfer_pair() if self.mode==1 and self._fft_kind()=='Transfer' else tuple(c.currentText() for c in self.channels)
            audio_names = {'RADIO'}
            if self.owner.filter_source.currentText()=='RADIO':audio_names.add('FILTER')
            chosen = set(selected)-{'Ninguno'}
            if chosen & audio_names:
                if chosen-audio_names:
                    if self.mode!=1 or self._fft_kind()=='Transfer':
                        self.reset();self.info.setText('Seleccionar canales de la misma FS para Transfer o Heatmap.');return
                    stream=getattr(self.owner,'radio_stream',None)
                    audio_owner=stream.analysis_owner(self.owner) if stream is not None else None
                    domains={name:(audio_owner,stream.rate if stream is not None else 40000)
                        if name in audio_names else (self.owner,self.owner.applied_configuration.actual_rate)
                        for name in ('CH1','CH2','FILTER','RADIO')}
                stream=getattr(self.owner,'radio_stream',None)
                if stream is None and not domains:
                    self.reset();self.info.setText('RADIO sin muestras de audio.');return
                if not domains:owner=stream.analysis_owner(self.owner)
        # Bound painting separately: FFT 30 Hz, heavier heatmap 20 Hz.
        # Advance the scheduled phase rather than rounding every update up
        # to the next 16-ms timer tick (which turns 20 Hz into ~15.6 Hz).
        if single_owner is None:
            now = time.monotonic()
            interval = 1/30 if self.mode == 1 else .05
            if (int(self.size.currentText())>=16384 and
                    getattr(self.owner,'serial_worker',None) is not None):
                # Large transforms plus Qt painting can occupy a full batch
                # interval. Keep live updates at 10 Hz; SINGLE and the full
                # FFT resolution remain unchanged.
                interval=max(interval,.1)
            elapsed = now-self.last_fast_render
            if elapsed < interval:
                return
            self.last_fast_render = now if elapsed >= 2*interval else self.last_fast_render+interval
        n = int(self.size.currentText())
        if len(owner.sample_numbers) < n and not domains:
            self.info.setText(f'Esperando {number(n, formats.n_)} muestras…'); return
        timestamps = owner.series.get('Tiempo (us)') if not domains else None
        if timestamps is not None and len(timestamps) >= n:
            dt = np.diff(timestamps[-n:])
            nominal = np.median(dt)
            if nominal <= 0 or np.any(dt <= 0) or np.any(np.abs(dt - nominal) > max(1.1, nominal * .25)):
                self.reset(); self.info.setText('Discontinuidad temporal: esperando un bloque completo.'); return
            fs = 1e6 / np.mean(dt)
        else:
            fs = domains['CH1'][1] if domains else owner.current_fs_hz
        if fs <= 0:
            self.info.setText('Esperando frecuencia de adquisición…'); return
        if self.mode == 1:
            if domains:self._render_fft_analysis(owner,fs,n,single_owner is not None,domains=domains)
            else:self._render_fft_analysis(owner,fs,n,single_owner is not None)
            return
        channels = tuple(c.currentText() for c in self.channels)
        context = (n, self.window.currentText(), channels, round(fs, 1), self.mode,
                   self.remove_dc.isChecked(), self.scale.currentText(), self.seconds.value(), self.overlap.currentIndex(), self.log_frequency.isChecked(), self.lock_axes.isChecked())
        if context != self.context:
            self.reset(); self.context = context; self.configure_plots()
            self.fft_weights = WINDOWS[self.window.currentText()](n)
            self.fft_frequencies = np.fft.rfftfreq(n, 1/fs)
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
            # Panels can share an immutable spectrum for this block only.
            by_channel = {}
            start = block_end - oldest - n
            valid_time = True
            if timestamps is not None and len(timestamps) >= start + n:
                differences = np.diff(timestamps.window(start, start + n))
                valid_time = bool(np.all(differences > 0) and
                    np.all(np.abs(differences - 1e6/fs) <= max(1.1, 1e6/fs * .25)))
            for channel in channels:
                if channel in by_channel:
                    spectra.append(by_channel[channel]); continue
                history = owner.series.get(channel)
                if channel == 'Ninguno' or history is None or len(history) != len(owner.sample_numbers) or not valid_time:
                    spectra.append(None); continue
                start = block_end - oldest - n
                values = history.window(start, start + n)
                if not np.all(np.isfinite(values)):
                    spectra.append(None); continue
                amplitudes = _amplitudes(values, self.fft_weights, self.remove_dc.isChecked())
                by_channel[channel] = (20 * np.log10(np.maximum(amplitudes, 1e-12))
                                       if self.scale.currentIndex() == 0 else amplitudes)
                spectra.append(by_channel[channel])
            self.frames.append((block_end, spectra)); self.last_end = block_end
        if not self.frames: return
        self.info.setText(f'Fs {number(fs, formats.n__0f)} Hz · Δf {number(fs/n, formats.n_2f)} Hz\nVentana {number(n/fs*1000, formats.n_1f)} ms · paso {number(hop/fs*1000, formats.n_1f)} ms')
        latest_values = self.frames[-1][1]
        shared_range = None
        if self.mode == 1 and self.lock_axes.isChecked():
            selected = [a[1:] if self.log_frequency.isChecked() else a for a in latest_values if a is not None]
            if selected: shared_range = self.stable_range('shared', selected)
        for i, channel in enumerate(channels):
            if channel == 'Ninguno':
                if self.images[i].image is not None: self.images[i].clear()
                continue
            values = latest_values[i]
            if values is None:
                self.curves[i].setData([], [])
                self.fft_fills[i].setData([], [])
                if self.mode == 1: continue
            color = owner.channel_colors.get(channel, '#00e5ff')
            self.curves[i].setPen(pg.mkPen(color, width=1))
            if self.mode == 1:
                frequencies = self.fft_frequencies
                log = self.log_frequency.isChecked()
                display_x = frequencies[1:] if log else frequencies
                display_y = values[1:] if log else values
                # Keep the complete analysis; draw an extrema envelope at screen
                # resolution, preserving narrow spectral peaks and finite gaps.
                axis_x = np.log10(display_x) if log else display_x
                width = max(32, int(self.plots[i].getViewBox().width()/2))
                reduced_x, display_y = owner._reduce_trace_for_display(
                    axis_x, display_y, axis_x[0], axis_x[-1], width)
                display_x = 10**reduced_x if log else reduced_x
                yrange = shared_range or self.stable_range(i, [values[1:] if log else values])
                if yrange is not None:
                    fill = pg.mkColor(color); fill.setAlpha(38)
                    baseline = yrange[0] if self.scale.currentIndex() == 0 else 0
                    # Reuse the same path for line and shading; no second
                    # PlotDataItem or explicit polygon array for each FFT.
                    self.curves[i].setData(display_x, display_y, fillLevel=baseline,
                                           fillBrush=pg.mkBrush(fill), connect='finite')
                else:
                    self.curves[i].setData(display_x, display_y, fillLevel=None, connect='finite')
                if yrange is not None:self._set_view_range(i,'y',*yrange)
                self._set_view_range(i,'x',np.log10(fs/n) if log else 0,
                                       np.log10(fs/2) if log else fs/2)
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
                self._set_view_range(i,'x',-count*hop/fs,0)
                self._set_view_range(i,'y',np.log10(fs/n) if log else 0,np.log10(fs/2) if log else fs/2)
