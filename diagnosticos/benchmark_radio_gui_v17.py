"""Paced offline GUI/RADIO load; no board access or physical acceptance."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys,time,json,threading
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt6 import QtCore,QtWidgets
from monitor.v17.app import SerialMonitorWindow,OutputWorker
from monitor.v17.numeric_batch import NumericBatch,SampleClock
from monitor.v17.receiver.unoq_acquisition import Configuration
from monitor.v17.receiver.unoq_switch import Mode


def main():
    app=QtWidgets.QApplication([])
    with patch('monitor.v17.app.usb_devices',return_value=[]):w=SerialMonitorWindow()
    config=Configuration(8,1403508);w._acquisition_confirmed(config.bits,config.rate)
    w.filter_source.setCurrentText('RADIO');w.radio_enabled.setChecked(True)
    w.spectral.mode=1;w.spectral.channels[0].setCurrentText('RADIO')
    w.spectral.channels[1].setCurrentText('Ninguno');w.spectral.size.setCurrentText('1024')
    w.show()
    worker=OutputWorker('offline',Mode.SPI);w.serial_worker=worker
    worker.batch_ready.connect(lambda b:w._deliver_worker_batch(worker,b),QtCore.Qt.ConnectionType.QueuedConnection)
    report={'scope':'Offline paced RF 1.4035 MHz, RADIO40/FILTER/FFT GUI; no physical acceptance','errors':[]}
    done=threading.Event()
    def produce():
        count=round(config.actual_rate*.02);clock=SampleClock(160000000);start=time.monotonic()
        batches=0
        try:
            while time.monotonic()-start<15:
                indices=np.arange(batches*count,(batches+1)*count,dtype=float)
                t=indices/config.actual_rate
                rf=1.65+(1+.4*np.sin(2*np.pi*1000*t))*(np.cos(2*np.pi*20000*t)+np.cos(2*np.pi*40000*t))/6
                raw=np.column_stack(((indices*114)%2**32,np.rint(rf*255/3.3),np.zeros(count),indices))
                worker.publish_batch(NumericBatch(raw,255,clock,1));batches+=1
                pause=start+batches*.02-time.monotonic()
                if pause>0:time.sleep(pause)
        except Exception as exc:report['errors'].append(str(exc))
        report['produced_batches']=batches;done.set()
    thread=threading.Thread(target=produce);thread.start()
    timer=QtCore.QTimer();timer.setInterval(100)
    def finish():
        if done.is_set() and worker.pending_batches==0:app.quit()
    timer.timeout.connect(finish);timer.start();app.exec();thread.join();timer.stop()
    report.update(pending_peak=worker.pending_batches_peak,queue_delay_max_ms=w.batch_queue_delay_max_ms,
        rf_history_capacity=w.sample_numbers.maxlen,
        processing_peak_ms=getattr(w,'batch_processing_peak_ms',0),processed_batches=getattr(w,'batch_processing_count',0),
        processing_mean_ms=getattr(w,'batch_processing_total_ms',0)/max(1,getattr(w,'batch_processing_count',0)))
    report['ok']=not report['errors'] and report['processed_batches']==report['produced_batches']
    w.serial_worker=None;w.close()
    path=ROOT/'diagnosticos/resultados_v17/radio_gui_offline_15s.json'
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
