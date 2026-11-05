#!/usr/bin/env python3
"""Offline full-detail step/DPR stress; no board connection."""
import os
os.environ['PYQTGRAPH_QT_LIB']='PySide6'
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys,time,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtWidgets
from monitor.v19.temporal_raster import RasterProcess

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--renderer',choices=('path','segments','polyline'),default='path')
    args=p.parse_args();app=QtWidgets.QApplication([])
    worker=RasterProcess();result=None;heartbeat=[];began=time.monotonic();last=began
    try:
        x=np.linspace(0,534000,724000);y=1.65+.1*np.random.default_rng(1).normal(size=len(x))
        options=dict(step=True,gap_cut=True,time_mode=True,dt=160/118,style='Rápido',dpr=2.,renderer=args.renderer)
        worker.submit([(x,y,'#00e5ff')],(0,534000,-.066,3.366),(2200,1200),options,1,None)
        while time.monotonic()-began<12:
            app.processEvents();result=worker.poll();now=time.monotonic();heartbeat.append(now-last);last=now
            if result is not None:break
            time.sleep(.005)
    finally:worker.close()
    report=dict(completed=result is not None,elapsed_s=time.monotonic()-began,
                raster_ms=result['milliseconds'] if result else None,max_heartbeat_ms=max(heartbeat,default=0)*1000)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return 0 if result is not None else 1

if __name__=='__main__':raise SystemExit(main())
