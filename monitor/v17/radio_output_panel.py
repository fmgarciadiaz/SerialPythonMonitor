"""Generator Radio: shared RADIO tuning/audio, independent A0 volume."""
import queue
import json,logging
from PyQt6 import QtCore,QtWidgets
from monitor.v17.radio_output import RadioDacSource,HighRateRadioDacSource,acquisition_error
from monitor.v17.radio_am import radio_input_supported,radio_tuning_max
from monitor.v17.radio_tuning import tuning_bounds,alias_frequency

def record_stop(owner,source,reason,status=None):
    """Keep the cause across UI resets without blocking acquisition or hiding faults."""
    from datetime import datetime
    from pathlib import Path
    try:
        config=owner.applied_configuration
        entry=dict(time=datetime.now().astimezone().isoformat(),reason=reason,
                   adc=dict(bits=config.bits,rate=config.rate),source=source.diagnostics())
        if status is not None:
            entry['dac']={name:int(getattr(status,name)) for name in
                          ('state','reason','played','accepted','free_blocks','queue_slots')
                          if hasattr(status,name)}
        path=Path(__file__).resolve().parents[2]/'diagnosticos/resultados_v17/radio_a0_stops.jsonl'
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(entry,ensure_ascii=False)+'\n')
    except (OSError,AttributeError,TypeError,ValueError):
        logging.getLogger(__name__).exception('No se pudo guardar la causa de Stop RADIO A0')

