"""Bounded point/envelope renderer; raw captures remain available to cursors."""
import multiprocessing as mp
from multiprocessing import shared_memory
import time
import numpy as np
from PySide6 import QtCore,QtGui
import pyqtgraph as pg


class EnvelopeBadge(pg.TextItem):
    """Small translucent overlay; never captures plotting mouse gestures."""
    def __init__(self):
        super().__init__('envelope',color='#d5dce3',anchor=(1,0))
        self.setText('  envelope  ')
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.textItem.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    def paint(self,painter,*args):
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing,True)
        painter.setPen(QtGui.QPen(QtGui.QColor(125,139,152,150),1))
        painter.setBrush(QtGui.QColor(42,51,61,175))
        painter.drawRoundedRect(self.boundingRect().adjusted(.5,.5,-.5,-.5),4,4)
        painter.restore()


def prepare_vertices(x,y,step,gap_cut,time_mode,dt,detect_gaps=True):
    """Same finite/gap and step geometry as the vector plot, without reduction."""
    n=len(x)
    if n<2 or len(y)!=n or (not step and not gap_cut):return x,y
    threshold,nominal=(max(3.*dt,1500.),dt) if time_mode and dt>0 else ((2000.,0.) if time_mode else (2.,1.))
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    gaps=np.diff(x)>threshold if gap_cut and detect_gaps else np.zeros(n-1,dtype=bool)
    if step and not np.any(gaps):
        xo=np.empty(2*n-1);yo=np.empty(2*n-1)
        xo[0],yo[0]=x[0],y[0]
        xo[1::2]=xo[2::2]=x[1:];yo[1::2],yo[2::2]=y[:-1],y[1:]
        return xo,yo
    if not np.any(gaps):return x,y
    hold=x[:-1]+nominal;extra=gaps&(hold<x[1:]) if step else gaps
    sizes=(2 if step else 1)+extra.astype(np.intp);ends=np.cumsum(sizes);starts=ends-sizes+1
    xo=np.empty(int(ends[-1])+1);yo=np.empty_like(xo)
    xo[0],yo[0]=x[0],y[0];xo[ends],yo[ends]=x[1:],y[1:]
    if step:
        xo[starts]=np.where(gaps,hold,x[1:]);yo[starts]=np.where(gaps&~extra,np.nan,y[:-1])
        xo[starts[extra]+1]=hold[extra];yo[starts[extra]+1]=np.nan
    else:xo[starts[gaps]],yo[starts[gaps]]=x[:-1][gaps],np.nan
    return xo,yo


def paint_traces(image,traces,rect,options):
    """Paint original vertices or display extrema without modifying captures."""
    xmin,xmax,ymin,ymax=rect
    envelope_used=False
    painter=QtGui.QPainter(image)
    try:
        painter.setClipRect(0,0,image.width(),image.height())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing,options['style']=='Suave')
        for x,y,color in traces:
            if options.get('envelope',False) and len(x)>=image.width()*4:
                from monitor.v20.temporal_envelope import envelope_geometry
                geometry=envelope_geometry(x,y,xmin,xmax,image.width(),step=options['step'],
                    gap_cut=options['gap_cut'],time_mode=options['time_mode'],dt=options['dt'])
                if geometry is not None:
                    cx,low,high,lx,ly=geometry
                    pen=pg.mkPen(color,width=(2 if options['style']=='Intenso' else 1)*options.get('dpr',1.))
                    pen.setCosmetic(True);painter.setPen(pen)
                    from pyqtgraph.graphicsItems.PlotCurveItem import arrayToLineSegments
                    bx=np.repeat((cx-xmin)*(image.width()/(xmax-xmin)),2)
                    by=(ymax-np.column_stack((low,high)).reshape(-1))*(image.height()/(ymax-ymin))
                    painter.drawLines(*arrayToLineSegments(bx,by,'pairs',True).drawargs())
                    if len(lx):
                        px=(lx-xmin)*(image.width()/(xmax-xmin));py=(ymax-ly)*(image.height()/(ymax-ymin))
                        painter.drawLines(*arrayToLineSegments(px,py,'pairs',True).drawargs())
                    envelope_used=True
                    continue
            x,y=prepare_vertices(x,y,options['step'],options['gap_cut'],options['time_mode'],options['dt'])
            pen=pg.mkPen(color,width=(2 if options['style']=='Intenso' else 1)*options.get('dpr',1.))
            pen.setCosmetic(True);painter.setPen(pen)
            # Map vertices first. A cosmetic pen under a very small world-X
            # transform makes Qt's stroker pathological for dense step traces.
            # Device-space geometry preserves every point and the same width.
            # Segment strokes avoid Qt's costly outline of a giant dense path.
            xp=(np.asarray(x)-xmin)*(image.width()/(xmax-xmin))
            yp=(ymax-np.asarray(y))*(image.height()/(ymax-ymin))
            renderer=options.get('renderer','segments')
            if renderer=='segments':
                from pyqtgraph.graphicsItems.PlotCurveItem import arrayToLineSegments
                painter.drawLines(*arrayToLineSegments(xp,yp,'finite',True).drawargs())
            elif renderer=='polyline':
                valid=np.isfinite(xp)&np.isfinite(yp)
                edges=np.flatnonzero(np.diff(np.r_[False,valid,False]))
                for start,end in edges.reshape(-1,2):
                    if end-start>1:painter.drawPolyline(pg.functions.arrayToQPolygonF(xp[start:end],yp[start:end]))
            else:painter.drawPath(pg.arrayToQPath(xp,yp,connect='finite',finiteCheck=True))
    finally:painter.end()
    return envelope_used


