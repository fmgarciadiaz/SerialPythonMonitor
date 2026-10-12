"""Shared status sources and compact, tooltip-backed status boxes."""
from PyQt6 import QtCore, QtGui, QtWidgets


class StatusLabel(QtWidgets.QLabel):
    text_changed = QtCore.pyqtSignal(str)

    def setText(self, text):
        changed = text != self.text()
        super().setText(text)
        if changed:
            self.text_changed.emit(text)

    def clear(self):
        self.setText('')


class StatusValue(QtWidgets.QLabel):
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.WindowText))
        value = self.fontMetrics().elidedText(self.text(), QtCore.Qt.TextElideMode.ElideRight,
                                             self.contentsRect().width())
        painter.drawText(self.contentsRect(), QtCore.Qt.AlignmentFlag.AlignLeft |
                         QtCore.Qt.AlignmentFlag.AlignVCenter, value)


class StatusBox(QtWidgets.QFrame):
    def __init__(self, title):
        super().__init__()
        self.setFixedHeight(34)
        self.setMinimumWidth(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setStyleSheet('StatusBox {background:#171920; border:1px solid #323946; border-radius:6px;} '
                           'QLabel {background:transparent; border:none; padding:0; font-size:11px;}')
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(9,0,9,0);layout.setSpacing(7)
        label = QtWidgets.QLabel(f'{title} ·')
        label.setStyleSheet('color:#8793a5;')
        self.value = StatusValue()
        self.value.setStyleSheet('color:#aeb8c8;')
        self.value.setMinimumWidth(0)
        self.value.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(label);layout.addWidget(self.value,1)

    def update_status(self, text, detail=None):
        self.value.setText(text.replace('\n',' · '))
        self.setToolTip(detail or text)
