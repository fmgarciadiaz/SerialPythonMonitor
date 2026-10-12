"""Capture actual panel preset parameters without connecting MIDI or hardware."""
import os
from dataclasses import replace

def panel_presets(names,rate=20000):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PyQt6 import QtWidgets
    from types import SimpleNamespace
    from monitor.v16.fm_panel import FMPanel
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    generator_panel=QtWidgets.QWidget();QtWidgets.QGridLayout(generator_panel)
    owner=SimpleNamespace(generator_mode=QtWidgets.QComboBox(),generator_panel=generator_panel)
    panel=FMPanel(owner);result={}
    try:
        panel.output_rate.setCurrentIndex(panel.output_rate.findData(rate))
        for name in names:
            panel.preset.setCurrentText(name)
            result[name]=replace(panel.parameters(),notes=(),gate=False)
    finally:panel.close();panel.deleteLater();app.processEvents()
    return result
