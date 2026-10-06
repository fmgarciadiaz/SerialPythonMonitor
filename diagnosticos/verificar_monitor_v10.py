#!/usr/bin/env python3
"""Qt/CSV physical test of acquisition controls and real ADC changes."""
import argparse,csv,json,math,os,sys,tempfile,time
from datetime import datetime
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PyQt5 import QtCore,QtWidgets
from monitor.historico.v10.app import SerialMonitorWindow
from transport.unoq_acquisition import Configuration
from transport.unoq_switch import Mode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='1060031107');parser.add_argument('--r4-port',required=True)
    parser.add_argument('--spi-rates',type=int,nargs='+')
    parser.add_argument('--oversampling',action='store_true')
    parser.add_argument('--oversampling-from-fast',action='store_true')
    parser.add_argument('--switch-cycles',type=int,default=2)
    parser.add_argument('--oversampling-rate',type=int,default=12500)
    parser.add_argument('--window',type=int,default=9000)
    parser.add_argument('--stage-seconds',type=float,default=2.5)
    args=parser.parse_args();app=QtWidgets.QApplication([]);app.setStyle('Fusion')
    errors=[];results=[];captures=[]
    stages=[(14,31250,0),(8,10000,0),(8,10000,1),(8,10000,0),(12,25000,0),(10,1000,0),(14,31250,0)]
    if args.spi_rates: stages=[(14,31250,0)]+[(14,rate,0) for rate in args.spi_rates]+[(14,31250,0),(14,31250,1),(14,31250,0)]
    if args.oversampling: stages=[(14,31250,0),(16,1000,0),(16,args.oversampling_rate,0),(16,min(args.oversampling_rate,31250),1),(14,31250,0)]
    if args.oversampling_from_fast: stages=[profile for _ in range(args.switch_cycles) for profile in ((14,62500,0),(16,50000,0))]+[(14,31250,0)]
    with tempfile.TemporaryDirectory(prefix='scope-v10-smoke-') as folder:
        class Window(SerialMonitorWindow):
            total=0;frames=0;last=None;last_index=None
            def _on_worker_error(self,message):errors.append(message);self.close()
            def _acquisition_confirmed(self,bits,rate):
                if self.applied_configuration!=Configuration(bits,rate):self.last=self.last_index=None
                super()._acquisition_confirmed(bits,rate)
            def handle_batch(self,batch):
                config=self.applied_configuration
                for row in batch:
                    t=int(row['Tiempo (us)']);i=int(row['Muestra'])
                    if self.last is not None and (t-self.last)&0xffffffff != config.period:errors.append(f'Timestamp Qt incorrecto: rate={config.rate}, t={t}, prev={self.last}, index={i}')
                    if self.last_index is not None and (i-self.last_index)&0xffffffff != 1:errors.append('Índice Qt incorrecto')
                    if row['ADC_IN']>config.maximum or row['ADC_OUT']>config.maximum:errors.append('Escala ADC Qt incorrecta')
                    if not math.isclose(row['V_IN'],row['ADC_IN']*3.3/config.maximum,abs_tol=1e-12):errors.append('Escala voltios incorrecta')
                    self.last,self.last_index=t,i
                self.total+=len(batch);super().handle_batch(batch)
            def render_frame(self):self.frames+=1;super().render_frame()
            def _create_log_filename(self):
                path=Path(folder)/f'capture_{len(captures)}.csv'
                captures.append((path,self.applied_configuration));return path
        w=Window();w.dial_h_scale.setValue(args.window);w.show()
        assert w.configuration_panel.isVisible()
        w.port_combo.setCurrentIndex(w.port_combo.findData(args.serial));w.r4_combo.setCurrentIndex(w.r4_combo.findData(args.r4_port))
        if w.port_combo.currentData()!=args.serial or w.r4_combo.currentData()!=args.r4_port:raise RuntimeError('Faltan las placas en el panel')
        stage=0;entered=None;baseline=0
        def tick():
            nonlocal stage,entered,baseline
            bits,rate,mode=stages[stage]
            ready=(not w.output_pending and w.serial_worker is not None and
                   w.applied_configuration==Configuration(bits,rate) and getattr(w,'confirmed_mode',None)==mode and w.sample_counter>0)
            if not ready:return
            if entered is None:
                entered=time.monotonic();baseline=w.total
                if not w.recording:w.start_recording()
                print('Qt aplicado:',dict(bits=bits,rate=rate,mode=mode),flush=True)
                if stage==2 and not (args.oversampling or args.oversampling_from_fast):
                    w.grab().save(str(ROOT/('assets/monitor_v10_fast_config.png' if args.spi_rates else 'assets/monitor_v10_config.png')))
                    app.processEvents()
                    w.grab().save(str(ROOT/('assets/monitor_v10_fast.png' if args.spi_rates else 'assets/monitor_v10.png')))
            elif time.monotonic()-entered>=args.stage_seconds:
                results.append(dict(bits=bits,rate=rate,mode=mode,pairs=w.total-baseline,estimated_rate=w.current_fs_hz,render_fps=w.current_fps,visible_samples=w.h_scale))
                if stage==len(stages)-1:timer.stop();w.close();return
                stage+=1;entered=None
                bits,rate,mode=stages[stage]
                w.config_bits_combo.setCurrentIndex(w.config_bits_combo.findData(bits))
                w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(rate))
                w.destination_combo.setCurrentIndex(w.destination_combo.findData(mode))
                if not args.oversampling_from_fast: w.apply_output()
        bits,rate,mode=stages[0]
        w.config_rate_combo.setCurrentIndex(w.config_rate_combo.findData(rate))
        w.connect_serial();timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(50)
        QtCore.QTimer.singleShot(int(1000*(30+len(stages)*(args.stage_seconds+4))),lambda:(errors.append('Timeout Qt'),w.close()))
        app.exec_()
        csv_results=[]
        for path,config in captures:
            n=gaps=indices=scale_errors=0;last=last_index=None
            with path.open() as f:
                for row in csv.DictReader(f):
                    t=int(float(row['Tiempo_us']));i=int(float(row['Muestra']))
                    if last is not None:gaps+=(t-last)&0xffffffff!=config.period
                    if last_index is not None:indices+=(i-last_index)&0xffffffff!=1
                    scale_errors+=not math.isclose(float(row['V_IN']),float(row['ADC_IN'])*3.3/config.maximum,abs_tol=1e-12)
                    last,last_index=t,i;n+=1
            csv_results.append(dict(bits=config.bits,rate=config.rate,rows=n,gaps=gaps,index_gaps=indices,scale_errors=scale_errors))
        report=dict(stages=results,csv=csv_results,errors=errors,total_pairs=w.total,render_calls=w.frames,
                    passed=not errors and len(results)==len(stages) and all(r['rows']>1000 and not (r['gaps'] or r['index_gaps'] or r['scale_errors']) for r in csv_results))
        output=ROOT/'diagnosticos/resultados_usb';output.mkdir(exist_ok=True)
        path=output/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_monitor_v10.json');path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({**report,'errors':errors[:10]},indent=2));print(path);return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
