"""Physical production GUI WAV recording: three bounded runs per ADC16 rate."""

import hashlib
import json
import sys
import time
import wave
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6 import QtCore, QtWidgets

from monitor.historico.v16.app import SerialMonitorWindow
from monitor.historico.v16.receiver.unoq_acquisition import Configuration
from monitor.historico.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.historico.v16.receiver.unoq_switch import Mode
from monitor.historico.v16.receiver.unoq_usb import Connection
from monitor.historico.v16.receiver.unoq_wav import State

SERIAL = '1060031107'
PROFILES = [Configuration(16, rate) for rate in (44101, 48004, 76226)]
REPEATS = 3
RECORD_MS = 29000  # Qt delivery may reach the production 30-second auto-stop.
OUTPUT = ROOT / 'diagnosticos/resultados_v16' / datetime.now().strftime(
    'wav_recording_live_%Y%m%d_%H%M%S.json')
report = {'scope': 'Production GUI stereo PCM16 recorder, 3 x 29 s per ADC16 rate; '
          'no generator stimulus or analog accuracy claim; 29-30 s windows',
          'cases': [], 'errors': [],
          'restored': False, 'ok': False,
          'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (ROOT/'monitor/historico/v16/app.py',
                                         ROOT/'monitor/historico/v16/receiver/unoq_config_decoder.py')}}


def save():
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')


def receive_prior():
    with Connection(SERIAL) as connection:
        receiver = OutputReceiver(connection, lambda batch: None)
        started = time.monotonic()
        while receiver.decoder.mode is None and time.monotonic() - started < 3:
            receiver.pump()
        if receiver.decoder.mode != Mode.SPI:
            raise RuntimeError('Q is not in SPI mode')
        receiver.select(Mode.SPI)
        prior = receiver.config
        generator = receiver.generator().active
        receiver.wav_request()
        deadline = time.monotonic() + 3
        while receiver.wav_pending and time.monotonic() < deadline:
            receiver.pump()
        if receiver.wav_pending or receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
            raise RuntimeError('WAV output is active or its state is unknown')
        return prior, generator


def restore(prior, generator):
    with Connection(SERIAL) as connection:
        receiver = OutputReceiver(connection, lambda batch: None)
        receiver.select(Mode.SPI)
        receiver.configure(prior)
        if receiver.generator().active != generator:
            receiver.generator(generator)
        exact = receiver.config == prior and receiver.generator().active == generator
        before = receiver.decoder.pairs
        started = time.monotonic()
        while time.monotonic() - started < 3:
            receiver.pump()
        report['restoration_integrity'] = {'seconds': time.monotonic()-started,
                                           'samples': receiver.decoder.pairs-before,
                                           'ok': receiver.decoder.pairs > before}
        return exact and report['restoration_integrity']['ok']


