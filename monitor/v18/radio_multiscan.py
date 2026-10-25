"""Multirate RF hypotheses and GUI-owned acquisition transaction."""
import time
import numpy as np
from PyQt6 import QtCore
from monitor.v18.radio_scan import SCAN_SIZE,SCAN_BLOCKS,scan_carriers
from monitor.v18.radio_tuning import alias_frequency
from monitor.v18.receiver.unoq_acquisition import Configuration,RATES


def folded(frequency,rate):return abs((frequency+rate/2)%rate-rate/2)


def scan_profiles(original):
    candidates=[]
    for rate in RATES:
        try:config=Configuration(original.bits,rate)
        except ValueError:continue
        if config.channels!=original.channels or config==original or config.actual_rate<20000:continue
        if config._native and (config._native.get('internal_only') or config._native.get('integration_pending')):continue
        candidates.append(config)
    # The ADC8 high-rate scan must stay on its SPI38/40 FIFO profiles.
    # Switching to the legacy 143-tick normal-scheduler profile lost a node
    # and closed the relay during an actual US scan from 1.818 MS/s.
    fast8={(88,3488),(100,3456),(114,3456)}
    if original.bits==8 and original.channels==1 and (original.period,original.node_pairs) in fast8:
        candidates=[c for c in candidates if (c.period,c.node_pairs) in fast8]
    candidates.sort(key=lambda c:abs(c.actual_rate-original.actual_rate))
    return [original,candidates[0],candidates[-1]] if len(candidates)>=2 else []


def estimate_rf(scans,base_rate,bandwidth):
    """Keep every supported hypothesis; never turn ambiguity into certainty."""
    if len(scans)<2:return []
    rate,peaks=scans[0];results=[]
    for peak in peaks:
        hypotheses=[]
        for rf in (peak['frequency'],base_rate-peak['frequency']):
            try:alias_frequency(base_rate,rf,bandwidth,True)
            except ValueError:continue
            support=[]
            for fs,other in scans[1:]:
                predicted=folded(rf,fs)
                if not bandwidth/2<predicted<fs/2-bandwidth/2:continue
                tolerance=max(base_rate,fs)/SCAN_SIZE*2+rf*100e-6
                matches=[p for p in other if abs(p['frequency']-predicted)<=tolerance]
                if not matches:break
                support.append(min(matches,key=lambda p:abs(p['frequency']-predicted)))
            else:
                if support:hypotheses.append((rf,len(support)+1))
        for rf,count in hypotheses:
            results.append(dict(peak,frequency=rf,alias_frequency=peak['frequency'],
                confidence='ambigua' if len(hypotheses)>1 else 'RF estimada',profiles=count))
    return sorted(results,key=lambda p:p['frequency'])


class MultirateScan(QtCore.QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.active=False;self.error=None
        self.timer=QtCore.QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.tick)

    def start(self):
        o=self.owner
        if self.active:
            self.error='Scan cancelado'
            if not self.restoring:self.restore()
            return
        if o.serial_worker is None or o.output_pending or o.recording or o.spectral.bode.active or o._wav_active or o._wav_preparing:
            o.radio_status.setText('Scan US · detener A0/registro/Bode y esperar adquisición libre.');return
        self.original=o.applied_configuration;self.frequency=o.radio_frequency.value();self.play=o.radio_enabled.isChecked()
        self.width=o.radio_bandwidth.currentData();self.threshold=o.radio_scan_threshold.currentData();self.persistence=3 if o.radio_scan_strict.isChecked() else 2
        profiles=scan_profiles(self.original)
        if not profiles:
            o.radio_status.setText('Scan US · faltan dos perfiles auxiliares con los mismos bits/canales.');return
        self.configs=profiles;self.scans=[];self.index=0;self.error=None;self.restoring=False
        self.future=None;self.active=True;o._auto_apply_timer.stop();o._set_radio_scan_playback(False)
        self.widgets=[o.radio_us,o.radio_bandwidth,o.radio_frequency,o.radio_frequency_dial,o.config_bits_combo,o.config_rate_combo,o.destination_combo,o.radio_enabled,o.generator_mode,o.radio_output_panel,o.radio_output_rate]
        self.enabled=[w.isEnabled() for w in self.widgets]
        o.radio_scan_button.setEnabled(True)
        o.radio_scan_button.setToolTip('Cancelar Scan US y restaurar FS original')
        for w in self.widgets:w.setEnabled(False)
        self.request(self.original);self.timer.start()

    def request(self,config):
        o=self.owner;self.target=config;self.deadline=time.monotonic()+20;self.ready=False
        if o.applied_configuration!=config:
            o.serial_worker.request_output(o.destination_combo.currentData(),o.r4_combo.currentData(),config)
        else:self.mark_ready()

    def mark_ready(self):
        self.ready=True;self.start_sample=self.owner.sample_counter;self.deadline=time.monotonic()+15

    def tick(self):
        o=self.owner
        try:
            if o.serial_worker is None:raise RuntimeError('Conexión interrumpida; verificar restauración del Q')
            if time.monotonic()>self.deadline:raise TimeoutError('Tiempo de espera agotado')
            if not self.ready:
                if o.applied_configuration==self.target and not o.output_pending:self.mark_ready()
                return
            if self.restoring:
                if o.sample_counter-self.start_sample<max(10000,int(self.original.actual_rate*.1)):return
                self.finish();return
            count=SCAN_SIZE*SCAN_BLOCKS
            o.radio_status.setText(f'Scan US · perfil {self.index+1}/3 · {self.target.actual_rate/1000:.3f} kHz')
            if o.sample_counter-self.start_sample<count+max(10000,int(self.target.actual_rate*.1)):return
            if self.future is None:
                times=o.series['Tiempo (us)'][-count:]
                if len(times)!=count or np.any(abs(np.diff(times)-self.target.dt_us)>.01):raise ValueError('Captura RF discontinua')
                values=o.series['CH1'][-count:]
                self.future=o._radio_scan_executor.submit(scan_carriers,values,self.target.actual_rate,self.threshold,self.persistence,self.width)
                return
            if not self.future.done():return
            self.scans.append((self.target.actual_rate,self.future.result()));self.future=None;self.index+=1
            if self.index==len(self.configs):self.restore()
            else:self.request(self.configs[self.index])
        except Exception as exc:
            if self.restoring:
                self.error=f'Restauración no confirmada: {exc}';self.finish()
            else:self.error=str(exc);self.restore()

    future=None

    def restore(self):
        self.restoring=True
        if self.owner.serial_worker is None:self.finish();return
        self.request(self.original)

    def finish(self):
        o=self.owner;self.timer.stop();self.active=False;self.future=None
        for widget,enabled in zip(self.widgets,self.enabled):widget.setEnabled(enabled)
        restored=o.applied_configuration==self.original and o.serial_worker is not None
        if restored:
            with QtCore.QSignalBlocker(o.radio_frequency):o.radio_frequency.setValue(self.frequency)
            o._sync_radio_dials()
            o._set_radio_scan_playback(self.play)
        if self.error or not restored:
            o.radio_status.setText(f'Scan US falló · {self.error or "restauración no confirmada"}');o._finish_radio_scan_a0(False);return
        peaks=estimate_rf(self.scans,self.original.actual_rate,self.width)
        o._publish_radio_scan(peaks)
        o.radio_status.setText(f'Scan US · {len(peaks)} hipótesis RF · FS original restaurada')
        o._finish_radio_scan_a0(True)
