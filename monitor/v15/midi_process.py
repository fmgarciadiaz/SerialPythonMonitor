"""Asynchronous, timeout-bounded MIDI bridge for the Qt interface."""
import json
import sys
from pathlib import Path
from collections import deque
from types import SimpleNamespace
from PyQt6 import QtCore


class MidiProcess(QtCore.QObject):
    ports=QtCore.pyqtSignal(list)
    ready=QtCore.pyqtSignal()
    error=QtCore.pyqtSignal(str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.process=QtCore.QProcess(self)
        self.timeout=QtCore.QTimer(self);self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(lambda:self.fail('CoreMIDI no respondió en 8 segundos; volver a actualizar MIDI'))
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _:self.fail(self.process.errorString()))
        self.buffer=bytearray();self.messages=deque()
        self.closed=False;self.discover=False
        self.reply_received=False

    def start(self,port=None,virtual=False):
        self.discover=port is None
        args=[str(Path(__file__).with_name('midi_backend.py'))]
        args+=['--list'] if self.discover else ['--port',port]+(['--virtual'] if virtual else [])
        self.timeout.start(8000)
        self.process.start(sys.executable,args)

    def read_output(self):
        if self.closed:return
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.buffer)>2*1024*1024:
            self.fail('MIDI saturado: demasiados mensajes pendientes');return
        parsed=0
        while b'\n' in self.buffer and parsed<256:
            parsed+=1
            line,_,rest=self.buffer.partition(b'\n');self.buffer=bytearray(rest)
            try:record=json.loads(line)
            except (ValueError,UnicodeDecodeError):continue
            if 'error' in record:self.fail(record['error']);return
            if 'ports' in record:
                self.reply_received=True;self.timeout.stop();self.ports.emit(record['ports'])
            elif 'ready' in record:
                self.reply_received=True;self.timeout.stop();self.ready.emit()
            elif 'message' in record:
                if len(self.messages)>=4096:
                    self.fail('MIDI saturado: se cerró la entrada para evitar notas atascadas');return
                self.messages.append(SimpleNamespace(**record['message']))
        if b'\n' in self.buffer:QtCore.QTimer.singleShot(0,self.read_output)

    def iter_pending(self):
        for _ in range(min(128,len(self.messages))):yield self.messages.popleft()

    def finished(self,code,status):
        self.read_output()
        if not self.closed and (code or not self.discover or not self.reply_received):
            detail=bytes(self.process.readAllStandardError()).decode(errors='replace').strip()[-300:]
            self.fail('La entrada MIDI se cerró inesperadamente'+(': '+detail if detail else ''))
        self.timeout.stop()

    def fail(self,text):
        if self.closed:return
        self.close();self.error.emit(text)

    def close(self):
        if self.closed:return
        self.closed=True;self.timeout.stop();self.messages.clear()
        # Disconnect callbacks before killing: Qt can emit errors during teardown.
        for signal in (self.process.readyReadStandardOutput,self.process.errorOccurred,self.process.finished):
            try:signal.disconnect()
            except TypeError:pass
        if self.process.state()!=QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()
            # Only reap a killed child, never wait on a CoreMIDI operation.
            self.process.waitForFinished(100)
        QtCore.QTimer.singleShot(0,self.deleteLater)
