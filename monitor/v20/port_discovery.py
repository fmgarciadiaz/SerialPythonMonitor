"""Read-only discovery outside the GUI; results contain plain Python values."""
from threading import Thread
from PySide6 import QtCore


class PortDiscovery(QtCore.QObject):
    completed = QtCore.Signal(int, object, str)

    def start(self, generation, devices, ports):
        def discover():
            result = None
            error = ''
            try:
                found = list(devices())
                rows = [(p.device, p.description, p.vid, p.pid, p.serial_number)
                        for p in ports()]
                result = (found, rows)
            except Exception as exc:
                error = str(exc)
            try:
                self.completed.emit(generation, result, error)
            except RuntimeError:
                pass  # The window was destroyed while discovery was running.
        Thread(target=discover, name='v20-port-discovery', daemon=True).start()
