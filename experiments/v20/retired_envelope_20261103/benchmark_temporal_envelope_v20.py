"""Offline comparison of dense points and display-only extrema. Never opens Q."""
import json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
from monitor.v20.temporal_raster import paint_traces

def main():
    qt=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    rows=[]
    for n in (100000,3720930):
        x=np.arange(n,dtype=float);y=np.sin(x*.013);y[n//2:n//2+200]=np.nan;y[42]=1.8
        for env in (False,True):
            times=[]
            for _ in range(3):
                im=QtGui.QImage(2500,600,QtGui.QImage.Format.Format_ARGB32_Premultiplied);im.fill(QtCore.Qt.GlobalColor.transparent)
                opts=dict(step=True,gap_cut=True,time_mode=False,dt=1,style='Rápido',dpr=1,envelope=env)
                start=time.perf_counter();used=paint_traces(im,[(x,y,'#ffe080')],(0,n,-2,2),opts);times.append((time.perf_counter()-start)*1000)
            rows.append(dict(samples=n,envelope_requested=env,envelope_used=used,milliseconds=times))
    out=ROOT/'diagnosticos/resultados_v20/temporal_envelope_benchmark_20261102';out.mkdir(exist_ok=True)
    (out/'report.json').write_text(json.dumps(dict(private=True,promoted=False,size=[2500,600],scope='Local QImage worker painter only; excludes capture copies, IPC and visible FPS',cases=rows),indent=2)+'\n')
    print(json.dumps(rows));qt.quit()
if __name__=='__main__':main()
