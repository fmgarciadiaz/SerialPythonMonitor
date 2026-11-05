#!/usr/bin/env python3
"""Offline candidates only: all points retained; compare exact output to V20."""
import os
os.environ.setdefault('PYQTGRAPH_QT_LIB','PySide6')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
import pyqtgraph as pg
from pyqtgraph.Qt import compat
from pyqtgraph.graphicsItems.PlotCurveItem import arrayToLineSegments
from monitor.v20.temporal_raster import paint_traces,prepare_vertices


def candidate(image,traces,rect,options,kind):
    if kind=='baseline':return paint_traces(image,traces,rect,options)
    xmin,xmax,ymin,ymax=rect;painter=QtGui.QPainter(image)
    try:
        painter.setClipRect(0,0,image.width(),image.height())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing,options['style']=='Suave')
        if kind=='source':painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        for x,y,color in traces:
            x,y=prepare_vertices(x,y,options['step'],options['gap_cut'],options['time_mode'],options['dt'])
            pen=pg.mkPen(color,width=(2 if options['style']=='Intenso' else 1)*options['dpr']);pen.setCosmetic(True);painter.setPen(pen)
            xp=(np.asarray(x)-xmin)*(image.width()/(xmax-xmin));yp=(ymax-np.asarray(y))*(image.height()/(ymax-ymin))
            if kind=='integer':
                valid=np.isfinite(xp)&np.isfinite(yp);edges=valid[:-1]&valid[1:]
                coords=np.column_stack((xp[:-1][edges],yp[:-1][edges],xp[1:][edges],yp[1:][edges]))
                if np.any(abs(coords)>100000000):raise ValueError('Integer experiment range exceeded')
                coords=np.ascontiguousarray(np.floor(coords+.5),dtype=np.int32)
                if len(coords):painter.drawLines(compat.wrapinstance(coords.ctypes.data,QtCore.QLine),len(coords))
            elif kind.startswith('chunk'):
                block=int(kind[5:])
                for begin in range(0,len(xp)-1,block):
                    end=min(len(xp),begin+block+1)
                    lines=arrayToLineSegments(xp[begin:end],yp[begin:end],'finite',True)
                    painter.drawLines(*lines.drawargs())
            else:painter.drawLines(*arrayToLineSegments(xp,yp,'finite',True).drawargs())
    finally:painter.end()


def render(traces,rect,opts,kind,size):
    image=QtGui.QImage(*size,QtGui.QImage.Format.Format_ARGB32_Premultiplied);image.fill(QtCore.Qt.GlobalColor.transparent)
    start=time.perf_counter();candidate(image,traces,rect,opts,kind);elapsed=(time.perf_counter()-start)*1000
    pixels=np.frombuffer(image.constBits(),np.uint8,count=image.sizeInBytes()).reshape(size[1],size[0],4).copy()
    return pixels,elapsed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--dense',type=int,default=3720930);p.add_argument('--repeat',type=int,default=3);args=p.parse_args()
    if args.output.exists():p.error('New report required')
    app=QtWidgets.QApplication([]);rng=np.random.default_rng(817);rows=[];kinds=['baseline','chunk4096','chunk65536','source','integer']
    # Sparse/subpixel, finite breaks, clipped values, step/line, style and DPR.
    for style in ('Rápido','Intenso','Suave'):
        for step in (False,True):
            for dpr in (1,2):
                x=np.linspace(-.2,2.2,4001);y=1.65+.24*rng.normal(size=len(x));y[100:105]=np.nan;y[150]=np.inf;y[1100:1110]+=10
                opts=dict(step=step,gap_cut=True,time_mode=False,dt=1.,style=style,dpr=dpr)
                traces=[(x,y,'#00e5ff'),(x,3.3-y,'#ffd166')];rect=(0,2,0,3.3);size=(480*dpr,240*dpr)
                reference,_=render(traces,rect,opts,'baseline',size)
                for kind in kinds[1:]:
                    pixels,ms=render(traces,rect,opts,kind,size)
                    rows.append(dict(phase='quality',kind=kind,style=style,step=step,dpr=dpr,ms=ms,different_pixels=int(np.count_nonzero(np.any(pixels!=reference,axis=2)))))
    accepted=[kind for kind in kinds if all(r['different_pixels']==0 for r in rows if r['kind']==kind)]
    x=np.linspace(0,2,args.dense);y=1.65+.08*rng.normal(size=len(x));y[50000::100000]=np.nan
    # Two full-detail dense cases, same vertices, all candidate/repeat timings saved.
    for step in (False,True):
        opts=dict(step=step,gap_cut=True,time_mode=True,dt=2e6/args.dense,style='Rápido',dpr=2.)
        traces=[(x*1e6,y,'#00e5ff')];rect=(0,2e6,-.066,3.366);reference=None
        for repeat in range(args.repeat):
            for kind in kinds[repeat%len(kinds):]+kinds[:repeat%len(kinds)]:
                if kind not in accepted:continue
                pixels,ms=render(traces,rect,opts,kind,(2200,1200))
                if reference is None:
                    if kind!='baseline':reference,_=render(traces,rect,opts,'baseline',(2200,1200))
                    else:reference=pixels
                rows.append(dict(phase='dense',kind=kind,step=step,repeat=repeat,samples=args.dense,ms=ms,different_pixels=int(np.count_nonzero(np.any(pixels!=reference,axis=2)))))
                del pixels
    report=dict(private=True,board_used=False,product_changed=False,rows=rows,quality_exact=accepted)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    for kind in kinds:
        q=[r['different_pixels'] for r in rows if r['kind']==kind and r['phase']=='quality']
        dense=[r['ms'] for r in rows if r['kind']==kind and r['phase']=='dense']
        print(kind,'quality max diff',max(q,default=0),'dense median ms',float(np.median(dense)) if dense else None)
    return 0

if __name__=='__main__':raise SystemExit(main())
