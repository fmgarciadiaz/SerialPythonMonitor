"""Count coalesced Qt paints containing new plot data, not timer callbacks."""
import time
import weakref
from PySide6 import QtCore


class DisplayFps(QtCore.QObject):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.views={};self.items=weakref.WeakSet();self.started=time.perf_counter()

    def watch(self,widget,plots):
        viewport=widget.viewport()
        self.views[viewport]={'dirty':False,'frames':0}
        viewport.installEventFilter(self)
        for plot in plots:
            original=plot.addItem
            def add(item,*args,_original=original,**kwargs):
                result=_original(item,*args,**kwargs)
                self._watch_item(item,viewport)
                return result
            plot.addItem=add
            # PlotWidget exports a bound copy of PlotItem.addItem.
            if getattr(widget,'plotItem',None) is plot:widget.addItem=add
            for item in plot.items:self._watch_item(item,viewport)

    def _watch_item(self,item,viewport):
        if item in self.items:return
        for name in ('sigPlotChanged','sigImageChanged','sigDataChanged'):
            signal=getattr(item,name,None)
            if signal is not None:
                signal.connect(lambda *args,v=viewport:self.mark(v))
                self.items.add(item)
                break

    def mark(self,viewport):
        self.views[viewport]['dirty']=True

    def eventFilter(self,watched,event):
        if event.type()==QtCore.QEvent.Type.Paint:
            state=self.views[watched]
            if state['dirty'] and watched.isVisible():
                state['frames']+=1;state['dirty']=False
        return False

    def sample(self,widget,now=None):
        now=time.perf_counter() if now is None else now
        elapsed=max(1e-9,now-self.started)
        state=self.views[widget.viewport()]
        rate=state['frames']/elapsed if widget.isVisible() else 0.
        for entry in self.views.values():entry['frames']=0
        self.started=now
        return rate