def _raster_child(pipe):
    # No QApplication: only private QImages, never a scene or a widget.
    try:
        while True:
            job=pipe.recv()
            if job is None:return
            inputs=output=None
            traces=[];image=x=y=None
            try:
                began=time.perf_counter()
                inputs=shared_memory.SharedMemory(name=job['input'])
                output=shared_memory.SharedMemory(name=job['output'])
                traces=[]
                for offset,count,color in job['traces']:
                    x=np.ndarray((count,),dtype=np.float64,buffer=inputs.buf,offset=offset)
                    y=np.ndarray((count,),dtype=np.float64,buffer=inputs.buf,offset=offset+count*8)
                    traces.append((x,y,color))
                width,height=job['size']
                image=QtGui.QImage(output.buf,width,height,width*4,QtGui.QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(QtCore.Qt.GlobalColor.transparent)
                used=paint_traces(image,traces,job['rect'],job['options'])
                pipe.send(dict(ok=True,envelope=used,milliseconds=(time.perf_counter()-began)*1000))
            except Exception as exc:pipe.send(dict(ok=False,error=repr(exc)))
            finally:
                image=x=y=None;traces.clear()
                if inputs is not None:inputs.close()
                if output is not None:output.close()
    except (EOFError,BrokenPipeError):pass
    finally:pipe.close()


class RasterProcess:
    """One job in flight, small control messages, shared arrays/images, bounded exit."""
    def __init__(self):
        context=mp.get_context('spawn');self.pipe,child=context.Pipe()
        self.process=context.Process(target=_raster_child,args=(child,),name='Arduscopio trace raster',daemon=True)
        self.process.start();child.close()
        self.pending=None;self.closed=False

    @property
    def busy(self):return self.pending is not None

    def submit(self,traces,rect,size,options,token,frame):
        if self.closed or self.busy:return False
        width,height=size
        if width<=0 or height<=0 or width*height>32_000_000:raise ValueError('Tamaño de raster inválido')
        count=sum(len(x) for x,y,color in traces)
        inputs=shared_memory.SharedMemory(create=True,size=max(1,count*16))
        output=None
        try:
            output=shared_memory.SharedMemory(create=True,size=width*height*4)
            offset=0;descriptors=[]
            for x,y,color in traces:
                n=len(x);descriptors.append((offset,n,color))
                np.ndarray((n,),np.float64,inputs.buf,offset=offset)[:]=x
                np.ndarray((n,),np.float64,inputs.buf,offset=offset+n*8)[:]=y
                offset+=n*16
            self.pending=dict(inputs=inputs,output=output,token=token,frame=frame,rect=rect,size=size)
            self.pipe.send(dict(input=inputs.name,output=output.name,traces=descriptors,rect=rect,size=size,options=options))
            return True
        except Exception:
            self.pending=None
            for block in (inputs,output):
                if block is not None:block.close();block.unlink()
            raise

    def poll(self):
        if not self.pending:return None
        if not self.pipe.poll():
            if not self.process.is_alive():raise RuntimeError('El proceso de dibujo se cerró')
            return None
        response=self.pipe.recv();pending=self.pending;self.pending=None
        try:
            if not response['ok']:raise RuntimeError(response['error'])
            width,height=pending['size']
            image=QtGui.QImage(pending['output'].buf,width,height,width*4,QtGui.QImage.Format.Format_ARGB32_Premultiplied).copy()
            return dict(image=image,token=pending['token'],frame=pending['frame'],rect=pending['rect'],envelope=response.get('envelope',False),milliseconds=response['milliseconds'])
        finally:
            for key in ('inputs','output'):pending[key].close();pending[key].unlink()

    def close(self):
        if self.closed:return
        self.closed=True
        # This child has no device, file transaction or restoration to finish.
        if self.process.is_alive():self.process.terminate()
        self.process.join(timeout=.25)
        if self.process.is_alive():self.process.kill();self.process.join(timeout=.25)
        self.pipe.close()
        if self.pending:
            for key in ('inputs','output'):self.pending[key].close();self.pending[key].unlink()
            self.pending=None


class RasterItem(pg.GraphicsObject):
    """Cheap image composition in data coordinates; axes/overlays remain vectors."""
    def __init__(self):
        super().__init__();self.image=None;self.rect=QtCore.QRectF();self.setZValue(0)
    def boundingRect(self):return self.rect
    def publish(self,image,rect):
        self.prepareGeometryChange()
        self.image=image;xmin,xmax,ymin,ymax=rect
        self.rect=QtCore.QRectF(xmin,ymin,xmax-xmin,ymax-ymin);self.update();self.show()
    def paint(self,painter,*args):
        if self.image is not None:
            # Image rows descend, whereas ordinary ViewBox data Y ascends.
            painter.save();painter.scale(1,-1)
            painter.drawImage(QtCore.QRectF(self.rect.left(),-self.rect.bottom(),self.rect.width(),self.rect.height()),self.image)
            painter.restore()


class TemporalRaster:
    """GUI coordinator: publish only matching view generations and raw snapshots."""
    MIN_POINTS=100_000
    def __init__(self,owner):
        self.owner=owner;self.worker=None;self.item=RasterItem()
        owner.plot_widget.addItem(self.item,ignoreBounds=True);self.item.hide()
        self.envelope_active=False
        self.env_label=EnvelopeBadge()
        font=self.env_label.textItem.font();font.setPointSize(8);self.env_label.setFont(font)
        self.env_label.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.env_label.textItem.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.env_label.setZValue(1000);owner.plot_widget.addItem(self.env_label,ignoreBounds=True);self.env_label.hide()
        self.epoch=0;self.active=False;self.failed=False;self.queued=None;self.closed=False
        self.published=0;self.last_ms=0.;self.context_at_publish=None
        self.rejected=0;self.last_rejection=[];self.error_message=None
        self.timer=QtCore.QTimer(owner);self.timer.setInterval(16);self.timer.timeout.connect(self.poll)
        self.timer.start()

    def context(self):
        o=self.owner;view=o.plot_widget.getViewBox();ranges=view.viewRange()
        dpr=o.plot_widget.devicePixelRatioF()
        cfg=getattr(o,'applied_configuration',None)
        return (getattr(getattr(o,'spectral',None),'mode',0),id(getattr(o,'serial_worker',None)),
                (getattr(cfg,'bits',None),getattr(cfg,'rate',None),getattr(cfg,'channels',None)),
                tuple(round(float(v),6) for pair in ranges for v in pair),
                max(1,round(view.width()*dpr)),max(1,round(view.height()*dpr)),float(dpr),
                o.trace_mode,o.trace_style_combo.currentText(),o.auto_gap_cut,o.x_axis_time_mode,
                o.h_scale,o.h_pos,o.detail_slider.value(),tuple(o.selected_columns.items()),
                tuple(o.channel_colors.items()),o.radio_offset.value(),o.radio_output_panel.volume.value(),
                o.generator_mode.currentIndex(),getattr(o,'_audio_continuity_epoch',0),
                id(getattr(o,'radio_stream',None)),o.radio_output_rate.currentData(),
                getattr(getattr(o,'radio_stream',None),'rate',None),
                (o.trigger_enabled,o.trigger_source,o.trigger_level,o.trigger_edge,o.trigger_mode),
                self.envelope_active,
                getattr(cfg,'dt_us',0.) if getattr(o,'serial_worker',None) is not None else round(o.current_dt_us,4))

    def invalidate(self):
        self.env_label.hide()
        self.epoch+=1;self.queued=None;self.item.hide();self.context_at_publish=None
        self.owner._visible_display_frame=None
        cursors=getattr(self.owner,'scope_cursors',None)
        if cursors is not None:cursors.invalidate()

    def skip_live(self):
        return (self.active and not self.failed and self.worker is not None and self.worker.busy
                and (self.worker.pending['token']==(self.epoch,self.context())
                     or self.queued is not None and self.queued[1]==(self.epoch,self.context())))

    def draw(self,xs,ys,channels):
        o=self.owner
        from monitor.v20.temporal_envelope import envelope_mode
        ctx=self.context();xmin,xmax=ctx[3][:2];counts=[]
        for c in channels:
            x=xs.get(c,()) if isinstance(xs,dict) else xs
            if len(x):counts.append(max(0,int(np.searchsorted(x,xmax,'right')-np.searchsorted(x,xmin,'left'))))
        self.envelope_active=envelope_mode(max(counts,default=0),ctx[4],self.envelope_active) if ctx[0]==0 else False
        dense=ctx[0]==0 and (self.envelope_active or o.detail_slider.value()==100 and sum(counts)>=self.MIN_POINTS)
        if not dense:
            if self.active:self.invalidate()
            self.active=False;self.failed=False
            if self.worker is not None:self.worker.close();self.worker=None
            return False
        if not self.active:self.invalidate()
        self.active=True
        key=(self.epoch,self.context())
        if self.failed:return True
        if self.worker is not None and self.worker.busy:
            # Only user/config changes need a replacement while rendering. Live
            # advancement never invalidates the job that will become visible.
            if (self.worker.pending['token']!=key and
                    (self.queued is None or self.queued[1]!=key)):
                self.queued=(self.snapshot(xs,ys,channels),key)
            return True
        self.submit(self.snapshot(xs,ys,channels),key)
        return True

    @staticmethod
    def snapshot(xs,ys,channels):
        x=({c:np.array(v,dtype=float,copy=True) for c,v in xs.items()} if isinstance(xs,dict)
           else np.array(xs,dtype=float,copy=True))
        y={c:np.array(v,dtype=float,copy=True) for c,v in ys.items()}
        return x,y,tuple(channels)

    def submit(self,frame,key):
        o=self.owner;xs,ys,channels=frame;traces=[]
        try:
            if self.worker is None:self.worker=RasterProcess()
            for col in o.line_items:o.line_items[col].setData([],[])
            for col in o.line_items:
                x=xs.get(col,()) if isinstance(xs,dict) else xs;y=ys.get(col,())
                if col in channels and len(x)==len(y) and len(x):
                    traces.append((x,o._radio_display_values(col,y),o.channel_colors[col]))
            ctx=key[1];xmin,xmax,ymin,ymax=ctx[3]
            if xmax<=xmin or ymax<=ymin:return
            options=dict(step=o.trace_mode=='Escalón',gap_cut=o.auto_gap_cut,time_mode=o.x_axis_time_mode,
                         dt=ctx[-1],style=o.trace_style_combo.currentText(),dpr=ctx[6],envelope=self.envelope_active)
            self.worker.submit(traces,(xmin,xmax,ymin,ymax),(ctx[4],ctx[5]),options,key,frame)
        except Exception as exc:self.error(exc)

    def error(self,exc):
        self.failed=True;self.queued=None;self.error_message=str(exc)
        import logging
        logging.getLogger(__name__).error('Raster detenido: %s',exc,exc_info=True)
        self.owner._set_connection_status('Error de dibujo: '+str(exc))
        # Never fall back to a million-point draw in the GUI after worker failure.
        if self.worker is not None:self.worker.close();self.worker=None

    def poll(self):
        if self.closed or not self.active:return
        try:
            context=self.context()
            if context[0]!=0:
                self.invalidate();self.active=False
                if self.worker is not None:self.worker.close();self.worker=None
                return
            if self.context_at_publish is not None and self.context_at_publish!=context:
                self.item.hide();self.env_label.hide();self.owner._visible_display_frame=None
                self.owner.scope_cursors.invalidate();self.context_at_publish=None
                if self.worker is not None and not self.worker.busy and not self.owner.is_running:
                    frame=getattr(self.owner,'_last_display_frame',None)
                    if frame is not None:self.draw(*frame)
            result=self.worker.poll() if self.worker is not None else None
            if result is None:return
            if result['token']!=(self.epoch,context):
                self.rejected+=1
                self.last_rejection=[(i,repr(a)[:180],repr(b)[:180]) for i,(a,b) in
                    enumerate(zip(result['token'][1],context)) if a!=b]
            if result['token']==(self.epoch,context):
                self.item.publish(result['image'],result['rect']);self.context_at_publish=context
                self.owner._visible_display_frame=result['frame']
                self.owner.scope_cursors.update_frame(*result['frame'])
                self.published+=1;self.last_ms=result['milliseconds']
                if result.get('envelope',False):
                    xmin,xmax,ymin,ymax=context[3]
                    self.env_label.setPos(xmax-(xmax-xmin)*.012,ymax-(ymax-ymin)*.015);self.env_label.show()
                else:self.env_label.hide()
            if self.queued is not None:
                frame,key=self.queued;self.queued=None
                if key==(self.epoch,context):self.submit(frame,key)
            if (self.worker is not None and not self.worker.busy and
                    result['token']!=(self.epoch,context)):
                if not self.owner.is_running:
                    frame=getattr(self.owner,'_last_display_frame',None)
                    if frame is not None:self.draw(*frame)
                elif (result['token'][0]==self.epoch and self.last_rejection and
                      all(index in (3,4,5,6) for index,_,_ in self.last_rejection)):
                    # Layout settling may resize the view without a new DATA
                    # frame. Repaint that same immutable capture at its new size.
                    self.submit(result['frame'],(self.epoch,context))
        except Exception as exc:self.error(exc)

    def close(self):
        self.closed=True;self.timer.stop();self.queued=None;self.env_label.hide()
        if self.worker is not None:self.worker.close();self.worker=None
