#!/usr/bin/env python3
"""Offline full-detail raster/GIL experiment; no acquisition or product changes."""
import os
os.environ.setdefault('PYQTGRAPH_QT_LIB','PySide6')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse
import json
import threading
import time
from pathlib import Path
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
import pyqtgraph as pg


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int,default=724000)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    app=QtWidgets.QApplication([])
    x=np.linspace(0,1100,args.samples)
    y=300+70*np.random.default_rng(1).normal(size=args.samples)
    gaps=np.arange(50000,args.samples,100000);y[gaps]=np.nan
    result=dict(samples=args.samples,nan_gaps=len(gaps),width=1100,height=600)
    heartbeat=[];start=time.perf_counter();done=threading.Event()
    def raster():
        try:
            began=time.perf_counter()
            image=QtGui.QImage(1100,600,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(QtCore.Qt.GlobalColor.transparent)
            path=pg.arrayToQPath(x,y,connect='finite',finiteCheck=True)
            result['path_ms']=(time.perf_counter()-began)*1000
            painter=QtGui.QPainter(image)
            try:
                painter.setPen(pg.mkPen('#ffd166',width=1))
                painter.drawPath(path)
            finally:painter.end()
            result['total_ms']=(time.perf_counter()-began)*1000
            result['image_bytes']=image.sizeInBytes()
            result['image_nonempty']=not image.isNull()
        except Exception as exc:result['error']=repr(exc)
        finally:done.set()
    worker=threading.Thread(target=raster)
    def beat():
        heartbeat.append(time.perf_counter()-start)
        if done.is_set():app.quit()
    timer=QtCore.QTimer();timer.timeout.connect(beat);timer.start(10)
    QtCore.QTimer.singleShot(100,worker.start)
    app.exec();worker.join()
    result['heartbeat_count']=len(heartbeat)
    result['heartbeat_max_gap_ms']=max(np.diff([0,*heartbeat]),default=0)*1000
    result['thread_viable']=bool(not result.get('error') and result['heartbeat_max_gap_ms']<100)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return int(bool(result.get('error')))

if __name__=='__main__':raise SystemExit(main())