def main():
    save()
    prior, generator = receive_prior()
    report['prior'] = {'configuration': asdict(prior), 'generator': asdict(generator),
                       'wav_state': 'IDLE', 'mode': 'SPI'}
    save()
    active = {'index': -1, 'stopping': False, 'recording': False}
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    class Window(SerialMonitorWindow):
        def _on_worker_error(self, message):
            report['errors'].append(message)
            save()
            finish()

    window = Window()
    window.show()
    window.record_format_combo.setCurrentText('WAV')
    window.record_dc_checkbox.setChecked(False)
    cases = [(profile, repetition) for profile in PROFILES for repetition in range(1, REPEATS+1)]
    watchdog = QtCore.QTimer()
    watchdog.setSingleShot(True)

    def stop_done():
        if window.stop_input() is False:
            QtCore.QTimer.singleShot(100, stop_done)
        else:
            window.close()
            app.quit()

    def finish():
        if active['stopping']:
            return
        active['stopping'] = True
        watchdog.stop()
        if window.recording:
            window.stop_recording()
        stop_done()

    def complete():
        if active['stopping']:
            return
        case = report['cases'][-1]
        elapsed = time.perf_counter() - active['started']
        recording_before_stop = window.recording
        status_before_stop = window.record_status_label.text()
        window.stop_recording()
        path = Path(window.record_filename)
        case.update(elapsed_s=elapsed, samples=window.record_rows,
                    filename=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                    record_status=window.record_status_label.text(),
                    status_before_stop=status_before_stop,
                    recording_before_stop=recording_before_stop)
        with wave.open(str(path), 'rb') as reader:
            case.update(rate=reader.getframerate(), channels=reader.getnchannels(),
                        sample_width=reader.getsampwidth(), frames=reader.getnframes())
        profile, _ = cases[active['index']]
        auto_limit = (not recording_before_stop and elapsed >= 29.5 and
                      status_before_stop.startswith('Guardado:'))
        case['auto_limit'] = auto_limit
        normal_close = (recording_before_stop or auto_limit) and case['record_status'].startswith('Guardado:')
        case['ok'] = (normal_close and case['samples'] > profile.actual_rate*min(elapsed, 30)*.95 and
                      case['frames'] == case['samples'] and case['bytes'] > 44 and
                      case['rate'] == profile.rate and case['channels'] == 2 and
                      case['sample_width'] == 2 and not report['errors'])
        case['status'] = 'PASS' if case['ok'] else 'FAIL'
        save()
        print('CASE', case['status'], profile.rate, active['index']+1,
              case['frames'], flush=True)
        if not case['ok']:
            report['errors'].append('WAV file or delivery validation failed')
            finish()
        else:
            next_case()

    def record():
        if active['stopping']:
            return
        profile, repetition = cases[active['index']]
        if window.applied_configuration != profile or not window.record_btn.isEnabled():
            report['errors'].append('WAV profile or production recording gate not confirmed')
            finish()
            return
        case = {'configuration': asdict(profile), 'repetition': repetition,
                'status': 'RUNNING'}
        report['cases'].append(case)
        window.start_recording()
        if not window.recording:
            report['errors'].append('Production recorder did not start')
            finish()
            return
        active['started'] = time.perf_counter()
        save()
        print('RECORD', profile.rate, repetition, flush=True)
        QtCore.QTimer.singleShot(RECORD_MS, complete)

    def confirmed(bits, rate):
        if active['stopping'] or active['index'] < 0 or active['index'] >= len(cases):
            return
        profile, _ = cases[active['index']]
        if (bits, rate) == (profile.bits, profile.rate):
            watchdog.stop()
            QtCore.QTimer.singleShot(1000, record)

    def next_case():
        active['index'] += 1
        if active['index'] >= len(cases):
            finish()
            return
        profile, _ = cases[active['index']]
        watchdog.start(15000)
        if window.applied_configuration == profile:
            watchdog.stop()
            QtCore.QTimer.singleShot(1000, record)
        else:
            window.serial_worker.request_output(Mode.SPI, None, profile)

    watchdog.timeout.connect(lambda: (report['errors'].append('Configuration timeout'), finish()))
    try:
        port = window.port_combo.findData(SERIAL)
        if port < 0:
            raise RuntimeError('Q not available in GUI port selector')
        window.port_combo.setCurrentIndex(port)
        window.connect_serial()
        window.serial_worker.acquisition_confirmed.connect(confirmed)
        QtCore.QTimer.singleShot(3000, next_case)
        QtCore.QTimer.singleShot(330000, finish)
        print('LOOP START', flush=True)
        app.exec()
    except Exception as exc:
        report['errors'].append(str(exc))
        raise
    finally:
        if window.recording:
            window.stop_recording()
        if window.serial_thread is not None and window.serial_thread.isRunning():
            report['errors'].append('GUI worker still active; restore deferred')
        else:
            try:
                report['restored'] = restore(prior, generator)
            except Exception as exc:
                report['restore_error'] = str(exc)
        report['ok'] = (len(report['cases']) == len(cases) and
                        all(case.get('ok') for case in report['cases']) and
                        not report['errors'] and report['restored'])
        save()
        print('REPORT', OUTPUT, 'OK', report['ok'], 'RESTORED', report['restored'], flush=True)


if __name__ == '__main__':
    main()
