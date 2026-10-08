"""Two-channel transient transfer measurement, independent from stepped tones."""
import time
from collections import deque
from dataclasses import replace
import numpy as np
from PyQt6 import QtWidgets, QtCore
from monitor.number_format import number, formats
from monitor.v13.bode import BodeSweep
from monitor.v13.receiver.unoq_generator import GeneratorConfig
from monitor.v13.receiver.unoq_switch import Phase


def transient_spectra(data, rate, onset, *, tail_samples=None):
    """Same rectangular acquisition window for both channels; preserve spectral gaps."""
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[1] != 3 or not np.all(np.isfinite(data)) or onset < 16:
        raise ValueError('Captura o referencia previa inválida')
    if np.any(np.abs(np.diff(data[:,0])-1/rate)>max(1.1e-6,.25/rate)):
        raise ValueError('Discontinuidad de adquisición')
    # The two ADC channels can see the edge in adjacent sample pairs.
    # Keep that edge out of the baseline statistics, but retain it in the FFT.
    baseline_end = max(16, onset - max(2, round(rate*.001)))
    signals = data[:,1:] - np.mean(data[:baseline_end,1:],axis=0)
    noise = np.std(signals[:baseline_end],axis=0)
    tail_length = max(16,len(signals)//10)
    if tail_samples is not None:
        # Long sweeps must not include the still-active stimulus in this check.
        # The configured tail contains the circuit's decay, not just silence.
        # Check its final fifth for settling, retaining the whole tail in FFT.
        tail_length = min(tail_length, max(16, round(int(tail_samples)*.2)))
    tail = signals[-tail_length:]
    peak = np.max(np.abs(signals),axis=0)
    if np.any(np.sqrt(np.mean(tail**2,axis=0)) > np.maximum(6*noise, .02*peak)):
        raise ValueError('La respuesta no terminó: aumentar Captura')
    spectra = np.fft.rfft(signals,axis=0)
    return spectra, noise, len(data)


def pulse_transfer(data, rate, onset, start=20., end=5000., *, tail_samples=None):
    spectra, noise, length = transient_spectra(data,rate,onset,tail_samples=tail_samples)
    freq = np.fft.rfftfreq(length,1/rate)
    amplitudes = np.abs(spectra)
    band = (freq>=start)&(freq<=min(end,.45*rate))
    if not np.any(band):raise ValueError('Captura demasiado corta para el rango elegido')
    floor = np.maximum(6*noise*np.sqrt(length), np.max(amplitudes[band],axis=0)*.01)
    valid = band & (amplitudes[:,0]>floor[0])
    if np.count_nonzero(valid)<3:raise ValueError('Referencia insuficiente para medir transferencia')
    gain = np.full(len(freq),np.nan); phase=gain.copy()
    ratio=spectra[valid,1]/spectra[valid,0]
    with np.errstate(divide='ignore'):
        gain[valid]=20*np.log10(np.abs(ratio))
    phase_valid = valid & (amplitudes[:,1]>6*noise[1]*np.sqrt(length)) & (amplitudes[:,1]>0)
    phase[phase_valid]=np.angle(spectra[phase_valid,1]/spectra[phase_valid,0],deg=True)
    return np.column_stack((freq[band],gain[band],phase[band]))


class PulseAverage:
    """H1 transfer estimator; accumulate spectra, not dB or wrapped phases."""
    def __init__(self, rate, capture, start=20., end=5000.):
        self.rate=rate;self.start=start;self.end=end
        self.pre=max(16,round(rate*.05));self.post=round(rate*capture)
        self.count=0;self.xx=None;self.yy=None;self.yx=None;self.noise_power=np.zeros(2)

    def add(self, data, onset):
        data=np.asarray(data,dtype=float)
        if onset<self.pre or len(data)-onset<self.post:
            raise ValueError('Captura insuficiente para promediar pulsos')
        # Equal lengths and the same edge-relative window for every shot.
        block=data[onset-self.pre:onset+self.post]
        spectra,noise,length=transient_spectra(block,self.rate,self.pre,tail_samples=self.post)
        x,y=spectra[:,0],spectra[:,1]
        if self.count==0:
            self.xx=np.zeros(len(x));self.yy=np.zeros(len(x));self.yx=np.zeros(len(x),dtype=complex)
            self.length=length
        self.xx+=abs(x)**2;self.yy+=abs(y)**2;self.yx+=y*np.conj(x)
        self.noise_power+=noise**2;self.count+=1

    def result(self):
        if not self.count:raise ValueError('Sin pulsos capturados')
        freq=np.fft.rfftfreq(self.length,1/self.rate)
        band=(freq>=self.start)&(freq<=min(self.end,.45*self.rate))
        if not band.any():raise ValueError('Captura demasiado corta para el rango elegido')
        input_amplitude=np.sqrt(self.xx/self.count)
        noise=np.sqrt(self.noise_power/self.count)
        floor=max(6*noise[0]*np.sqrt(self.length),input_amplitude[band].max()*.01)
        valid=band&(input_amplitude>floor)
        if valid.sum()<3:raise ValueError('Referencia insuficiente para medir transferencia')
        gain=np.full(len(freq),np.nan);phase=gain.copy()
        h=self.yx[valid]/self.xx[valid]
        with np.errstate(divide='ignore'):
            gain[valid]=20*np.log10(abs(h))
        coherence=np.zeros(len(freq));power=self.xx*self.yy
        np.divide(abs(self.yx)**2,power,out=coherence,where=power>0)
        coherence=np.clip(coherence,0,1)
        output_amplitude=np.sqrt(self.yy/self.count)
        phase_valid=valid&(output_amplitude>6*noise[1]*np.sqrt(self.length/self.count))
        if self.count>1:phase_valid &= coherence>=.8
        phase[phase_valid]=np.angle(self.yx[phase_valid]/self.xx[phase_valid],deg=True)
        self.coherence=coherence[band]
        return np.column_stack((freq[band],gain[band],phase[band]))


class BodePulse(BodeSweep):
    def __init__(self,spectral,form):
        super().__init__(spectral,form)
        for control in (self.points,self.settle,self.cycles):
            label=form.labelForField(control)
            if label:label.hide()
            control.hide()
        self.estimate.hide()
        self.width=QtWidgets.QSpinBox();self.width.setRange(100,65535);self.width.setValue(100)
        self.width.setSuffix(' µs');self.width.setSingleStep(100)
        self.capture=QtWidgets.QDoubleSpinBox();self.capture.setRange(.05,5);self.capture.setDecimals(2)
        self.capture.setValue(.5);self.capture.setSuffix(' s')
        self.averages=QtWidgets.QSpinBox();self.averages.setRange(1,64);self.averages.setValue(8)
        self.averages.setToolTip('Cantidad de pulsos. Promedio H1 de espectros cruzados; más pulsos reducen ruido aleatorio, no el desfase instrumental.')
        self.width.setToolTip('Ancho del estímulo; 100 µs requiere firmware con capacidad de pulso por hardware.')
        self.capture.setToolTip('Tiempo después del flanco: debe incluir toda la respuesta del circuito.')
        form.insertRow(2,'Ancho',self.width);form.insertRow(3,'Captura',self.capture)
        self.end.setValue(5000)
        self.button.setText('Repetir')
        self.status.setText('A2 entrada · A3 salida\nPromedio H1 de espectros cruzados.')
        self.stage='idle'

    def stimulus_config(self, stimulus):
        width=self.width.value();o=self.owner
        return GeneratorConfig(wave=4,enabled=1,low=stimulus.low,high=stimulus.high,
                               duration=width if o._pulse_us_capable else width//1000,
                               duration_us=int(o._pulse_us_capable))

    def capture_seconds(self):return self.capture.value()

    def begin(self,add=False):
        if self.active:return
        o=self.owner
        if o.serial_worker is None or not o.is_running:
            self.status.setText('Conectar el Q y activar RUN.');return
        if o._wav_active or o._wav_preparing:
            self.status.setText('Detener la reproducción Wav antes de medir Bode.');return
        if o._auto_apply_timer.isActive() or not o.config_rate_combo.isEnabled() or o._generator_requested is not None or not o._generator_state_known:
            self.status.setText('Esperar confirmación del Q.');return
        for control in (self.width,self.capture,self.start,self.end,self.averages):control.interpretText()
        width=self.width.value();fs=o.applied_configuration.rate
        if not getattr(self, "sweep_method", False) and not o._pulse_us_capable and width%1000:
            self.status.setText('Este ancho requiere el firmware de pulsos µs; con el anterior usar múltiplos de 1000 µs.');return
        if not 0<self.start.value()<self.end.value()<.45*fs:
            self.status.setText('Elegir inicio < final < 0,45 Fs.');return
        if not getattr(self, "sweep_method", False) and self.capture.value()<width/1e6*2:
            self.status.setText('Captura debe superar dos veces el ancho del pulso.');return
        if add and self.result and len(self.history)>=4:
            self.status.setText('Máximo de cinco curvas.');return
        try:stimulus=o._generator_config()
        except ValueError as exc:self.status.setText(str(exc));return
        if stimulus.high-stimulus.low<10:
            self.status.setText('Elegir una amplitud mayor.');return
        if add and self.result:
            self.history.append(list(self.result));self.history_profiles.append(self.result_profile)
            self.history_instruments.append(self.result_instrument);self.history_methods.append(self.result_method)
        elif not add:
            self.history.clear();self.history_profiles.clear();self.history_instruments.clear();self.history_methods.clear()
        self.previous=None  # Transient measurement ends with output disabled.
        self.result=[];self.result_profile=o.applied_configuration
        self.result_instrument=self.spectral.bode.instrument
        self.result_method=('chirp' if self.method.currentIndex()==1 else 'sweep') if getattr(self,'sweep_method',False) else 'pulse_h1'
        self.target_pulses=1 if getattr(self,'sweep_method',False) else self.averages.value()
        self.pulse_average=PulseAverage(fs,self.capture.value(),self.start.value(),self.end.value())
        self.pulse_config=self.stimulus_config(stimulus)
        self.config=GeneratorConfig(wave=1,enabled=1,low=stimulus.low,high=stimulus.low)
        self.active=True;self.stage='baseline';self.buffer=[];self.baseline=deque(maxlen=round(fs*.05));self.onset=None
        self.last_timestamp=None;self.baseline_anchor=None;self.waiting=True
        self.add_button.setEnabled(False);self.button.setText('Cancelar');self.deadline=time.monotonic()+10
        controls=o._generator_controls+[o.generator_frequency_dial,o.config_bits_combo,o.config_rate_combo,
                  o.destination_combo,o.single_btn,self.start,self.end,self.width,self.capture,self.averages,self.spectral.bode.tabs]
        if getattr(self,'sweep_method',False):
            controls.extend((self.method,self.duration))
        self.locked=[(c,c.isEnabled()) for c in controls]
        for c,_ in self.locked:c.setEnabled(False)
        o.single_shot_armed=False;o._generator_timer.stop();o._generator_dirty=False
        self.spectral.reset();self.spectral.configure_plots();self.draw()
        o._generator_requested=self.config
        try:o.serial_worker.request_generator(self.config)
        except Exception as exc:self.cancel(str(exc));return
        self.status.setText('Preparando nivel previo…')

    def confirmed(self,reply):
        if not self.active or not self.waiting or reply.active!=self.config and reply.phase!=Phase.REJECTED:return
        if reply.phase==Phase.REJECTED:self.cancel('Q rechazó el estímulo');return
        if reply.phase==Phase.APPLIED:
            self.waiting=False
            self.deadline=time.monotonic()+self.capture_seconds()+10

    def batch(self,batch):
        if not self.active:return
        fs=self.result_profile.rate
        for sample in batch:
            t=sample['Tiempo (us)']*1e-6
            if self.last_timestamp is not None and abs(t-self.last_timestamp-1/fs)>max(1.1e-6,.25/fs):
                self.cancel('Discontinuidad de adquisición');return
            self.last_timestamp=t
            row=(t,sample['V_IN'],sample['V_OUT'])
            if self.stage=='baseline':
                if self.waiting:continue
                if self.baseline_anchor is None:self.baseline_anchor=t
                self.baseline.append(row)
                if t-self.baseline_anchor>=.3:
                    self.buffer=list(self.baseline);self.stage='capture';self.config=self.pulse_config
                    self.waiting=True;self.owner._generator_requested=self.config
                    try:self.owner.serial_worker.request_generator(self.config)
                    except Exception as exc:self.cancel(str(exc));return
                    self.status.setText('Estímulo enviado · capturando entrada y salida…' if getattr(self,'sweep_method',False)
                                        else f'Pulso {self.pulse_average.count+1}/{self.target_pulses} · capturando…')
                continue
            self.buffer.append(row)
            if self.onset is None:
                baseline=self.config.low*3.3/4095;amplitude=(self.config.high-self.config.low)*3.3/4095
                if row[1]>baseline+.25*amplitude:self.onset=len(self.buffer)-1
            if self.onset is not None and len(self.buffer)-self.onset>=round(fs*self.capture_seconds()) and not self.waiting:
                try:
                    if getattr(self,'sweep_method',False):
                        data=pulse_transfer(self.buffer,fs,self.onset,self.start.value(),self.end.value(),
                                            tail_samples=round(fs*self.capture.value()))
                    else:
                        self.pulse_average.add(self.buffer,self.onset)
                        if self.pulse_average.count<self.target_pulses:
                            self.next_pulse()
                            return
                        data=self.pulse_average.result()
                    self.result=data.tolist();self.draw()
                    self.cancel('Captura completa' if getattr(self,'sweep_method',False)
                                else f'Promedio completo · {self.pulse_average.count} '+('pulso' if self.pulse_average.count==1 else 'pulsos'))
                    self.coverage.setToolTip('Salida atenuada: se conserva la ganancia estimada. Bajo el ruido, la fase se omite y la ganancia puede estar limitada por el ruido. Sin referencia de entrada no se calcula transferencia.')
                except ValueError as exc:
                    text=str(exc)
                    if getattr(self,'sweep_method',False):text=text.replace('aumentar Captura','aumentar Cola')
                    self.cancel(text)
                return
            if len(self.buffer)>round(fs*(self.capture_seconds()+2)):
                self.cancel('No se detectó el estímulo en A2');return

    def next_pulse(self):
        fs=self.result_profile.rate
        self.config=GeneratorConfig(wave=1,enabled=1,low=self.pulse_config.low,high=self.pulse_config.low)
        self.stage='baseline';self.buffer=[];self.baseline=deque(maxlen=round(fs*.05));self.onset=None
        # Remaining samples in the completed batch are deliberately discarded.
        self.last_timestamp=None;self.baseline_anchor=None;self.waiting=True
        self.deadline=time.monotonic()+10;self.owner._generator_requested=self.config
        try:self.owner.serial_worker.request_generator(self.config)
        except Exception as exc:self.cancel(str(exc));return
        self.status.setText(f'Pulso {self.pulse_average.count+1}/{self.target_pulses} · preparando…')

    def cancel(self,text='Cancelado',restore=True):
        was_active=self.active
        super().cancel(text,restore=False)
        self.button.setText('Repetir');self.stage='idle'
        if was_active and restore and self.owner.serial_worker is not None:
            config=replace(self.pulse_config, enabled=0)
            self.owner._generator_requested=config
            try:self.owner.serial_worker.request_generator(config)
            except Exception as exc:self.status.setText(text+f' · No se confirmó apagado: {exc}')


class BodeChirp(BodePulse):
    def __init__(self,spectral,form):
        super().__init__(spectral,form)
        self.sweep_method=True
        form.labelForField(self.width).hide();self.width.hide()
        self.method=QtWidgets.QComboBox();self.method.addItems(['Sweep','Chirp']);self.method.setCurrentIndex(1)
        self.method.currentIndexChanged.connect(lambda: self.spectral.bode.refresh_reference() if hasattr(self.spectral,'bode') else None)
        self.duration=QtWidgets.QDoubleSpinBox();self.duration.setRange(.01,10)
        self.duration.setDecimals(2);self.duration.setValue(2);self.duration.setSuffix(' s')
        form.insertRow(2,'Método',self.method);form.insertRow(3,'Barrido',self.duration)
        form.labelForField(self.capture).setText('Cola')
        self.capture.setToolTip('Captura adicional después del barrido para incluir la respuesta completa.')
        self.status.setText('Seno barrido · FFT(V_OUT) / FFT(V_IN)\nCaptura conjunta y cola de respuesta.')

    def stimulus_config(self,stimulus):
        return GeneratorConfig(wave=1,enabled=1,mode=self.method.currentIndex()+1,
                               frequency=round(self.start.value()*1000),final_frequency=round(self.end.value()*1000),
                               low=stimulus.low,high=stimulus.high,duration=round(self.duration.value()*1000))

    def capture_seconds(self):return self.duration.value()+self.capture.value()

    def begin(self,add=False):
        self.duration.interpretText()
        super().begin(add)


class BodeStack(QtWidgets.QStackedWidget):
    """Only the selected method determines the panel's required height."""
    def __init__(self):
        super().__init__()
        self.layout().setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetNoConstraint)
        self.currentChanged.connect(lambda _: self.updateGeometry())

    def sizeHint(self):
        widget=self.currentWidget()
        return widget.sizeHint() if widget is not None else super().sizeHint()

    def minimumSizeHint(self):
        widget=self.currentWidget()
        return widget.minimumSizeHint() if widget is not None else super().minimumSizeHint()

    def event(self,event):
        result=super().event(event)
        if event.type()==QtCore.QEvent.Type.LayoutRequest:self.updateGeometry()
        return result


