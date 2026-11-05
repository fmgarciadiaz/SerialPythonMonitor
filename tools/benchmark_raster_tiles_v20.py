#!/usr/bin/env python3
"""Offline experimental strip workers; no acquisition/product changes."""
import os
if __name__=='__main__':
    os.environ.setdefault('PYQTGRAPH_QT_LIB','PySide6')
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,json,sys,time,multiprocessing as mp
from multiprocessing import shared_memory
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotCurveItem import arrayToLineSegments
from monitor.v20.temporal_raster import paint_traces,prepare_vertices


def tile(job):
    source=shared_memory.SharedMemory(name=job['source']);target=shared_memory.SharedMemory(name=job['target'])
    image=painter=x=y=None;traces=[]
    try:
        width,height=job['size'];left,right=job['clip'];xmin,xmax,ymin,ymax=job['rect'];opts=job['options']
        image=QtGui.QImage(target.buf,width,height,width*4,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
        painter=QtGui.QPainter(image);painter.setClipRect(left,0,right-left,height)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing,opts['style']=='Suave')
        pad=2*opts['dpr']+2
        for offset,n,color in job['traces']:
            x=np.ndarray((n,),np.float64,buffer=source.buf,offset=offset)
            y=np.ndarray((n,),np.float64,buffer=source.buf,offset=offset+n*8)
            # A pen can enter a strip from outside it. Keep neighbors and a
            # device-width halo; use the original global mapping, not a tile map.
            lo=max(0,int(np.searchsorted(x,xmin+(left-pad)/width*(xmax-xmin)))-1)
            hi=min(n,int(np.searchsorted(x,xmin+(right+pad)/width*(xmax-xmin)))+1)
            x,y=prepare_vertices(x[lo:hi],y[lo:hi],opts['step'],opts['gap_cut'],opts['time_mode'],opts['dt'])
            pen=pg.mkPen(color,width=(2 if opts['style']=='Intenso' else 1)*opts['dpr']);pen.setCosmetic(True);painter.setPen(pen)
            xp=(x-xmin)*(width/(xmax-xmin));yp=(ymax-y)*(height/(ymax-ymin))
            painter.drawLines(*arrayToLineSegments(xp,yp,'finite',True).drawargs())
        painter.end();painter=None
        return True
    finally:
        if painter is not None:painter.end()
        image=x=y=None;source.close();target.close()


def tiled(pool,workers,traces,rect,opts,size):
    for x,y,_ in traces:
        if not np.all(np.isfinite(x)) or np.any(np.diff(x)<0):raise ValueError('Experimental tiles require finite sorted X')
    began=time.perf_counter();nbytes=sum(len(x)*16 for x,y,c in traces)
    source=shared_memory.SharedMemory(create=True,size=nbytes);target=shared_memory.SharedMemory(create=True,size=size[0]*size[1]*4)
    try:
        descriptors=[];offset=0
        for x,y,color in traces:
            n=len(x);np.ndarray((n,),np.float64,source.buf,offset)[:]=x;np.ndarray((n,),np.float64,source.buf,offset+n*8)[:]=y
            descriptors.append((offset,n,color));offset+=n*16
        pixels=np.ndarray((size[1],size[0],4),np.uint8,target.buf);pixels[:]=0
        jobs=[dict(source=source.name,target=target.name,traces=descriptors,rect=rect,options=opts,size=size,clip=(i*size[0]//workers,(i+1)*size[0]//workers)) for i in range(workers)]
        for result in pool.map(tile,jobs):assert result
        answer=pixels.copy();del pixels
        return answer,(time.perf_counter()-began)*1000
    finally:source.close();source.unlink();target.close();target.unlink()


def baseline(traces,rect,opts,size):
    image=QtGui.QImage(*size,QtGui.QImage.Format.Format_ARGB32_Premultiplied);image.fill(QtCore.Qt.GlobalColor.transparent)
    start=time.perf_counter();paint_traces(image,traces,rect,opts)
    return np.frombuffer(image.constBits(),np.uint8,count=image.sizeInBytes()).reshape(size[1],size[0],4).copy(),(time.perf_counter()-start)*1000


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=3720930);args=p.parse_args()
    if args.output.exists():p.error('New report required')
    app=QtWidgets.QApplication([]);rows=[];rng=np.random.default_rng(722)
    for workers in (2,4):
        with ProcessPoolExecutor(workers,mp_context=mp.get_context('spawn')) as pool:
            for style in ('Rápido','Intenso','Suave'):
                for step in (False,True):
                    for dpr in (1,2):
                        x=np.linspace(-.2,2.2,4001);y=1.65+.3*rng.normal(size=len(x));y[100:105]=np.nan;y[151]=np.inf;y[800:810]+=8
                        opts=dict(step=step,gap_cut=True,time_mode=False,dt=1.,style=style,dpr=dpr)
                        traces=[(x,y,'#00e5ff'),(x,3.3-y,'#ffd166')];rect=(0,2,0,3.3);size=(480*dpr,240*dpr)
                        ref,_=baseline(traces,rect,opts,size);actual,ms=tiled(pool,workers,traces,rect,opts,size)
                        rows.append(dict(phase='quality',workers=workers,style=style,step=step,dpr=dpr,ms=ms,different_pixels=int(np.count_nonzero(np.any(ref!=actual,axis=2)))))
            x=np.linspace(0,2e6,args.samples);y=1.65+.08*rng.normal(size=len(x));y[50000::100000]=np.nan
            for step in (False,True):
                opts=dict(step=step,gap_cut=True,time_mode=True,dt=2e6/args.samples,style='Rápido',dpr=2.)
                traces=[(x,y,'#00e5ff')];rect=(0,2e6,-.066,3.366);size=(2200,1200)
                for repeat in range(3):
                    ref,base_ms=baseline(traces,rect,opts,size);actual,ms=tiled(pool,workers,traces,rect,opts,size)
                    rows.append(dict(phase='dense',workers=workers,step=step,repeat=repeat,ms=ms,baseline_ms=base_ms,speedup=base_ms/ms,different_pixels=int(np.count_nonzero(np.any(ref!=actual,axis=2)))))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(private=True,board_used=False,product_changed=False,rows=rows),indent=2)+'\n')
    for workers in (2,4):
        selected=[r for r in rows if r['workers']==workers];print(workers,'max pixel diff',max(r['different_pixels'] for r in selected),'median speedup',np.median([r['speedup'] for r in selected if r['phase']=='dense']))
    return 0

if __name__=='__main__':raise SystemExit(main())
