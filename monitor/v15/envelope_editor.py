"""Compact ADSR editor: two envelopes, with logarithmic time sliders."""
import math
from PyQt6 import QtCore, QtGui, QtWidgets

class EnvelopeCurve(QtWidgets.QWidget):
    def __init__(self, controls, color):
        super().__init__();self.controls=controls;self.color=color
        self.setFixedHeight(20)
        for control in controls:control.valueChanged.connect(self.update)
    def paintEvent(self,event):
        painter=QtGui.QPainter(self);painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        a,d,s,r=[c.value() for c in self.controls]
        widths=[math.log1p(a),math.log1p(d),3,math.log1p(r)]
        unit=(self.width()-12)/sum(widths);x=6;bottom=self.height()-4;top=4
        points=[QtCore.QPointF(x,bottom)]
        for width,y in zip(widths,(top,bottom-(bottom-top)*s/100,bottom-(bottom-top)*s/100,bottom)):
            x+=width*unit;points.append(QtCore.QPointF(x,y))
        painter.setPen(QtGui.QPen(QtGui.QColor(self.color),1.5));painter.drawPolyline(QtGui.QPolygonF(points))

class EnvelopeEditor(QtWidgets.QWidget):
    def __init__(self, groups):
        super().__init__();layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(1)
        self.sliders=[]
        for title,controls,color in groups:
            header=QtWidgets.QLabel(title);header.setFixedHeight(14);header.setStyleSheet('color: '+color+';');layout.addWidget(header)
            layout.addWidget(EnvelopeCurve(controls,color))
            row=QtWidgets.QGridLayout();row.setSpacing(2)
            for i,(label,spin) in enumerate(zip(('A','D','S','R'),controls)):
                text=QtWidgets.QLabel(label);text.setFixedHeight(14);text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                slider=QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical);slider.setRange(0,1000);slider.setFixedHeight(22)
                slider.setToolTip(('Ataque','Caída','Sostenido','Liberación')[i])
                def to_value(v,spin=spin,i=i):
                    return v/10 if i==2 else round(math.exp(math.log(spin.minimum())+v/1000*math.log(spin.maximum()/spin.minimum())))
                def sync(v,slider=slider,spin=spin,i=i):
                    value=round(v*10) if i==2 else round(1000*math.log(max(v,spin.minimum())/spin.minimum())/math.log(spin.maximum()/spin.minimum()))
                    with QtCore.QSignalBlocker(slider):slider.setValue(value)
                slider.valueChanged.connect(lambda v,spin=spin,f=to_value:spin.setValue(f(v)))
                spin.valueChanged.connect(sync);sync(spin.value())
                spin.setFixedHeight(22);spin.setDecimals(0);spin.setSuffix('');spin.setToolTip(slider.toolTip()+(' (%)' if i==2 else ' (ms)'))
                row.addWidget(text,0,i);row.addWidget(slider,1,i,QtCore.Qt.AlignmentFlag.AlignHCenter);row.addWidget(spin,2,i)
                row.setColumnStretch(i,1);self.sliders.append(slider)
            layout.addLayout(row)
