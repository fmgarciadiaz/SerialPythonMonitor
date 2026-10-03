#!/usr/bin/env python3
"""Physical Bode check through V10; save raw CSV and preserve board settings."""
import csv
import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5 import QtCore, QtWidgets
from monitor.v10.app import SerialMonitorWindow
from transport.unoq_usb import Connection, usb_devices
from transport.unoq_config_receiver import OutputReceiver
from monitor.v10.bode_calibration import CALIBRATION_PATH


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',type=float,default=2)
    parser.add_argument('--end',type=float,default=100)
    parser.add_argument('--points-per-decade',type=int,default=4)
    parser.add_argument('--cycles',type=int,default=8)
    parser.add_argument('--settle-ms',type=int,default=300)
    parser.add_argument('--calibration',action='store_true',help='Guardar referencia; requiere A0 conectado directamente a A2 y A3.')
    args=parser.parse_args()
    serial=usb_devices()[0]
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=ROOT/'capturas/bode_v10'/stamp; folder.mkdir(parents=True)
    report={'passed':False,'serial':serial,'errors':[],'curves':[]}
    errors=report['errors']
    with Connection(serial) as connection:
        receiver=OutputReceiver(connection,lambda records:None)
        before=receiver.generator().active
        if receiver.decoder.config is None:
            raise RuntimeError('No hay muestras SPI; no se cambia el destino para este ensayo.')
        config=receiver.config
        receiver.close()
    report['before']={'generator':asdict(before),'acquisition':asdict(config)}
    csv_path=folder/'muestras.csv'
    app=QtWidgets.QApplication([]);app.setStyle('Fusion')
    class Window(SerialMonitorWindow):
        previous=None
        pairs=0
        def _create_log_filename(self):return csv_path
        def _on_worker_error(self,text):
            errors.append(text);self.close()
        def handle_batch(self,batch):
            for sample in batch:
                current=int(sample['Muestra']),int(sample['Tiempo (us)'])
                if self.previous and (((current[0]-self.previous[0])&0xffffffff)!=1 or
                    ((current[1]-self.previous[1])&0xffffffff)!=config.period):
                    errors.append('Discontinuidad en muestras Qt')
                self.previous=current
            self.pairs+=len(batch)
            super().handle_batch(batch)
    w=Window()
    w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(config.bits))
    w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(config.rate))
    w._auto_apply_timer.stop()
    w.show();w.connect_serial()
    stage=0; began=time.monotonic(); finish=None
    def tick():
        nonlocal stage, finish
        if errors:
            timer.stop();w.close();return
        if time.monotonic()-began>75:
            errors.append('Timeout de validación Bode');timer.stop();w.close();return
        if stage==0:
            if not w.sample_counter or w.output_pending or not w._generator_state_known: return
            if w.applied_configuration!=config or w._generator_active!=before:
                errors.append('El estado inicial no coincide con el snapshot');return
            w.start_recording()
            b=w.spectral.bode
            b.calibrated.setChecked(False)
            b.start.setValue(args.start);b.end.setValue(args.end);b.points.setValue(args.points_per_decade);b.settle.setValue(args.settle_ms);b.cycles.setValue(args.cycles)
            w.spectral.set_mode(3)
            if not b.active: errors.append(b.status.text());return
            report['requested']={'start_hz':args.start,'end_hz':args.end,'points_per_decade':args.points_per_decade,'points':len(b.frequencies),'cycles':b.cycles.value(),'settle_ms':b.settle.value()}
            stage=1
        elif stage==1:
            b=w.spectral.bode
            if b.active:return
            if not b.status.text().startswith('Barrido terminado'):
                errors.append(b.status.text());return
            report['curves']=[{'frequency_hz':float(f),'gain_db':float(g) if math.isfinite(g) else None,'gain_zero':bool(g==float('-inf')),'phase_deg':float(p) if math.isfinite(p) else None} for f,g,p in b.result]
            if len(b.result)!=report['requested']['points']:errors.append('No se recorrieron todos los puntos');return
            report['invalid_points']=b.invalid_points
            if not w.recording:errors.append('El barrido cerró el CSV');return
            w.grab().save(str(folder/'bode.png'))
            with (folder/'bode.csv').open('w',newline='') as file:
                writer=csv.writer(file);writer.writerow(['Frecuencia_Hz','Ganancia_dB','Fase_grados']);writer.writerows(b.result)
            stage=2;finish=time.monotonic()
        elif stage==2:
            if w._generator_requested is not None:return
            if w._generator_active!=before:
                errors.append('El generador no se restauró exactamente');return
            if time.monotonic()-finish<1:return
            w.stop_recording();timer.stop();w.close()
    def checked_tick():
        try:tick()
        except Exception as exc:
            errors.append(repr(exc));timer.stop();w.close()
    timer=QtCore.QTimer();timer.timeout.connect(checked_tick);timer.start(50)
    app.exec_();timer.stop();w.stop_input()
    report['pairs']=w.pairs
    try:
        with Connection(serial) as connection:
            receiver=OutputReceiver(connection,lambda records:None)
            after=receiver.generator().active
            if after!=before: receiver.generator(before)
            # The initial profile was retained throughout the Qt capture.
            report['after']={'generator':asdict(receiver.generator().active),'acquisition':asdict(receiver.config)}
            receiver.close()
        if report['after']!=report['before']:errors.append('Estado final distinto del inicial')
    except Exception as exc:errors.append(f'Restauración/consulta final: {exc}')
    rows=0; gaps=0;previous=None
    if csv_path.exists():
        with csv_path.open() as file:
            for row in csv.DictReader(file):
                current=int(float(row['Muestra'])),int(float(row['Tiempo_us']))
                if previous and (((current[0]-previous[0])&0xffffffff)!=1 or ((current[1]-previous[1])&0xffffffff)!=config.period):gaps+=1
                previous=current;rows+=1
    report['csv_rows']=rows;report['csv_gaps']=gaps
    if rows<1000 or gaps:errors.append(f'CSV inválido: {rows} filas / {gaps} saltos')
    report['passed']=not errors and len(report['curves'])==report.get('requested',{}).get('points')
    report['capture_folder']=str(folder.relative_to(ROOT))
    if args.calibration:
        valid = report['passed'] and all(p['gain_db'] is not None and p['phase_deg'] is not None for p in report['curves'])
        report['calibration_saved'] = valid
        if valid:
            reference = {'acquisition':asdict(config),'points':[[p['frequency_hz'],p['gain_db'],p['phase_deg']] for p in report['curves']],
                         'capture_folder':report['capture_folder'],'created':stamp}
            CALIBRATION_PATH.parent.mkdir(parents=True,exist_ok=True)
            CALIBRATION_PATH.write_text(json.dumps(reference,indent=2)+'\n')
        else:
            errors.append('Calibración no guardada: faltan puntos válidos o falló la adquisición.')
            report['passed'] = False
    output=ROOT/'diagnosticos/resultados_usb'/f'{stamp}_bode_qt_v10.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));print(output)
    if not report['passed']:raise RuntimeError(errors)


if __name__=='__main__':main()
