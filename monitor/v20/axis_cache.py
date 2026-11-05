"""Bounded device-resolution cache for static temporal axes, never trace data."""
import math
import pyqtgraph as pg
from PySide6 import QtCore,QtGui


def paint_cached_axis(axis,painter,option,widget=None):
    transform=painter.worldTransform()
    enabled=getattr(axis,'cache_static_paint',False)
    if (not enabled or abs(transform.m11()-1)>1e-9 or abs(transform.m22()-1)>1e-9
            or abs(transform.m12())>1e-9 or abs(transform.m21())>1e-9):
        return pg.AxisItem.paint(axis,painter,option,widget)
    dpr=painter.device().devicePixelRatioF()
    bounds=axis.boundingRect().adjusted(-1,-1,1,1)
    # Align the cached raster with the original device-pixel phase, including
    # fractional item placement in QGraphicsLayout (important on Retina).
    left=math.floor((bounds.left()+transform.dx())*dpr)/dpr-transform.dx()
    top=math.floor((bounds.top()+transform.dy())*dpr)/dpr-transform.dy()
    width=max(1,math.ceil((bounds.right()-left)*dpr))
    height=max(1,math.ceil((bounds.bottom()-top)*dpr))
    if width*height>4_000_000:
        axis._static_axis_cache=None
        return pg.AxisItem.paint(axis,painter,option,widget)
    key=(left,top,width,height,dpr,painter.font().key())
    cached=getattr(axis,'_static_axis_cache',None)
    if axis.picture is not None and cached is not None and cached[0] is axis.picture and cached[1]==key:
        painter.drawPixmap(QtCore.QPointF(left,top),cached[2]);return
    # Let pyqtgraph generate specifications in its original painter context.
    pg.AxisItem.paint(axis,painter,option,widget)
    if axis.picture is None:return
    image=QtGui.QPixmap(width,height);image.setDevicePixelRatio(dpr)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    cached_painter=QtGui.QPainter(image)
    try:
        cached_painter.setRenderHints(painter.renderHints())
        cached_painter.setFont(painter.font());cached_painter.translate(-left,-top)
        axis.picture.play(cached_painter)
    finally:cached_painter.end()
    axis._static_axis_cache=(axis.picture,key,image)
