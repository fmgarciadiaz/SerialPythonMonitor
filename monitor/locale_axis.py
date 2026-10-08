"""Localized numeric plot ticks without changing axis scaling."""
import pyqtgraph as pg
from monitor.number_format import number

class LocaleAxis(pg.AxisItem):
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
