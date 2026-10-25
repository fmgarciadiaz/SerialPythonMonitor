"""Comparación ABBA de publicación de acordes MIDI en Qt; sin MIDI/Q físico."""
import importlib.util,sys,json,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PyQt6 import QtWidgets
from monitor.historico.v16.fm_panel import FMPanel

class RecordingSource:
    def __init__(self):self.started=0;self.wait=0;self.parameters=None
    def observe_midi_batch(self,messages):pass
    def update(self,p):
        self.wait=(time.perf_counter_ns()-self.started)/1000;self.parameters=p

def trial(cls,app):
    widget=QtWidgets.QWidget();QtWidgets.QGridLayout(widget)
    owner=SimpleNamespace(generator_panel=widget,generator_mode=QtWidgets.QComboBox(),
        generator_status=QtWidgets.QLabel(),serial_worker=SimpleNamespace(request_wav_levels=lambda *args:None))
    panel=cls(owner);panel.show();app.processEvents()
    panel.midi_input.blockSignals(True);panel.midi_input.addItem('test');panel.midi_input.setCurrentIndex(1);panel.midi_input.blockSignals(False)
    source=RecordingSource();panel.source=source
    state={};panel.midi=SimpleNamespace(iter_pending=lambda:iter(state['messages']),close=lambda:None)
    waits=[];total=[];parameters=[]
    try:
        for i in range(350):
            messages=[SimpleNamespace(type='control_change',control=64,value=0)]
            messages += [SimpleNamespace(type='note_off',note=n,velocity=0) for n,_ in panel.notes]
            messages += [SimpleNamespace(type='note_on',note=48+i%3+j,velocity=70+j*5) for j in (0,4,7)]
            messages += [SimpleNamespace(type='control_change',control=64,value=127 if i%3==0 else 0),
                         SimpleNamespace(type='control_change',control=1,value=i%127),
                         SimpleNamespace(type='control_change',control=7,value=64+i%20)]
            state['messages']=messages;source.started=time.perf_counter_ns();panel.poll_midi()
            elapsed=(time.perf_counter_ns()-source.started)/1000
            if i>=50:waits.append(source.wait);total.append(elapsed)
            parameters.append(source.parameters)
            if i%10==0:app.processEvents()
        return parameters,dict(publication_median_us=float(np.median(waits)),publication_p95_us=float(np.percentile(waits,95)),poll_median_us=float(np.median(total)))
    finally:panel.source=None;panel.close();panel.deleteLater();widget.deleteLater();app.processEvents()

def main():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    spec=importlib.util.spec_from_file_location('midi_publish_reference','respaldos/synth/20261010_midi_publish/fm_panel.py')
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    reference=None;rows=[]
    for variant in ('before','after','after','before'):
        parameters,metrics=trial(old.FMPanel if variant=='before' else FMPanel,app)
        if reference is None:reference=parameters
        else:assert parameters==reference
        rows.append(dict(variant=variant,parameters_exact=True,**metrics))
    output=Path('diagnosticos/resultados_piano/eficiencia_v16/20261010_midi_publish.json')
    output.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
