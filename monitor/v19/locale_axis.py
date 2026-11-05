"""Localized numeric plot ticks without changing axis scaling."""
import pyqtgraph as pg
from monitor.v19.number_format import number

def time_unit(max_seconds):
    """Keep displayed magnitudes below 1000, using one unit per axis."""
    magnitude=abs(float(max_seconds))
    if magnitude>=1:return 's',1.
    if magnitude>=1e-3:return 'ms',1e-3
    if magnitude>=1e-6 or magnitude==0:return 'µs',1e-6
    return 'ns',1e-9

class LocaleAxis(pg.AxisItem):
    def set_time_label(self,text,base_seconds):
        self._time_text=text;self._time_base_seconds=base_seconds
        if base_seconds is None:
            if self.scale!=1.:self.setScale(1.)
            if self.labelText!=text or self.labelUnits:self.setLabel(text,units=None,color='#ffffff')
        else:
            self.enableAutoSIPrefix(False)
            self._update_time_scale()

    def _update_time_scale(self):
        base=getattr(self,'_time_base_seconds',None)
        if base is None:return
        unit,seconds=time_unit(max(abs(v) for v in self.range)*base)
        factor=base/seconds
        if self.scale!=factor:self.setScale(factor)
        if self.labelText!=self._time_text or self.labelUnits!=unit:
            self.setLabel(self._time_text,units=unit,color='#ffffff')

    def setRange(self,mn,mx):
        super().setRange(mn,mx)
        self._update_time_scale()

    def tickStrings(self, values, scale, spacing):
        labels = super().tickStrings(values, scale, spacing)
        result = []
        for label in labels:
            try:
                value = float(label)
            except ValueError:
                result.append(label)
            else:
                result.append(number(value))
        return result
