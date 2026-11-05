"""Compare V19/V20 temporal preparation and point drawing without opening Q."""
import importlib,json,os,statistics,sys,time
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtWidgets


def main():
    qt=QtWidgets.QApplication([]);rows=[]
    n=3_720_930;x=np.arange(n,dtype=float)*1e6/1_860_465
    y=1.65+.2*np.sin(np.arange(n)*.02)
    for version in ('v19','v20'):
        mod=importlib.import_module('monitor.'+version+'.app')
        with patch.object(mod,'usb_devices',return_value=[]):w=mod.SerialMonitorWindow()
        try:
            w.render_timer.stop();w.show();qt.processEvents()
            w.known_columns=['CH1'];w.selected_columns={'CH1':True};w._update_curve_items(['CH1'])
            w.current_dt_us=1e6/1_860_465;w.current_fs_hz=1_860_465
            w.sample_counter=n;w.sample_numbers.resize(n+1000);w.sample_numbers.extend(np.arange(n))
            for name,values in (('Tiempo (us)',x),('CH1',y)):
                w.series[name].resize(n+1000);w.series[name].extend(values)
            w.h_scale=n;w.h_pos=0;w.x_axis_time_mode=True;w.trigger_enabled=False
            w.detail_slider.setValue(50);w.scope_cursors.buttons[0].setChecked(False)
            times=[];counts=[]
            for _ in range(10):
                began=time.perf_counter();w.render_frame();qt.processEvents()
                times.append((time.perf_counter()-began)*1000)
                counts.append(len(w.line_items['CH1'].getData()[0]))
            rows.append(dict(version=version,samples=n,detail=50,frame_ms=times,
                             median_ms=statistics.median(times),drawn_points=counts))
        finally:w.close();qt.processEvents()
    output=ROOT/'diagnosticos/resultados_v20/recovery_review_20261103'
    output.mkdir(exist_ok=True)
    report=dict(scope='Offline identical synthetic 2-second RF, Qt offscreen; not physical FPS',cases=rows)
    (output/'temporal_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
