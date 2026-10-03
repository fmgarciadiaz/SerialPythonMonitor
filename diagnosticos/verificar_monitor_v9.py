#!/usr/bin/env python3
"""Physical Qt/CSV test of V9: live SPI/UART/SPI and reconnect in both modes."""
import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PyQt5 import QtCore, QtWidgets
from monitor.historico.v9.app import SerialMonitorWindow
from transport.unoq_switch import Mode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--r4-port', required=True)
    args = parser.parse_args()
    app = QtWidgets.QApplication([])
    app.setStyle('Fusion')
    errors, confirmations = [], []
    sessions = []
    with tempfile.TemporaryDirectory(prefix='scope-v9-smoke-') as folder:
        class Window(SerialMonitorWindow):
            total = 0
            frames = 0
            last = None
            last_index = None
            def _on_worker_error(self, message):
                errors.append(message)
                self.close()
            def handle_batch(self, batch):
                for row in batch:
                    timestamp = int(row['Tiempo (us)'])
                    index = int(row['Muestra'])
                    if self.last is not None and (timestamp-self.last)&0xffffffff != 32:
                        errors.append('Hueco de timestamps entregados a Qt')
                    if self.last_index is not None and (index-self.last_index)&0xffffffff != 1:
                        errors.append('Hueco de índices entregados a Qt')
                    self.last, self.last_index = timestamp, index
                self.total += len(batch)
                super().handle_batch(batch)
            def render_frame(self):
                self.frames += 1
                super().render_frame()
            def _create_log_filename(self):
                return Path(folder)/'capture.csv'
            def _output_confirmed(self, mode, r4_port):
                super()._output_confirmed(mode, r4_port)
                confirmations.append(dict(mode=mode, r4=r4_port, pairs=self.total))
                print('Qt confirmó:', confirmations[-1], flush=True)
                count = len(confirmations)
                if count == 1:
                    self.start_recording()
                    QtCore.QTimer.singleShot(4000, lambda: change(Mode.UART))
                elif count == 2:
                    QtCore.QTimer.singleShot(4000, lambda: change(Mode.SPI))
                elif count == 3:
                    QtCore.QTimer.singleShot(4000, lambda: reconnect(Mode.UART))
                elif count == 4:
                    QtCore.QTimer.singleShot(4000, lambda: reconnect(Mode.SPI))
                elif count == 5:
                    QtCore.QTimer.singleShot(4000, self.close)
        window = Window()
        q_index = window.port_combo.findData(args.serial)
        r4_index = window.r4_combo.findData(args.r4_port)
        if q_index < 0 or r4_index < 0:
            raise RuntimeError('Q o R4 no aparecen en sus selectores')
        window.port_combo.setCurrentIndex(q_index)
        window.r4_combo.setCurrentIndex(r4_index)
        def change(mode):
            window.destination_combo.setCurrentIndex(window.destination_combo.findData(int(mode)))
            window.apply_output()
        def reconnect(mode):
            sessions.append(window.total)
            window.stop_input()
            window.last = window.last_index = None
            window.destination_combo.setCurrentIndex(window.destination_combo.findData(int(mode)))
            QtCore.QTimer.singleShot(500, window.connect_serial)
        window.show()
        window.connect_serial()
        QtCore.QTimer.singleShot(65000, lambda: (errors.append('Timeout de integración Qt'), window.close()))
        started = time.monotonic()
        app.exec_()
        elapsed = time.monotonic()-started
        rows = gaps = index_gaps = 0
        last = last_index = None
        capture = Path(folder)/'capture.csv'
        if capture.exists():
            with capture.open() as f:
                for row in csv.DictReader(f):
                    timestamp = int(float(row['Tiempo_us']))
                    index = int(float(row['Muestra']))
                    if last is not None: gaps += (timestamp-last)&0xffffffff != 32
                    if last_index is not None: index_gaps += (index-last_index)&0xffffffff != 1
                    last, last_index = timestamp, index
                    rows += 1
        report = dict(elapsed_seconds=elapsed, confirmations=confirmations,
                      total_pairs=window.total, render_calls=window.frames,
                      csv_rows=rows, csv_timestamp_gaps=gaps, csv_index_gaps=index_gaps,
                      errors=errors, session_totals=sessions,
                      sample_rate_hz=window.current_fs_hz)
        report['passed'] = bool(not errors and not gaps and not index_gaps and rows > 300000
                                and [c['mode'] for c in confirmations] == [0,1,0,1,0]
                                and len(sessions) == 2 and window.total-sessions[-1] > 80000
                                and window.frames > 200)
        output = ROOT/'diagnosticos/resultados_usb'
        output.mkdir(exist_ok=True)
        path = output/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_monitor_v9.json')
        path.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2), flush=True)
        print(path)
        return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
