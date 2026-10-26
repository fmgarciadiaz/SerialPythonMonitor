"""Small audio-only spectrum display; independent of the analysis FFT."""
import numpy as np
from PyQt6 import QtCore,QtGui,QtWidgets

CENTERS=np.array([63,125,250,500,1000,2000,4000,6000,8000,12000])

class RadioLedSpectrum(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedHeight(92)
        self.setToolTip('Espectro de audio · 10 bandas · nivel relativo a escala completa; no modifica el sonido')
        self.samples=np.empty(0);self.key=None;self.rate=40000
        self.levels=np.zeros(10);self.window=np.hanning(2048)
        self._at=None;self._dirty=False
        self._visual_at=None;self._target=np.zeros(10)

    def feed(self,audio,key,rate,offset):
        if key!=self.key:
            self.samples=np.empty(0);self.key=key;self.levels[:]=0
        self.rate=rate
        values=np.asarray(audio)[-2048:]-offset
        if not np.isfinite(values).all():return
        self.samples=np.concatenate((self.samples,values))[-2048:]
        self._dirty=True

    def refresh(self,now,live,volume):
        if self._visual_at is None or now-self._visual_at>=1/30:
            dt=1/30 if self._visual_at is None else min(1.,now-self._visual_at)
            self._visual_at=now
            target=self._target if live and volume else np.zeros(10)
            tau=np.where(target>self.levels,.045,.18)
            levels=self.levels+(target-self.levels)*(1-np.exp(-dt/tau))
            levels=np.where(levels<.002,0,levels)
            if np.max(np.abs(levels-self.levels))>.001:
                self.levels=levels;self.update()
        if self._at is not None and now-self._at<.075:return
        elapsed=.075 if self._at is None else min(1.,now-self._at)
        self._at=now
        target=np.zeros(10)
        if live and self._dirty and len(self.samples)==2048:
            values=(self.samples-self.samples.mean())*self.window
            power=np.abs(np.fft.rfft(values))**2
            frequencies=np.fft.rfftfreq(2048,1/self.rate)
            edges=np.r_[CENTERS[0]/np.sqrt(2),np.sqrt(CENTERS[:-1]*CENTERS[1:]),CENTERS[-1]*np.sqrt(2)]
            for i in range(10):
                mask=(frequencies>=edges[i])&(frequencies<min(edges[i+1],self.rate/2))
                # Hann-normalized band RMS relative to a full-scale sine.
                rms=np.sqrt(2*power[mask].sum()/(2048*(self.window**2).sum()))
                db=20*np.log10(max(1e-12,rms*volume/(1.65/np.sqrt(2))))
                target[i]=np.clip((db+54)/54,0,1)
            self._dirty=False
        self._target=target

    def paintEvent(self,event):
        p=QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor('#4a515d'),1))
        p.setBrush(QtGui.QColor('#171c22'))
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),6,6)
        font=p.font();font.setPixelSize(9);p.setFont(font)
        width=max(1,self.width()-12)/10
        for i,center in enumerate(CENTERS):
            for led in range(12):
                amount=np.clip(self.levels[i]*12-led,0,1)
                off=QtGui.QColor('#28332f')
                on=QtGui.QColor('#65c99a' if led<8 else '#e5a34e' if led<10 else '#e56964')
                color=QtGui.QColor(*(round(a+(b-a)*amount) for a,b in zip(off.getRgb()[:3],on.getRgb()[:3])))
                p.fillRect(QtCore.QRectF(6+i*width+3,65-led*4.5,max(2,width-6),3),color)
            p.setPen(QtGui.QColor('#9ca8b5'))
            label=str(center) if center<1000 else f'{center//1000}k'
            p.drawText(QtCore.QRectF(6+i*width,71,width,15),QtCore.Qt.AlignmentFlag.AlignCenter,label)