class RadioOutputPanel(QtWidgets.QWidget):
    def __init__(self,owner,dial_type=QtWidgets.QDial,combo_type=QtWidgets.QComboBox):
        super().__init__();self.owner=owner;self.source=None
        box=QtWidgets.QVBoxLayout(self);box.setContentsMargins(0,6,0,0);box.setSpacing(6)
        self.frequency=QtWidgets.QLabel('Sintonía del panel RADIO')
        self.frequency.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        box.addWidget(self.frequency)
        self.input_source=combo_type();self.input_source.addItems(['RADIO','FILTER'])
        self.input_source.setProperty('centerInWholeBox',True)
        self.input_source.setToolTip('IN: RADIO demodulada o FILTER con fuente RADIO')
        self.input_source.currentTextChanged.connect(self.input_changed)
        self.play=QtWidgets.QPushButton('▶ Play');self.play.clicked.connect(self.toggle)
        box.addWidget(self.play)
        levels=QtWidgets.QHBoxLayout();levels.setSpacing(6)
        volume_box=QtWidgets.QVBoxLayout();offset_box=QtWidgets.QVBoxLayout()
        label=QtWidgets.QLabel('Volumen · A0');label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter);volume_box.addWidget(label)
        self.volume=dial_type();self.volume.setRange(0,100);self.volume.setValue(25)
        self.volume.setFixedSize(64,64);self.volume.setNotchesVisible(True)
        self.volume.setProperty('redColor',True)
        volume_box.addWidget(self.volume,0,QtCore.Qt.AlignmentFlag.AlignCenter)
        self.value=QtWidgets.QLabel('25 %');self.value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter);volume_box.addWidget(self.value)
        offset_label=QtWidgets.QLabel('Offset');offset_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        offset_box.addWidget(offset_label);offset_box.addStretch()
        self.offset_box=offset_box
        offset_box.addStretch()
        levels.addLayout(volume_box,1);levels.addLayout(offset_box,1);box.addLayout(levels)
        self.volume.valueChanged.connect(self.volume_changed)
        self.state=QtWidgets.QLabel('Audio de RADIO → A0 · 20/40 kHz');self.state.setWordWrap(True);box.addWidget(self.state)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.sync)

    def volume_changed(self,value):
        self.value.setText(f'{value} %')
        if self.source is not None:self.source.set_volume(value/100)
        self._refresh_generator_status()

    def sync(self):
        owner=self.owner
        input_name=self.input_source.currentText()
        self.frequency.setText(f'{input_name} · {owner.radio_frequency.value():g} kHz → A0')
        if self.source is not None and self.source.error:
            error=self.source.error;self.stop(reason=error);self.state.setText(error)
        elif self.source is not None and not self.source.played:
            self.state.setText('Preparando audio de RADIO…')
        elif self.source is not None:
            self.state.setText(f'RADIO → A0 · {self.source.rate//1000} kHz · '+('recorte' if self.source.clipped_samples else 'en vivo'))
        self._refresh_generator_status()

    def _refresh_generator_status(self):
        if getattr(self.owner,'_central_status_ready',False):self.owner._refresh_status_boxes()

    def radio_changed(self):
        if self.source is None:
            enabled=self.owner.radio_enabled.isChecked()
            rate=self.owner.radio_output_rate.currentData()
            self.state.setText(f'RADIO {"encendida" if enabled else "apagada"} · {rate/1000:g} kHz · A0 detenido')
        error=acquisition_error(self.owner.applied_configuration)
        if self.source is not None and error:
            self.stop(reason=error);self.state.setText(error);return
        if self.source is not None and self.source.input_source=='FILTER' and self.owner.filter_config.source!='RADIO':
            self.stop(reason='FILTER ya no tiene fuente RADIO')
            self.state.setText('Seleccionar RADIO como fuente de FILTER');return
        if self.source is not None and (not self.owner.radio_enabled.isChecked() or self.owner.radio_output_rate.currentData()!=self.source.rate):
            self.stop(reason='RADIO apagada o cambio de FS SALIDA')
        self.sync()

    def input_changed(self,*args):
        if self.source is not None:self.stop(reason='Cambio de entrada IN')
        self.radio_changed()

    def toggle(self):
        owner=self.owner
        if self.source is not None:self.stop();return
        if owner.serial_worker is None or not owner._wav_capable:
            self.state.setText('Conectar Q para enviar RADIO a A0');return
        if owner.output_pending or owner._auto_apply_timer.isActive() or owner._wav_active or owner._wav_preparing or owner.spectral.bode.active:
            self.state.setText('Esperar que la salida esté libre');return
        if not radio_input_supported(owner.applied_configuration):
            self.state.setText('RADIO requiere adquisición de al menos 20 kHz');return
        error=acquisition_error(owner.applied_configuration)
        if error:
            self.state.setText(error);return
        if not tuning_bounds(owner.applied_configuration.actual_rate,owner.radio_bandwidth.currentData(),owner.radio_us.isChecked())[0]<=owner.radio_frequency.value()*1000<=tuning_bounds(owner.applied_configuration.actual_rate,owner.radio_bandwidth.currentData(),owner.radio_us.isChecked())[1]:
            self.state.setText('Sintonía fuera de banda');return
        try:alias_frequency(owner.applied_configuration.actual_rate,owner.radio_frequency.value()*1000,owner.radio_bandwidth.currentData(),owner.radio_us.isChecked())
        except ValueError as exc:
            self.state.setText(str(exc));return
        rate=owner.radio_output_rate.currentData()
        if rate not in (20000,40000):
            self.state.setText('A0 admite 20/40 kHz; 48 kHz requiere otro firmware');return
        item=owner.wav_rate.findData(rate)
        if item<0 or not owner.wav_rate.model().item(item).isEnabled():
            self.state.setText(f'Q no confirmó salida de audio a {rate//1000} kHz');return
        if self.input_source.currentText()=='FILTER' and owner.filter_config.source!='RADIO':
            self.state.setText('Seleccionar RADIO como fuente de FILTER');return
        source_type=HighRateRadioDacSource if owner.applied_configuration.bits==14 and owner.applied_configuration.rate==851063 else RadioDacSource
        source=source_type(self.volume.value()/100,input_source=self.input_source.currentText(),rate=rate)
        if getattr(self,'scan_fade_in',False):
            source.fade_in();self.scan_fade_in=False
        try:
            owner.radio_enabled.setChecked(True)
            owner.serial_worker.set_radio_output_source(source)
            owner.serial_worker.request_wav(1,source,source.rate)
        except queue.Full:
            owner.serial_worker.set_radio_output_source(None);source.close()
            self.state.setText('Salida ocupada; intentar otra vez');return
        self.source=source;owner._wav_active=True;owner._wav_cancelled=False
        self.play.setText('■ Stop');owner._sync_wav_transport();self.timer.start();self.sync()

    def stop(self,reason='Stop solicitado',status=None):
        if self.source is not None:
            record_stop(self.owner,self.source,reason,status)
            self.source.close();self.source=None
            worker=self.owner.serial_worker
            if worker is not None:worker.set_radio_output_source(None)
            self.owner._stop_wav()
        self.timer.stop();self.play.setText('▶ Play');self.state.setText('Audio de RADIO → A0 · 20/40 kHz')
        self._refresh_generator_status()

    def status(self,status):
        if self.source is not None and (int(status.state) in (0,3,4,5) or status.reason):
            message='Radio A0 detenida' if not status.reason and int(status.state) in (0,3) else 'Radio A0 interrumpida: faltó audio' if int(status.state)==4 else f'Radio A0: error {status.reason}'
            self.stop(reason=message,status=status);self.state.setText(message)
            self._refresh_generator_status()
