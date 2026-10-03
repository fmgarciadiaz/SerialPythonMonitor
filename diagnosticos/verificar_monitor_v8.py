#!/usr/bin/env python3
"""Smoke físico de V8: gráfico Qt, muestras, CSV y reconexión (offscreen)."""
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PyQt5 import QtCore,QtWidgets
from monitor.historico.v8.app import SerialMonitorWindow


def main():
    app=QtWidgets.QApplication([])
    app.setStyle('Fusion')
    errors=[]
    with tempfile.TemporaryDirectory(prefix='scope-v8-smoke-') as folder:
        class Window(SerialMonitorWindow):
            total=0
            frames=0
            last=None
            def _on_worker_error(self,message):
                errors.append(message)
                self.stop_input()
            def handle_batch(self,batch):
                for row in batch:
                    timestamp=int(row['Tiempo (us)'])
                    if self.last is not None and (timestamp-self.last)&0xffffffff !=32:
                        errors.append('Hueco en muestras entregadas a Qt')
                    self.last=timestamp
                self.total+=len(batch)
                super().handle_batch(batch)
            def render_frame(self):
                self.frames+=1
                super().render_frame()
            def _create_log_filename(self):
                return Path(folder)/'capture.csv'
        window=Window()
        window.show()
        window.connect_serial()
        QtCore.QTimer.singleShot(1000,window.start_recording)
        first={}
        def reconnect():
            first.update(pairs=window.total,frames=window.frames,fs=window.current_fs_hz)
            window.stop_input()
            def connect_again():
                window.last=None
                first['pairs']=window.total
                window.connect_serial()
            QtCore.QTimer.singleShot(500,connect_again)
        QtCore.QTimer.singleShot(10000,reconnect)
        QtCore.QTimer.singleShot(16000,window.close)
        app.exec_()
        capture=Path(folder)/'capture.csv'
        rows=0;last=None;csv_gaps=0
        if capture.exists():
            with capture.open() as f:
                for row in csv.DictReader(f):
                    t=int(float(row['Tiempo_us']))
                    if last is not None and (t-last)&0xffffffff !=32:
                        csv_gaps+=1
                    last=t;rows+=1
        report=dict(first_session=first,total_pairs=window.total,render_calls=window.frames,
                    csv_rows=rows,csv_gaps=csv_gaps,errors=errors,
                    reconnect_pairs=window.total-first.get('pairs',window.total))
        report['pass']=bool(not errors and not csv_gaps and rows>100000 and
                            first.get('pairs',0)>200000 and report['reconnect_pairs']>100000
                            and first.get('fs')==31250 and window.frames>100)
        output=ROOT/'diagnosticos/resultados_usb'
        output.mkdir(exist_ok=True)
        path=output/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_monitor.json')
        path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
        print(path)
        return 0 if report['pass'] else 1


if __name__=='__main__':
    raise SystemExit(main())
