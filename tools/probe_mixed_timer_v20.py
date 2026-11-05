"""QTimer reset probe with genuine deferred Qt painting; no Scope Q connection."""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6 import QtCore, QtWidgets


def main():
    app = QtWidgets.QApplication([])
    started = time.perf_counter()
    events = []
    timer = QtCore.QTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(80)

    def record(origin, before, after):
        events.append(dict(origin=origin, at_ms=round((time.perf_counter()-started)*1000, 3),
                           interval_before=before[0], remaining_before=before[1],
                           interval_after=after[0], remaining_after=after[1],
                           timer_id=timer.timerId()))

    def state(): return (timer.interval(), timer.remainingTime())

    class Plot(QtWidgets.QWidget):
        def paintEvent(self, event):
            before = state()
            if timer.interval() != 180: timer.setInterval(180)
            record('paint', before, state())

    plot = Plot()
    plot.resize(200, 100)
    plot.show()

    def timeout():
        before = state()
        record('timeout', before, state())
        if timer.interval() != 120:
            before = state(); timer.setInterval(120)
            record('prepare', before, state())
        plot.update()  # real deferred paint after the callback returns

    timer.timeout.connect(timeout)
    timer.start()
    QtCore.QTimer.singleShot(700, app.quit)
    app.exec()
    out = Path(__file__).resolve().parents[1]/'diagnosticos/resultados_v20/mixed_timer_20261103'
    out.mkdir(parents=True, exist_ok=True)
    (out/'timer_reset_probe.json').write_text(json.dumps(events, indent=2)+'\n')
    print(out/'timer_reset_probe.json')
    for e in events[:10]: print(e)


if __name__ == '__main__': main()