class BodePanels:
    """Route existing Bode hooks to three independent control/result panels."""
    def __init__(self,spectral,form):
        self.spectral=spectral;self.tabs=BodeStack();self.panels=[];self.instrument=None
        for title,cls in (('Tonos',BodeSweep),('Pulso',BodePulse),('Sweep/Chirp',BodeChirp)):
            widget=QtWidgets.QWidget();layout=QtWidgets.QFormLayout(widget)
            layout.setContentsMargins(8,10,8,8)
            layout.setVerticalSpacing(7);layout.setHorizontalSpacing(10)
            layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            panel=cls(spectral,layout)
            self.organize(panel,layout)
            self.panels.append(panel);self.tabs.addWidget(widget)
        form.addRow(self.tabs);self.tabs.currentChanged.connect(self.changed)
        self.changed(0)

    def set_instrument(self, instrument):
        self.instrument=instrument
        self.refresh_reference()

    def refresh_reference(self):
        from monitor.v13.bode_calibration import find_reference
        config=self.spectral.owner.applied_configuration
        for panel,method in zip(self.panels,('tone','pulse_h1','sweep')):
            if isinstance(panel,BodeChirp):method='chirp' if panel.method.currentIndex()==1 else 'sweep'
            panel.reference=find_reference(self.instrument,config,method)
            if panel.reference is not None:
                low, high = panel.reference['points'][0][0], panel.reference['points'][-1][0]
                panel.calibrated.setToolTip(
                    f'Referencia validada · {config.bits} bits · {number(config.rate/1000, formats.ng)} kHz\n'
                    f'Banda: {number(low, formats.ng)}–{number(high, formats.ng)} Hz. No se extrapola fuera de ella.')
            else:
                panel.calibrated.setToolTip('Sin referencia validada para este Q, firmware, perfil ADC y método.')
            panel.calibrated.blockSignals(True)
            panel.calibrated.setEnabled(panel.reference is not None)
            panel.calibrated.setChecked(panel.reference is not None)
            panel.calibrated.blockSignals(False)
        if self.spectral.mode==3:self.draw()

    @staticmethod
    def organize(panel,form):
        # Reuse the controls and signals, replacing the tall inherited form.
        while form.rowCount():
            row=form.takeRow(0)
            if row.labelItem and row.labelItem.widget():
                row.labelItem.widget().hide();row.labelItem.widget().deleteLater()
            if row.fieldItem and row.fieldItem.layout():
                layout=row.fieldItem.layout()
                while layout.count():layout.takeAt(0)
                layout.deleteLater()
        form.setContentsMargins(4,5,4,2)
        form.setVerticalSpacing(5);form.setHorizontalSpacing(8)

        def pair(fields):
            widget=QtWidgets.QWidget();grid=QtWidgets.QGridLayout(widget)
            grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(8);grid.setVerticalSpacing(2)
            for col,(text,control) in enumerate(fields):
                label=QtWidgets.QLabel(text)
                label.setStyleSheet('color:#aeb8c8; background:transparent; border:none;')
                grid.addWidget(label,0,col);grid.addWidget(control,1,col)
                grid.setColumnStretch(col,1)
            form.addRow(widget)

        pair((('Desde',panel.start),('Hasta',panel.end)))
        if isinstance(panel,BodeChirp):
            form.addRow('Método',panel.method)
            pair((('Barrido',panel.duration),('Cola',panel.capture)))
        elif isinstance(panel,BodePulse):
            pair((('Ancho',panel.width),('Captura',panel.capture)))
            form.addRow('Pulsos',panel.averages)
        else:
            pair((('Puntos / década',panel.points),('Ciclos',panel.cycles)))
            form.addRow('Asentamiento',panel.settle)
            form.addRow(panel.estimate)
        options=QtWidgets.QHBoxLayout();options.setSpacing(8)
        panel.calibrated.setText('Calibración');panel.log_frequency.setText('Eje X log')
        options.addWidget(panel.calibrated);options.addWidget(panel.log_frequency)
        form.addRow(options)
        buttons=QtWidgets.QHBoxLayout();buttons.setSpacing(8)
        buttons.addWidget(panel.add_button);buttons.addWidget(panel.button)
        form.addRow(buttons)
        for label in (panel.coverage,panel.curve_labels,panel.status):form.addRow(label)
        for control in (panel.start,panel.end,panel.points,panel.settle,panel.cycles,
                        getattr(panel,'width',None),getattr(panel,'capture',None),
                        getattr(panel,'averages',None),
                        getattr(panel,'method',None),getattr(panel,'duration',None)):
            if control is not None:
                control.setMinimumWidth(0);control.setMinimumHeight(28)
                control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        for button in (panel.button,panel.add_button):button.setMinimumHeight(30)
        for label in (panel.estimate,panel.coverage,panel.curve_labels,panel.status):
            label.setStyleSheet('color:#aeb8c8; background:transparent; border:none;')
        for label in (panel.coverage,panel.curve_labels):label.setVisible(bool(label.text()))
        panel.status.setContentsMargins(0,3,0,0)

    def __getattr__(self,name):return getattr(self.panels[self.tabs.currentIndex()],name)
    @property
    def active(self):return any(p.active for p in self.panels)
    def confirmed(self,reply):
        for p in self.panels:p.confirmed(reply)
    def batch(self,batch):
        for p in self.panels:
            if p.active:p.batch(batch)
    def tick(self):
        for p in self.panels:p.tick()
    def cancel(self,*args,**kwargs):
        for p in self.panels:
            if p.active:p.cancel(*args,**kwargs)
    def changed(self,index):
        for p in self.panels:
            if p.active:p.cancel('Cambio de método')
            for pair in p.curve_sets[1:]+p.shadows:
                for curve in pair:curve.hide()
        if not hasattr(self.spectral,'bode'):return
        self.spectral.configure_plots();self.panels[index].draw()
