"""Bounded WAV visualization from the existing immutable transfer file and DAC ACKs."""
import math,time
import numpy as np
from PySide6 import QtCore


class WavOutputMeter(QtCore.QObject):
    def __init__(self,owner,spectrum,dial):
        super().__init__(owner)
        self.owner=owner;self.spectrum=spectrum;self.dial=dial
        self.codes=None;self.status=None;self.at=0.;self.feed_at=0.;self.pending=False
        self.level=0.;self.target=0.;self.visual_at=None
        self.timer=QtCore.QTimer(self);self.timer.setInterval(33)
        self.timer.timeout.connect(self.refresh)

    def load(self,path,rate):
        self.release()
        try:
            codes=np.load(path,mmap_mode='r',allow_pickle=False)
            if codes.ndim!=1 or codes.dtype.kind not in 'ui':return
            self.codes=codes;self.rate=rate;self.pending=True
        except (OSError,ValueError):return  # A visual meter must never prevent playback.

    def observe(self,status):
        # Polls from before BEGIN may still arrive while the WAV is priming.
        if self.pending and int(status.state) in (0,3):return
        if int(status.state) in (1,2):self.pending=False
        self.status=status;self.at=time.monotonic()
        if int(status.state)==2 and self.codes is not None:self.timer.start()
        elif int(status.state) in (0,3,4,5):self.release()

    def release(self):
        self.codes=None;self.status=None;self.target=0.;self.feed_at=0.;self.pending=False
        if hasattr(self,'timer'):self.timer.stop()
        self.level=0.;self.visual_at=None
        self.dial.audio_meter_level=0. if self.owner.generator_mode.currentIndex()==4 else None
        self.dial.update()
        self.spectrum.samples=np.empty(0);self.spectrum.levels[:]=0
        self.spectrum._target[:]=0;self.spectrum._dirty=False;self.spectrum.update()

    def refresh(self):
        now=time.monotonic();status=self.status
        visible=self.owner.generator_mode.currentIndex()==4 and self.spectrum.isVisible()
        live=(visible and status is not None and int(status.state)==2
              and self.codes is not None and now-self.at<1.)
        volume=self.owner.generator_amplitude.value()/3.3
        if live and now-self.feed_at>=.075:
            self.feed_at=now
            # played already includes seek origin; accepted is session-relative.
            # Use the acknowledged position rather than inventing future samples.
            end=min(len(self.codes),max(0,int(status.played)))
            values=np.asarray(self.codes[max(0,end-2048):end],dtype=float)*(3.3/4095)
            self.spectrum.feed(values,'wav',status.rate,1.65)
            self.target=(min(1.,float(np.max(np.abs(values-1.65)))*volume/1.65)
                         if len(values) else 0.)
        elif not live:self.target=0.
        self.spectrum.refresh(now,live,volume)
        dt=1/30 if self.visual_at is None else min(1.,now-self.visual_at)
        self.visual_at=now
        tau=.045 if self.target>self.level else .18
        self.level+=(self.target-self.level)*(1-math.exp(-dt/tau))
        level=round(self.level*100)/100
        if level!=getattr(self.dial,'audio_meter_level',None):
            self.dial.audio_meter_level=level;self.dial.update()
