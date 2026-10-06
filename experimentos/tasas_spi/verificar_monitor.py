#!/usr/bin/env python3
"""Offscreen full V11 UI with real USB, V/t/FFT/heatmap and CSV at 100 kHz."""
import sys,time,json,csv
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PyQt5 import QtCore,QtWidgets
from monitor.historico.v11.app import SerialMonitorWindow

def main():
    app=QtWidgets.QApplication([]);w=SerialMonitorWindow();report={'segments':[],'errors':[]}
    path=ROOT/'experimentos/tasas_spi/resultados'/('monitor_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    def error(message):report['errors'].append(message)
    # Offscreen message boxes cannot be dismissed; record them instead.
    QtWidgets.QMessageBox.critical=lambda owner,title,message: error(f'{title}: {message}')
    QtWidgets.QMessageBox.warning=lambda owner,title,message: error(f'{title}: {message}')
    w.show();app.processEvents()
    if w.port_combo.findData('1060031107')<0:w.port_combo.addItem('UNO Q test','1060031107')
    w.port_combo.setCurrentIndex(w.port_combo.findData('1060031107'))
    w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(100000))
    w.connect_serial();w.serial_worker.error_occurred.connect(error)
    def wait(seconds):
        loop=QtCore.QEventLoop()
        QtCore.QTimer.singleShot(round(seconds*1000),loop.quit)
        loop.exec_()
    try:
        wait(3)
        if report['errors'] or w.applied_configuration.rate!=100000:raise RuntimeError('No confirmed 100 kHz profile')
        for mode,name in ((0,'V/t'),(1,'FFT'),(2,'Heatmap')):
            w.spectral.set_mode(mode);start_count=w.sample_counter;start=time.monotonic()
            if mode==0:w.start_recording()
            wait(30 if mode==2 else 7)
            if mode==0:
                w.stop_recording();report['csv']=w.record_filename
            elapsed=time.monotonic()-start;count=w.sample_counter-start_count
            row={'mode':name,'pairs':count,'seconds':elapsed,'pairs_per_second':count/elapsed,'passed':count/elapsed>95000}
            report['segments'].append(row);print(json.dumps(row),flush=True)
            if report['errors'] or not row['passed']:raise RuntimeError('UI sample throughput or receiver error')
    except Exception as exc:report['errors'].append(str(exc))
    finally:w.stop_input();w.close();app.processEvents()
    if report.get('csv'):
        previous=None;rows=0;gaps=0
        with Path(report['csv']).open() as f:
            for record in csv.DictReader(f):
                index=int(float(record['Muestra']));timestamp=int(float(record['Tiempo_us']))
                if previous is not None:gaps+=int(((index-previous[0])&0xffffffff)!=1 or ((timestamp-previous[1])&0xffffffff)!=10)
                previous=(index,timestamp);rows+=1
        report['csv_validation']={'rows':rows,'gaps':gaps,'passed':rows>500000 and gaps==0}
        if not report['csv_validation']['passed']:report['errors'].append('CSV continuity or count')
    report['passed']=not report['errors'] and len(report['segments'])==3
    path.write_text(json.dumps(report,indent=2)+'\n');print(path,flush=True)
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
