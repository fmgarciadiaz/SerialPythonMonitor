"""FM generator controls and optional MIDI input; audio generation stays in the transport worker."""
from PyQt6 import QtCore, QtGui, QtWidgets
from monitor.number_format import number
from monitor.v16.fm_source import FMSource, FMParameters, PRESETS, SYNTH_PATCHES, MAX_VOICES
from monitor.v16.midi_process import MidiProcess


class SynthEditorStack(QtWidgets.QStackedWidget):
    """Reserve space for the selected editor instead of the tallest page."""
    def sizeHint(self):
        page = self.currentWidget()
        return page.sizeHint() if page is not None else super().sizeHint()

    def minimumSizeHint(self):
        page = self.currentWidget()
        return page.minimumSizeHint() if page is not None else super().minimumSizeHint()


class FMPanel(QtWidgets.QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.source = None
        self.midi = None
        self._midi_discovery = None
        self.midi_error = ''
        self.notes = []
        self.pressed_notes = set()
        self.sustain_pedal = False
        self.velocity = 1.0
        self.note_id = 0
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0,0,0,0);layout.setVerticalSpacing(5)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.setColumnStretch(0,1);layout.setColumnStretch(1,1)
        # Reuse the monitor's graduated dial, including its centered paint geometry.
        from monitor.v16.app import InstrumentDial, AmplitudeDial, GeneratorComboBox, generator_wave_icon
        from pathlib import Path
        self.tabs = SynthEditorStack()
        self.tabs.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.tabs.currentChanged.connect(lambda: self.tabs.updateGeometry())
        self.editor_mode=GeneratorComboBox()
        self.editor_mode.setFixedHeight(28);self.editor_mode.setIconSize(QtCore.QSize(18,18))
        assets=Path(__file__).parent/'assets'
        for title,icon in (('Config','instrument_manual'),('Osc 1','fm_operators'),('Osc 2','fm_operators'),('Osc 3','fm_operators'),('ADSR','fm_adsr'),('Timbre','fm_timbre'),('Filtros','synth_filters'),('Virtual','instrument_pluck')):
            self.editor_mode.addItem(QtGui.QIcon(str(assets/(icon+'.svg'))),title)
        self.editor_mode.setItemData(0,"MIDI, velocidad, salida y reproducción",QtCore.Qt.ItemDataRole.ToolTipRole)
        self.editor_mode.setItemData(1,"Oscilador 1 · FM o formas de onda",QtCore.Qt.ItemDataRole.ToolTipRole)
        self.editor_mode.setItemData(2,"Oscilador 2 · mezcla, octava y desafinación",QtCore.Qt.ItemDataRole.ToolTipRole)
        self.editor_mode.currentIndexChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.editor_mode.setCurrentIndex)
        operators = QtWidgets.QWidget();envelope = QtWidgets.QWidget();timbre=QtWidgets.QWidget();filters=QtWidgets.QWidget();osc2=QtWidgets.QWidget();osc3=QtWidgets.QWidget();virtual=QtWidgets.QWidget()
        operator_grid=QtWidgets.QGridLayout(operators);envelope_grid=QtWidgets.QGridLayout(envelope)
        timbre_grid=QtWidgets.QGridLayout(timbre)
        filter_grid=QtWidgets.QGridLayout(filters)
        osc2_grid=QtWidgets.QGridLayout(osc2)
        osc3_grid=QtWidgets.QGridLayout(osc3)
        virtual_grid=QtWidgets.QGridLayout(virtual)
        for grid in (operator_grid,envelope_grid,timbre_grid,filter_grid,osc2_grid,osc3_grid,virtual_grid):
            grid.setContentsMargins(0,2,0,2);grid.setSpacing(2)
            grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        config = QtWidgets.QWidget()
        config_grid = QtWidgets.QGridLayout(config)
        config_grid.setContentsMargins(0,2,0,2)
        config_grid.setVerticalSpacing(5)
        config_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        for page in (config,operators,osc2,osc3,envelope,timbre,filters,virtual):self.tabs.addWidget(page)
        layout.addWidget(self.tabs,0,0,1,2)
        self.dials = []

        def knob(grid,position,title,value,low,high,suffix,scale=100,volume=False):
            box=QtWidgets.QWidget();column=QtWidgets.QVBoxLayout(box)
            column.setContentsMargins(0,0,0,0);column.setSpacing(0)
            label=QtWidgets.QLabel(title);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            dial=AmplitudeDial() if volume else InstrumentDial();dial.setFixedSize(36,36);dial.setNotchesVisible(True)
            if grid is virtual_grid:dial.setProperty('virtualColor',True)
            dial.setRange(round(low*scale),round(high*scale));dial.setSingleStep(1)
            spin=QtWidgets.QDoubleSpinBox();spin.setRange(low,high);spin.setDecimals(2)
            spin.setMinimumWidth(0);spin.setSuffix(suffix);spin.setSingleStep(1/scale)
            spin.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
            spin.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            def synchronize(value):
                with QtCore.QSignalBlocker(dial):dial.setValue(round(value*scale))
            dial.valueChanged.connect(lambda value:spin.setValue(value/scale))
            spin.valueChanged.connect(synchronize);spin.setValue(value);synchronize(value)
            column.addWidget(label);column.addWidget(dial,0,QtCore.Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(spin);grid.addWidget(box,position//2+(2 if grid in (operator_grid,filter_grid,osc2_grid,osc3_grid,virtual_grid) else 0),position%2)
            self.dials.append(dial)
            return spin

        carrier=knob(operator_grid,0,'Portadora',440,.1,10000,' Hz',10)
        self.ratio=knob(operator_grid,1,'Relación M/C',.5,.1,8,' ×')
        index=knob(operator_grid,2,'Nivel modulador',2,0,20,'')
        amplitude=knob(operator_grid,3,'Vol',2.5,0,3.3,' Vpp',volume=True)
        self.dials[3].setFixedSize(60,60)
        volume_column=amplitude.parentWidget().layout()
        volume_column.removeWidget(amplitude)
        amplitude.hide()
        self.volume_value=QtWidgets.QLabel()
        self.volume_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.volume_value.setStyleSheet('color:#aeb8c8; background:transparent; border:none; padding:0;')
        amplitude.valueChanged.connect(lambda value:self.volume_value.setText(number(value,'.2f')+' Vpp'))
        self.volume_value.setText(number(amplitude.value(),'.2f')+' Vpp')
        volume_column.addWidget(self.volume_value)
        modulator=QtWidgets.QDoubleSpinBox(self);modulator.setRange(.1,10000)
        modulator.setValue(220);modulator.hide()
        self.controls=[carrier,modulator,index,amplitude]
        self.envelope_controls=[]
        for i,(title,value,low,high,suffix,scale) in enumerate([
            ('Ataque',8,1,2000,' ms',1),('Caída',50,1,3000,' ms',1),
            ('Sostenido',100,0,100,' %',1),('Liberación',25,1,3000,' ms',1)]):
            spin=knob(envelope_grid,i,title,value,low,high,suffix,scale)
            spin.valueChanged.connect(self.update_source);self.envelope_controls.append(spin)
        # Keep dial indices stable for existing controls; replace ADSR visuals.
        for control in self.envelope_controls:control.parentWidget().hide()
        self.osc2_envelope_controls=[]
        for control in self.envelope_controls:
            spin=QtWidgets.QDoubleSpinBox();spin.setRange(control.minimum(),control.maximum());spin.setValue(control.value())
            spin.setMinimumWidth(0);spin.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            spin.valueChanged.connect(self.update_source);self.osc2_envelope_controls.append(spin)
        self.osc3_envelope_controls=[]
        for control in self.envelope_controls:
            spin=QtWidgets.QDoubleSpinBox();spin.setRange(control.minimum(),control.maximum());spin.setValue(control.value())
            spin.setMinimumWidth(0);spin.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            spin.valueChanged.connect(self.update_source);self.osc3_envelope_controls.append(spin)
        from monitor.v16.envelope_editor import EnvelopeEditor
        self.envelope_editor=EnvelopeEditor((('Osc 1 · ms / %',self.envelope_controls,'#55dfc4'),
                                            ('Osc 2 · ms / %',self.osc2_envelope_controls,'#a8b7d5'),
                                            ('Osc 3 · ms / %',self.osc3_envelope_controls,'#e2bd72')))
        envelope_grid.addWidget(self.envelope_editor,0,0,3,2)
        self.timbre_controls=[]
        for i,(title,value,low,high,suffix) in enumerate([
            ('Relación brillo',3.5,.1,8,' ×'),('Mezcla brillo',0,0,100,' %'),
            ('Caída brillo',700,1,3000,' ms'),('Velocidad',65,0,100,' %')]):
            spin=knob(timbre_grid,i,title,value,low,high,suffix,1 if i>0 else 100)
            spin.valueChanged.connect(self.update_source);self.timbre_controls.append(spin)
        self.filter_type=GeneratorComboBox();self.filter_type.setFixedHeight(28)
        self.filter_type.setIconSize(QtCore.QSize(18,18))
        for title,value in (('Sin filtro','off'),('Pasa bajos','lowpass'),('Pasa altos','highpass'),
                            ('Pasa banda','bandpass'),('Notch','notch')):
            self.filter_type.addItem(QtGui.QIcon(str(assets/'synth_filters.svg')),title,value)
        filter_label=QtWidgets.QLabel('Tipo');filter_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        filter_grid.addWidget(filter_label,0,0,1,2);filter_grid.addWidget(self.filter_type,1,0,1,2)
        self.filter_controls=[]
        for i,(title,value,low,high,suffix,scale) in enumerate([
            ('Corte',2000,20,9000,' Hz',1),('Resonancia',.71,.5,8,' Q',100),
            ('Drive',1,1,8,' ×',100),('Mezcla',100,0,100,' %',1)]):
            spin=knob(filter_grid,i,title,value,low,high,suffix,scale)
            spin.valueChanged.connect(self.update_source);self.filter_controls.append(spin)
        self.filter_type.currentIndexChanged.connect(self._filter_changed)
        self._filter_changed()
        self.osc2_wave=GeneratorComboBox();self.osc2_wave.setIconSize(QtCore.QSize(24,14))
        for wave,title,index in (('sine','Seno',1),('square','Cuadrada',0),('triangle','Triángulo',2),('saw','Rampa',3)):
            self.osc2_wave.addItem(generator_wave_icon(index),title,wave)
        self.osc2_wave.addItem(QtGui.QIcon(str(assets/'mode_fm.svg')),'FM','fm')
        self.osc2_wave.setCurrentIndex(3)
        self.osc2_octave=GeneratorComboBox()
        for title,value in (('−1 octava',-1),('Misma octava',0),('+1 octava',1)):self.osc2_octave.addItem(title,value)
        self.osc2_octave.setCurrentIndex(1)
        for column,(title,control) in enumerate((('Onda',self.osc2_wave),('Octava',self.osc2_octave))):
            label=QtWidgets.QLabel(title);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            osc2_grid.addWidget(label,0,column);osc2_grid.addWidget(control,1,column)
        self.osc2_detune=knob(osc2_grid,0,'Detune',0,-20,20,' cents',10)
        self.osc2_mix=knob(osc2_grid,1,'Mezcla',0,0,100,' %',1)
        for control in (self.osc2_wave,self.osc2_octave,self.osc2_detune,self.osc2_mix):
            control.setMinimumWidth(0);control.valueChanged.connect(self.update_source) if isinstance(control,QtWidgets.QDoubleSpinBox) else control.currentIndexChanged.connect(self.update_source)
        self.osc2_fm_ratio=knob(osc2_grid,2,'Parcial FM',1,.1,31,' ×')
        self.osc2_fm_amount=knob(osc2_grid,3,'Amount FM',1.5,0,20,'')
        for control in (self.osc2_fm_ratio,self.osc2_fm_amount):control.valueChanged.connect(self.update_source)
        self.osc2_wave.currentIndexChanged.connect(self._osc2_changed)
        self._osc2_changed()
        self.osc3_ratio=knob(osc3_grid,0,'Parcial FM',1,.1,31,' ×')
        self.osc3_amount=knob(osc3_grid,1,'Amount FM',1.4,0,20,'')
        self.osc3_detune=knob(osc3_grid,2,'Detune',-7,-20,20,' cents',10)
        self.osc3_mix=knob(osc3_grid,3,'Mezcla',0,0,100,' %',1)
        self.feedback_controls=[]
        from monitor.v16.fm_feedback import warmup
        feedback_available=warmup()
        for grid in (operator_grid,osc2_grid,osc3_grid):
            label=QtWidgets.QLabel('Feedback');label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            spin=QtWidgets.QDoubleSpinBox();spin.setRange(0,7);spin.setSingleStep(.1);spin.setDecimals(1)
            spin.setMinimumWidth(0);spin.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            spin.setEnabled(feedback_available);spin.setToolTip('Realimentación del modulador · 0–7')
            grid.addWidget(label,6,0);grid.addWidget(spin,6,1)
            spin.valueChanged.connect(self.update_source);self.feedback_controls.append(spin)
        for control in (self.osc3_ratio,self.osc3_amount,self.osc3_detune,self.osc3_mix):control.valueChanged.connect(self.update_source)
        self.ratio.valueChanged.connect(self._ratio_changed)
        for spin in self.controls:spin.valueChanged.connect(self.update_source)
        self.waveform=GeneratorComboBox();self.waveform.setIconSize(QtCore.QSize(24,14))
        self.waveform.addItem(QtGui.QIcon(str(assets/'mode_fm.svg')),'FM','fm')
        for wave,title,index in (('sine','Seno',1),('square','Cuadrada',0),
                                 ('triangle','Triángulo',2),('saw','Rampa',3)):
            self.waveform.addItem(generator_wave_icon(index),title,wave)
        self.waveform.addItem(QtGui.QIcon(str(assets/'instrument_pluck.svg')),'Virtual','virtual')
        self.virtual_model=GeneratorComboBox()
        self.virtual_model.addItem(QtGui.QIcon(str(assets/'instrument_guitar.svg')),'Guitarra','guitar')
        self.virtual_model.addItem(QtGui.QIcon(str(assets/'instrument_piano.svg')),'Piano','piano')
        virtual_grid.addWidget(self.virtual_model,0,0,1,2)
        self.virtual_model.currentIndexChanged.connect(self._virtual_model_changed)
        self.string_controls=[knob(virtual_grid,0,'Vibración',3,.1,10,' s',100),knob(virtual_grid,1,'Posición',22,5,95,' %',1),knob(virtual_grid,2,'Brillo',65,5,95,' %',1),knob(virtual_grid,3,'Caja',55,0,100,' %',1),knob(virtual_grid,4,'Puente',20,0,100,' %',1),knob(virtual_grid,5,'Rigidez',15,0,100,' %',1)]
        for control in self.string_controls:control.valueChanged.connect(self.update_source)
        room_row=QtWidgets.QWidget();room_layout=QtWidgets.QGridLayout(room_row)
        room_layout.setContentsMargins(0,0,0,0)
        room_layout.setHorizontalSpacing(virtual_grid.horizontalSpacing());room_layout.setVerticalSpacing(2)
        self.room_mix=QtWidgets.QSpinBox();self.room_mix.setRange(0,30);self.room_mix.setSuffix(' %')
        self.room_decay=QtWidgets.QDoubleSpinBox();self.room_decay.setRange(.1,5);self.room_decay.setDecimals(1);self.room_decay.setValue(1.2);self.room_decay.setSuffix(' s')
        for column,(text,control) in enumerate((('Sala',self.room_mix),('Cola',self.room_decay))):
            label=QtWidgets.QLabel(text);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            control.setMinimumWidth(0);control.setFixedHeight(28)
            control.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            control.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            room_layout.setColumnStretch(column,1)
            room_layout.addWidget(label,0,column);room_layout.addWidget(control,1,column)
            control.valueChanged.connect(self.update_source)
        virtual_grid.addWidget(room_row,5,0,1,2)
        from monitor.v16.virtual_string import warmup as warmup_string
        warmup_string()
        from monitor.v16.virtual_instruments import warmup as warmup_instruments
        warmup_instruments()
        self.waveform.setFixedHeight(28)
        self.waveform.currentIndexChanged.connect(self._waveform_changed)
        self.preset = GeneratorComboBox()
        preset_icons={'Manual':'manual','Seno limpio':'manual','Bass Punch':'bass','Lead':'lead','Brass':'brass',
                      'Warm Pad':'pad','Guitarra':'guitar','Piano Virtual':'piano','Pluck':'pluck','Flauta':'flute','Órgano':'organ',
                      'DX Brillo':'epiano','DX Piano':'epiano','Campana':'bell'}
        for name in PRESETS:
            self.preset.addItem(QtGui.QIcon(str(assets/('instrument_'+preset_icons[name]+'.svg'))),name)
        self.preset.setIconSize(QtCore.QSize(18,18))
        self.preset.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
        self.preset.currentTextChanged.connect(self.apply_preset)
        for column,title in enumerate(('Sonido','Preset')):
            label=QtWidgets.QLabel(title);label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            operator_grid.addWidget(label,0,column)
        operator_grid.addWidget(self.waveform,1,0)
        operator_grid.addWidget(self.preset,1,1)
        self.preset.setToolTip('Preset del sintetizador')
        self.config_preset=GeneratorComboBox()
        self.config_preset.setModel(self.preset.model())
        self.config_preset.setIconSize(self.preset.iconSize())
        self.config_preset.setToolTip('Preset del sintetizador')
        self.preset.currentIndexChanged.connect(self.config_preset.setCurrentIndex)
        self.config_preset.currentIndexChanged.connect(self.preset.setCurrentIndex)
        config_grid.addWidget(self.config_preset,0,0,1,2)
        self.velocity_label=QtWidgets.QLabel('Velocidad · —')
        self.velocity_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.midi_activity=QtWidgets.QLabel()
        self.midi_activity.setFixedSize(8,8)
        self.midi_activity.setToolTip('Recepción de mensajes MIDI')
        self.midi_activity_timer=QtCore.QTimer(self)
        self.midi_activity_timer.setSingleShot(True)
        self.midi_activity_timer.setInterval(150)
        self.midi_activity_timer.timeout.connect(lambda:self._set_midi_activity(False))
        self._set_midi_activity(False)
        activity_row=QtWidgets.QHBoxLayout()
        activity_row.setContentsMargins(0,0,0,0);activity_row.setSpacing(6)
        activity_row.addWidget(self.midi_activity)
        activity_row.addWidget(self.velocity_label,1)
        config_grid.addLayout(activity_row,2,0,1,2)
        self.note_label=QtWidgets.QLabel('Nota · —')
        self.pedal_label=QtWidgets.QLabel('Pedal · libre')
        for label in (self.note_label,self.pedal_label):
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        config_grid.addWidget(self.note_label,3,0)
        config_grid.addWidget(self.pedal_label,3,1)
        self.refresh = QtWidgets.QPushButton('↻');self.refresh.clicked.connect(self.refresh_midi)
        self.refresh.setToolTip('Actualizar entradas MIDI')
        self.refresh.setStyleSheet('QPushButton {background:#2c3240; border:1px solid #3e4658; color:#d3d8e0; padding:0; border-radius:6px;} QPushButton:hover {background:#394152;} QPushButton:pressed {background:#202630;} QPushButton:disabled {color:#627083;}')
        self.refresh.setFixedWidth(30)
        self.midi_input = QtWidgets.QComboBox();self.midi_input.addItem('Sin MIDI')
        self.midi_input.setStyleSheet('QComboBox {padding-left:10px;} QComboBox QAbstractItemView::item {padding-left:10px;}')
        self.midi_input.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
        self.midi_input.currentIndexChanged.connect(self.choose_midi)
        midi_row=QtWidgets.QHBoxLayout();midi_row.setContentsMargins(0,0,0,0);midi_row.setSpacing(4)
        midi_row.addWidget(self.refresh);midi_row.addWidget(self.midi_input,1)
        config_grid.addLayout(midi_row,1,0,1,2)
        self.play = QtWidgets.QPushButton('Play');self.play.setFixedHeight(32)
        self.play.clicked.connect(self.toggle);config_grid.addWidget(self.play,5,0,1,2)
        self.output_rate=GeneratorComboBox()
        self.output_rate.addItem(f'20 kHz · {MAX_VOICES} voces',20000)
        self.output_rate.addItem(f'40 kHz · experimental',40000)
        self.output_rate.setFixedHeight(28)
        self.output_rate.setToolTip(f'Hasta {MAX_VOICES} voces. 20 kHz: mayor margen de transporte; 40 kHz: experimental.')
        self.info = self.output_rate
        config_grid.addWidget(self.info,4,0,1,2)
        volume_box=amplitude.parentWidget()
        operator_grid.removeWidget(volume_box)
        config_grid.addWidget(volume_box,6,0,1,2)
        self.osc1_mix=knob(operator_grid,3,'Mezcla',100,0,100,' %',1)
        self.osc1_mix.setToolTip('Nivel de Osc 1 antes del volumen máximo; 0 % silencia este oscilador.')
        self.osc1_mix.valueChanged.connect(self.update_source)
        for control in (self.osc2_mix,self.osc3_mix):
            control.setToolTip('Nivel independiente antes del volumen máximo; no reduce los otros osciladores.')
        # Match the equal columns used by the Analysis selectors; text must not
        # enlarge one column and squeeze its neighbour.
        for grid in (operator_grid,envelope_grid,timbre_grid,filter_grid,osc2_grid,osc3_grid,virtual_grid):
            grid.setColumnStretch(0,1);grid.setColumnStretch(1,1)
            grid.setHorizontalSpacing(owner.generator_panel.layout().horizontalSpacing())
        for combo in (self.editor_mode,self.waveform,self.preset,self.config_preset,self.filter_type,self.output_rate,self.osc2_wave,self.osc2_octave,self.virtual_model):
            combo.setMinimumWidth(0)
            combo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
            combo.setFixedHeight(28)
        for spin in self.controls+ self.envelope_controls+self.timbre_controls+self.filter_controls+[self.osc2_detune,self.osc2_mix]:
            spin.setFixedHeight(28)
        self.preset.setCurrentText("DX Piano")
        owner.generator_mode.currentIndexChanged.connect(self._generator_mode_entered)

    def _generator_mode_entered(self, index):
        if index == 5:
            self.refresh_midi()

    def parameters(self, level=1):
        gate = bool(self.notes) or self.midi_input.currentIndex()<=0
        carrier,modulator,index = [control.value() for control in self.controls[:3]]
        limit=self.output_rate.currentData()*.4
        carrier=min(carrier,limit-.1)
        if self.preset.currentText() != 'Manual' or self.midi_input.currentIndex()>0 or self.output_rate.currentData()<40000:
            # Reduce brightness in the high register rather than reject MIDI notes.
            modulator = min(modulator,max(.1,limit-carrier))
            index = min(index,max(0,(limit-carrier)/modulator-1))
        return FMParameters(carrier,modulator,index,level,
                            self.preset.currentText(),gate,self.note_id,
                            (self.envelope_controls[0].value()/1000,
                             self.envelope_controls[1].value()/1000,
                             self.envelope_controls[2].value()/100,
                             self.envelope_controls[3].value()/1000),
                            oscillator_levels=(self.osc1_mix.value()/100,self.osc2_mix.value()/100,self.osc3_mix.value()/100),
                            osc2_envelope=tuple(c.value()/(100 if i==2 else 1000) for i,c in enumerate(self.osc2_envelope_controls)),
                            fm_body_envelope=tuple(c.value()/(100 if i==2 else 1000) for i,c in enumerate(self.envelope_controls)) if self.preset.currentText() in ('DX Piano','DX Brillo') else None,
                            fm_brightness_envelope=None,
                            room_mix=self.room_mix.value()/100,room_decay=self.room_decay.value(),virtual_model=self.virtual_model.currentData(),virtual_sustain=self.sustain_pedal,body_mix=self.string_controls[3].value()/100,bridge_coupling=self.string_controls[4].value()/100,string_stiffness=self.string_controls[5].value()*.00002,
                            string_decay=self.string_controls[0].value(),string_position=self.string_controls[1].value()/100,string_brightness=self.string_controls[2].value()/100,
                            dx_body_detune=None,
                            feedback=self.feedback_controls[0].value(),osc2_feedback=self.feedback_controls[1].value(),osc3_feedback=self.feedback_controls[2].value(),
                            osc3_mix=self.osc3_mix.value()/100,osc3_ratio=self.osc3_ratio.value(),osc3_amount=self.osc3_amount.value(),osc3_detune=self.osc3_detune.value(),
                            osc3_envelope=tuple(c.value()/(100 if i==2 else 1000) for i,c in enumerate(self.osc3_envelope_controls)),
                            note_ratio=self.ratio.value() if self.midi_input.currentIndex()>0 else None,
                            note_index=self.controls[2].value() if self.midi_input.currentIndex()>0 else None,
                            notes=tuple(self.notes[-MAX_VOICES:]) if self.midi_input.currentIndex()>0 else None,
                            bell_ratio=self.timbre_controls[0].value(),
                            bell_mix=self.timbre_controls[1].value()/100,
                            brightness_decay=self.timbre_controls[2].value()/1000,
                            velocity_sensitivity=self.timbre_controls[3].value()/100,
                            waveform=self.waveform.currentData(),
                            osc2_wave=self.osc2_wave.currentData(),osc2_octave=self.osc2_octave.currentData(),
                            osc2_fm_ratio=self.osc2_fm_ratio.value(),osc2_fm_amount=self.osc2_fm_amount.value(),
                            osc2_detune=self.osc2_detune.value(),osc2_mix=self.osc2_mix.value()/100,filter_type=self.filter_type.currentData(),
                            cutoff=self.filter_controls[0].value(),resonance=self.filter_controls[1].value(),
                            drive=self.filter_controls[2].value(),filter_mix=self.filter_controls[3].value()/100)

    def _osc2_changed(self,*args):
        fm=self.osc2_wave.currentData()=='fm'
        for control in (self.osc2_fm_ratio,self.osc2_fm_amount):control.parentWidget().setVisible(fm)

    def _filter_changed(self,*args):
        enabled=self.filter_type.currentData()!='off'
        for widget in (*self.filter_controls,*self.dials[12:16]):widget.setEnabled(enabled)
        if hasattr(self,'preset'):self.update_source()

    def _virtual_model_changed(self,*args):
        piano=self.virtual_model.currentData()=='piano'
        self.string_controls[5].parentWidget().setEnabled(piano)
        self.string_controls[5].setToolTip('Piano: 15 % reproduce la rigidez publicada por registro; los demás valores la escalan proporcionalmente.')
        self.string_controls[1].setToolTip('Piano: 12 % reproduce la posición publicada por registro; los demás valores la escalan proporcionalmente.' if piano else 'Posición del pellizco como porcentaje de la longitud de cuerda.')
        self.string_controls[2].setToolTip('Piano: 78 % reproduce el contacto de referencia; cambia la dureza del fieltro en el próximo golpe.' if piano else 'Brillo de la cuerda.')
        self.update_source()

    def _waveform_changed(self,*args):
        fm=self.waveform.currentData()=='fm'
        for widget in (self.ratio,self.controls[2],self.dials[1],self.dials[2],
                       *self.timbre_controls,*self.dials[8:12]):widget.setEnabled(fm)
        self.controls[0].parentWidget().layout().itemAt(0).widget().setText('Portadora' if fm else 'Frecuencia')
        self.update_source()

    def _ratio_changed(self, *args):
        with QtCore.QSignalBlocker(self.controls[1]):
            self.controls[1].setValue(self.controls[0].value()*self.ratio.value())
        self.update_source()

    def apply_preset(self, name):
        ratio,index,attack,decay,sustain,release,*_ = PRESETS[name]
        widgets=[self.waveform,self.filter_type,self.controls[0],self.ratio,self.controls[1],self.controls[2],
                 *self.envelope_controls,*self.osc2_envelope_controls,*self.timbre_controls,*self.filter_controls,
                 self.osc1_mix,self.osc2_wave,self.osc2_octave,self.osc2_detune,self.osc2_mix,self.osc2_fm_ratio,self.osc2_fm_amount,self.osc3_ratio,self.osc3_amount,self.osc3_detune,self.osc3_mix,*self.osc3_envelope_controls,*self.feedback_controls,*self.string_controls,self.virtual_model,self.room_mix,self.room_decay]
        blockers=[QtCore.QSignalBlocker(widget) for widget in widgets]
        second={'Bass Punch':('square',-1,0,20),'Lead':('saw',0,6,35),
                'Brass':('saw',0,7,40),'Warm Pad':('saw',0,10,50),
                'Pluck':('triangle',0,4,20),'Órgano':('sine',-1,0,20),
                'DX Piano':('fm',0,3.5,25),'DX Brillo':('fm',0,4,42)}.get(name,('saw',0,0,0))
        wave2,octave,detune,mix2=second
        self.osc2_wave.setCurrentIndex(self.osc2_wave.findData(wave2))
        self.osc2_octave.setCurrentIndex(self.osc2_octave.findData(octave))
        self.osc2_detune.setValue(detune);self.osc2_mix.setValue(mix2)
        self.osc2_fm_ratio.setValue(14 if name in ('DX Piano','DX Brillo') else 1)
        self.osc2_fm_amount.setValue(.55 if name=='DX Piano' else 1.35 if name=='DX Brillo' else 1.5)
        self._osc2_changed()
        patch=SYNTH_PATCHES.get(name)
        if patch:
            wave,cutoff,resonance,drive,mix,pitch=patch
            self.waveform.setCurrentIndex(self.waveform.findData(wave))
            self.controls[0].setValue(pitch)
            self.filter_type.setCurrentIndex(self.filter_type.findData('lowpass'))
            for control,value in zip(self.filter_controls,(cutoff,resonance,drive,mix*100)):control.setValue(value)
        else:
            if name!='Manual':self.waveform.setCurrentIndex(self.waveform.findData('virtual') if name in ('Guitarra','Piano Virtual') else 0)
            if name=='Seno limpio':self.waveform.setCurrentIndex(self.waveform.findData('sine'))
            self.filter_type.setCurrentIndex(0)
            for control,value in zip(self.filter_controls,(2000,.71,1,100)):control.setValue(value)
        self.ratio.setValue(.5 if ratio is None else ratio)
        self.controls[1].setValue(self.controls[0].value()*self.ratio.value())
        self.controls[2].setValue(index)
        for control,value in zip(self.envelope_controls,(attack*1000,decay*1000,sustain*100,release*1000)):
            control.setValue(value)
        for first,second in zip(self.envelope_controls,self.osc2_envelope_controls):second.setValue(first.value())
        if name in ('DX Piano','DX Brillo'):
            metal_adsr=(3,1800,0,160) if name=='DX Piano' else (2,1400,0,140)
            for control,value in zip(self.osc2_envelope_controls,metal_adsr):control.setValue(value)
        for first,second in zip(self.envelope_controls,self.osc3_envelope_controls):second.setValue(first.value())
        self.osc3_ratio.setValue(1);self.osc3_amount.setValue(index*.7)
        self.osc3_detune.setValue(-7 if name=='DX Piano' else -8 if name=='DX Brillo' else 0)
        self.osc3_mix.setValue(26 if name=='DX Piano' else 24 if name=='DX Brillo' else 0)
        # Preserve each preset's former nested crossfade as independent levels.
        mix3=self.osc3_mix.value()/100
        self.osc1_mix.setValue((100-mix2)*(1-mix3))
        self.osc2_mix.setValue(mix2*(1-mix3))
        for i,control in enumerate(self.feedback_controls):control.setValue(4 if i==2 and name in ('DX Piano','DX Brillo') and control.isEnabled() else 0)
        brightness=PRESETS[name][6]
        timbre=(1,0,1800,90) if name=='DX Brillo' else (1,0,2400,80) if name=='DX Piano' else (3.5,0,
                    max(1,brightness*1000) if brightness else 700,80 if name=='DX Piano' else 65)
        for control,value in zip(self.timbre_controls,timbre):
            control.setValue(value)
        self.virtual_model.setCurrentIndex(1 if name=='Piano Virtual' else 0)
        self.room_mix.setValue(6 if name=='Piano Virtual' else 0);self.room_decay.setValue(1.2)
        for control,value in zip(self.string_controls,(4,12,78,45,20,15) if name=='Piano Virtual' else (3,22,65,55,20,0)):control.setValue(value)
        self.note_id += 1
        self._waveform_changed();self._filter_changed();self._virtual_model_changed()
        del blockers
        self.update_source()

    def update_source(self, *args):
        if getattr(self,'_midi_updating_controls',False):return
        if self.sender() is self.controls[0]:
            with QtCore.QSignalBlocker(self.controls[1]):
                self.controls[1].setValue(self.controls[0].value()*self.ratio.value())
        if not self.source: return
        try:
            self.source.update(self.parameters(self.velocity if self.notes else (0 if self.midi_input.currentIndex()>0 else 1)))
            self.owner.serial_worker.request_wav_levels(self.controls[3].value(),1.65)
        except (ValueError,AttributeError) as error: self.owner.generator_status.setText(str(error))

    def toggle(self):
        owner = self.owner
        if owner._wav_active:
            owner._stop_wav();self.source=None;self.output_rate.setEnabled(True);self.play.setText('Play');return
        if owner.serial_worker is None or not owner._wav_capable:
            owner.generator_status.setText('Conectar Q con firmware de audio antes de iniciar Synth');return
        if owner.output_pending or owner.applied_configuration.rate > 40000:
            owner.generator_status.setText('Synth: esperando adquisición de hasta 40 kHz. Volvé a pulsar Play cuando se aplique.')
            return
        rate=self.output_rate.currentData()
        if not owner.wav_rate.model().item(owner.wav_rate.findData(rate)).isEnabled():
            owner.generator_status.setText('El Q no confirmó la tasa de salida elegida');return
        try:
            source = FMSource(rate=rate,parameters=self.parameters(self.velocity if self.notes else (0 if self.midi_input.currentIndex()>0 else 1)))
            from datetime import datetime
            from pathlib import Path
            folder=Path(__file__).resolve().parents[2]/'diagnosticos'/'resultados_fm'
            folder.mkdir(parents=True,exist_ok=True)
            source.diagnostic_path=folder/('fm_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.jsonl')
            owner.serial_worker.request_wav_levels(self.controls[3].value(),1.65)
            owner.serial_worker.request_wav(1,source,rate)
            self.source=source;owner._wav_active=True;owner._wav_cancelled=False
            owner.single_shot_armed=False
            owner.run_stop_btn.setChecked(True)
            owner.toggle_run_stop()
            self.play.setText('Stop');self.output_rate.setEnabled(False);owner._sync_wav_transport()
            owner.generator_status.setText('Synth · cargando · '+str(rate//1000)+' kHz')
        except Exception as error: owner.generator_status.setText(str(error))

    def status(self, status):
        active = int(status.state) in (1,2)
        self.play.setText('Stop' if int(status.state) in (1,2,4,5) else 'Play')
        names = ('Listo','Cargando','Activo','Finalizado','Interrumpido: faltaron muestras','Error')
        self.output_rate.setEnabled(not active)
        queued=max(0,status.accepted-status.played)/status.rate*1000
        self.output_rate.setToolTip('Audio pendiente en el DAC: '+number(queued,'.0f')+
                                   ' ms. La cola se adapta al transporte; no es la latencia MIDI total.')
        self.owner.generator_status.setText('Synth · '+names[int(status.state)]+' · '+str(status.rate//1000)+' kHz'+
                                            (' · MIDI sin conexión' if self.midi_error else ''))
        if not active: self.source=None

    def refresh_midi(self):
        if self._midi_discovery is not None:return
        self.refresh.setEnabled(False)
        self.owner.generator_status.setText('Buscando entradas MIDI…')
        client=MidiProcess(self);self._midi_discovery=client
        client.ports.connect(self._midi_ports_found)
        client.error.connect(self._midi_discovery_failed)
        client.start()

    def _midi_ports_found(self, names):
        previous=self.midi_input.currentText()
        with QtCore.QSignalBlocker(self.midi_input):
            self.midi_input.clear();self.midi_input.addItem('Sin MIDI')
            self.midi_input.addItem('UNO Q Synth · virtual','virtual')
            self.midi_input.addItems(names)
            self.midi_input.setCurrentText(previous)
            self.midi_input.setToolTip('Notas: portadora; velocidad: volumen; CC1: índice FM; CC7: volumen. Bus IAC para aplicaciones de macOS.')
        client=self._midi_discovery;self._midi_discovery=None
        if client is not None:client.close()
        self.refresh.setEnabled(True);self.midi_error=''
        if self.midi_input.currentText()!=previous:self.choose_midi()
        self.owner.generator_status.setText(str(len(names))+' entradas MIDI · elegir entrada')

    def _midi_discovery_failed(self, text):
        self._midi_discovery=None;self.refresh.setEnabled(True)
        self._midi_failed(text)

    def _midi_failed(self,text):
        self.close_midi();self.update_source();self.midi_error=text
        self.midi_input.setToolTip(text)
        self.owner.generator_status.setText('MIDI: '+text)

    def choose_midi(self, *args):
        self.close_midi()
        self.midi_error=''
        if self.midi_input.currentIndex() <= 0: self.update_source();return
        virtual=self.midi_input.currentData()=='virtual'
        client=MidiProcess(self);self.midi=client
        client.error.connect(self._midi_failed)
        client.messages_ready.connect(self.poll_midi)
        client.ready.connect(lambda:self.owner.generator_status.setText('MIDI conectado · '+self.midi_input.currentText()))
        client.start('UNO Q Synth' if virtual else self.midi_input.currentText(),virtual)
        self.update_source()

    def _set_midi_activity(self, active):
        color='#55dfc4' if active else '#46505e'
        self.midi_activity.setStyleSheet('background:'+color+'; border:none; border-radius:4px;')

    def _update_midi_indicators(self):
        if self.notes:
            note,velocity=self.notes[-1]
            name=('Do','Do♯','Re','Re♯','Mi','Fa','Fa♯','Sol','Sol♯','La','La♯','Si')[note%12]
            self.note_label.setText(f'Nota · {name}{note//12-1}')
            self.note_label.setToolTip(f'Nota MIDI {note} · última voz activa')
            self.velocity_label.setText('Velocidad · '+str(velocity))
        else:
            self.note_label.setText('Nota · —')
            self.note_label.setToolTip('Sin notas activas')
        self.pedal_label.setText('Pedal · '+('pisado' if self.sustain_pedal else 'libre'))
        self.pedal_label.setStyleSheet('color:#55dfc4;' if self.sustain_pedal else '')

    def poll_midi(self):
        if self.midi is None:return
        try:
            changed=False;received=False;last_velocity=None;controller_values={}
            messages=list(self.midi.iter_pending())
            for message in messages:
                received=True
                if message.type not in ('note_on','note_off','control_change'):continue
                changed=True
                if message.type=='note_on' and message.velocity:
                    self.pressed_notes.add(message.note)
                    self.notes=[n for n in self.notes if n[0]!=message.note]+[(message.note,message.velocity)]
                    self.note_id += 1
                    last_velocity=message.velocity
                elif message.type in ('note_off','note_on'):
                    self.pressed_notes.discard(message.note)
                    if not self.sustain_pedal:
                        self.notes=[n for n in self.notes if n[0]!=message.note]
                elif message.type=='control_change':
                    if message.control==1:
                        controller_values[2]=message.value/127*10
                    elif message.control==7:
                        controller_values[3]=message.value/127*3.3
                    elif message.control==64:
                        self.sustain_pedal=message.value>=64
                        if not self.sustain_pedal:
                            self.notes=[n for n in self.notes if n[0] in self.pressed_notes]
                    elif message.control in (120,123):
                        self.notes=[];self.pressed_notes.clear();self.sustain_pedal=False
            if received:
                self._set_midi_activity(True)
                self.midi_activity_timer.start()
            if changed:
                # Keep dial/value-label signals active, but publish only the
                # final controller values together with the complete chord.
                self._midi_updating_controls=True
                try:
                    for control,value in controller_values.items():self.controls[control].setValue(value)
                finally:self._midi_updating_controls=False
                # Process the complete pending chord before making room, so
                # pedal-only notes are recycled for all incoming notes at once.
                while len(self.notes)>MAX_VOICES:
                    victim=next((n for n in self.notes if n[0] not in self.pressed_notes),self.notes[0])
                    self.notes.remove(victim)
                if self.notes:
                    note,velocity=self.notes[-1];self.velocity=velocity/127
                    with QtCore.QSignalBlocker(self.controls[0]):self.controls[0].setValue(440*2**((note-69)/12))
                    with QtCore.QSignalBlocker(self.controls[1]):
                        self.controls[1].setValue(self.controls[0].value()*self.ratio.value())
                if last_velocity is not None:self.velocity_label.setText('Velocidad · '+str(last_velocity))
                self._update_midi_indicators()
                if self.source is not None:
                    self.source.observe_midi_batch(messages)
                self.update_source()
        except Exception as error:
            self.close_midi();self.update_source();self.owner.generator_status.setText('MIDI desconectado: '+str(error))

    def close_midi(self):
        self.notes=[];self.pressed_notes.clear();self.sustain_pedal=False
        self.midi_activity_timer.stop();self._set_midi_activity(False)
        self.velocity_label.setText('Velocidad · —')
        self._update_midi_indicators()
        if self.midi is not None:self.midi.close();self.midi=None

    def close_backend(self):
        self.close_midi()
        if self._midi_discovery is not None:
            self._midi_discovery.close();self._midi_discovery=None
