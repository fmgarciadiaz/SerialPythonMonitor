"""Observe actual paint/exposure only while DAC playback is active."""
import time
from PyQt6 import QtCore


class WavVisualAudit(QtCore.QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.started = None
        self.seconds = 0.
        self.last_exposure = -float('inf')
        self.counts = dict(scope_paints=0,fft_paints=0,exposure_checks=0,exposed_checks=0)
        self.targets = {window.plot_widget.viewport():'scope_paints',
                        window.spectral.widget.viewport():'fft_paints'}
        for target in self.targets: target.installEventFilter(self)

    def playing(self, active):
        if active and self.started is None:
            self.started = time.monotonic()
        elif not active and self.started is not None:
            self.seconds += time.monotonic()-self.started
            self.started = None

    def sample_exposure(self):
        if self.started is None: return
        now = time.monotonic()
        if now-self.last_exposure >= .1:
            self.last_exposure = now
            self.counts['exposure_checks'] += 1
            handle = self.window.windowHandle()
            self.counts['exposed_checks'] += int(handle is not None and handle.isExposed())

    def eventFilter(self, obj, event):
        if self.started is not None and event.type()==QtCore.QEvent.Type.Paint:
            key = self.targets.get(obj)
            if key is not None: self.counts[key] += 1
        return False

    def snapshot(self):
        seconds = self.seconds+(time.monotonic()-self.started if self.started is not None else 0.)
        fps = (self.counts['scope_paints']+self.counts['fft_paints'])/seconds if seconds>0 else 0.
        exposure = self.counts['exposed_checks']/max(1,self.counts['exposure_checks'])
        return dict(self.counts,seconds=seconds,paint_fps=fps,exposed_fraction=exposure,
                    visual_ok=exposure>=.9 and fps>=5)
