"""Time the real Qt scene paint, including deferred curve path construction."""
import time
import math
import pyqtgraph as pg


def visual_interval(base,paint_ms,prepare_ms):
    # Leave most GUI time for acquisition delivery and user input. This paces
    # drawing only; it neither reduces samples nor changes acquisition/DSP.
    return max(base,min(500,round(max(paint_ms*4,prepare_ms*3))))


def balanced_visual_interval(paint_ms,prepare_ms):
    """Reserve 40% of GUI time for delivery and interaction in short RF views."""
    return min(500,max(34,math.ceil((paint_ms+prepare_ms)/.60)))


class TemporalPlotWidget(pg.PlotWidget):
    paint_observer=None
    def paintEvent(self,event):
        began=time.perf_counter()
        try:return super().paintEvent(event)
        finally:
            if self.paint_observer is not None:self.paint_observer((time.perf_counter()-began)*1000)
