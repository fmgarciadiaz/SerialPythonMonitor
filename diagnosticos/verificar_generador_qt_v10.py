#!/usr/bin/env python3
"""Prueba controles del generador, CSV continuo, STOP y SINGLE usando las placas."""
import csv,json,os,sys,time
from datetime import datetime
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt5 import QtCore,QtWidgets
from monitor.historico.v10.app import SerialMonitorWindow


def main():
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/generador_v10'/('qt_'+stamp);folder.mkdir(parents=True)
    csv_path=folder/'continuo.csv';errors=[];results=[]
    app=QtWidgets.QApplication([]);app.setStyle('Fusion')
    class Window(SerialMonitorWindow):
        total=0;previous=None
        def _on_worker_error(self,text):errors.append(text);self.close()
        def _create_log_filename(self):return csv_path
        def handle_batch(self,batch):
            for row in batch:
                current=int(row['Muestra']),int(row['Tiempo (us)'])
                if self.previous and ((current[0]-self.previous[0])&0xffffffff!=1 or (current[1]-self.previous[1])&0xffffffff!=32):errors.append('Discontinuidad Qt')
                self.previous=current
            self.total+=len(batch);super().handle_batch(batch)
    w=Window();w.show();w.connect_serial()
    stage=0;entered=None;started=time.monotonic()
    def tick():
        nonlocal stage,entered
        if errors:return
        if time.monotonic()-started>45:errors.append('Timeout Qt generador');w.close();return
        if not w.serial_worker or w.output_pending or not w.sample_counter:return
        if entered is None:
            if 'Activo' not in w.generator_status.text():return
            entered=time.monotonic();w.start_recording();w.generator_wave.setCurrentIndex(1);w.generator_frequency.setValue(10)
            return
        if time.monotonic()-entered<3:return
        if w._generator_requested is not None:return
        if not w.recording:errors.append('El cambio de generador cerró el CSV');w.close();return
        results.append({'stage':stage,'pairs':w.total,'status':w.generator_status.text(),'csv_open':w.recording})
        if stage==0:
            if w._generator_active.wave!=1 or w._generator_active.frequency!=10000:return
            w.grab().save(str(ROOT/'assets/monitor_v10_generador.png'))
            w.run_stop_btn.click();assert not w.is_running
            w.generator_wave.setCurrentIndex(2)
        elif stage==1:
            if w._generator_active.wave!=2:return
            assert not w.is_running
            w.run_stop_btn.click();w.generator_wave.setCurrentIndex(0)
            w.trigger_source_combo.setCurrentText('V_OUT');w.arm_single_shot()
        elif stage==2:
            if w.single_shot_armed or w.is_running:errors.append('SINGLE no congeló la captura')
            w.generator_wave.setCurrentIndex(0);w.generator_frequency.setValue(2.5)
        else:
            timer.stop();w.stop_recording();w.close();return
        stage+=1;entered=time.monotonic()
    def checked_tick():
        try:tick()
        except Exception as exc:
            errors.append(repr(exc));timer.stop();w.close()
    timer=QtCore.QTimer();timer.timeout.connect(checked_tick);timer.start(50)
    app.exec_();timer.stop();w.stop_input()
    count=gaps=0;previous=None
    if csv_path.exists():
        with csv_path.open() as file:
            for row in csv.DictReader(file):
                current=int(float(row['Muestra'])),int(float(row['Tiempo_us']))
                if previous and ((current[0]-previous[0])&0xffffffff!=1 or (current[1]-previous[1])&0xffffffff!=32):gaps+=1
                previous=current;count+=1
    if gaps or count<1000:errors.append(f'CSV: {count} filas, {gaps} discontinuidades')
    report={'stages':results,'errors':errors,'csv_rows':count,'csv_gaps':gaps,'passed':not errors,
            'csv':str(csv_path.relative_to(ROOT))}
    output=ROOT/'diagnosticos/resultados_usb'/(stamp+'_generador_qt_v10.json')
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(output)
    if errors:raise RuntimeError(errors)

if __name__=='__main__':main()
