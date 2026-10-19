"""Physical V16 Bode loopback without modifying calibration or firmware.

Requires A0 connected directly to both A2 and A3, with common ground and no
other Q reader. Runs the production tone estimator and causal FILTER path.
"""

import hashlib
import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.signal import sosfreqz, butter
from PyQt6 import QtWidgets

import monitor.v16.bode as bode_module
from monitor.v16.app import SerialMonitorWindow
from monitor.v16.bode_calibration import instrument_identity
from monitor.v16.receiver.unoq_acquisition import Configuration
from monitor.v16.receiver.unoq_config_receiver import OutputReceiver
from monitor.v16.receiver.unoq_switch import Mode
from monitor.v16.receiver.unoq_usb import Connection
from monitor.v16.receiver.unoq_wav import State

SERIAL = '1060031107'
PROFILE = Configuration(16, 76226)
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT = ROOT / 'diagnosticos/resultados_bode' / f'{STAMP}_bode_v16_loopback.json'
report = {'scope': 'V16 production Bode tones; A0 wired directly to A2/A3; '
          '1 Vpp centered at 1.65 V; raw uncalibrated CH2/CH1 and CH1/FILTER',
          'serial': SERIAL, 'profile': asdict(PROFILE), 'cases': [], 'errors': [],
          'restored': False, 'reference_written': False,
          'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (ROOT/'monitor/v16/bode.py', ROOT/'monitor/v16/digital_filter.py',
                                      ROOT/'monitor/v16/app.py',
                                      ROOT/'monitor/v16/bode_timing.py',
                                      ROOT/'monitor/v16/receiver/unoq_config_decoder.py')}}


def save():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')


def preflight():
    with Connection(SERIAL) as connection:
        receiver = OutputReceiver(connection, lambda batch: None)
        start = time.monotonic()
        while receiver.decoder.mode is None and time.monotonic()-start < 3:
            receiver.pump()
        if receiver.decoder.mode != Mode.SPI:
            raise RuntimeError('Q is not in SPI mode')
        receiver.select(Mode.SPI)
        prior = receiver.config
        generator = receiver.generator().active
        receiver.wav_request()
        deadline = time.monotonic()+3
        while receiver.wav_pending and time.monotonic()<deadline:
            receiver.pump()
        if receiver.wav_pending or receiver.wav_status is None or receiver.wav_status.state != State.IDLE:
            raise RuntimeError('WAV output active or unknown')
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
        start = time.monotonic()
        statuses = 0
        dropped = fatal = 0
        while time.monotonic()-start<3:
            receiver.pump()
            for status in receiver.decoder.statuses:
                statuses += 1
                dropped = max(dropped, status['dropped'])
                fatal = max(fatal, status['fatal'])
        report['restoration_integrity'] = {'seconds': time.monotonic()-start,
                                           'samples': receiver.decoder.pairs-before,
                                           'status_frames': statuses,
                                           'dropped': dropped, 'fatal': fatal,
                                           'ok': receiver.decoder.pairs>before and statuses>0
                                                 and dropped == 0 and fatal == 0}
        return exact and report['restoration_integrity']['ok']


def fit_diagnostics(t, vin, vout, frequency):
    angle = 2*np.pi*frequency*(np.asarray(t)-t[0])
    basis = np.column_stack((np.cos(angle), np.sin(angle), np.ones(len(t))))
    x = np.linalg.lstsq(basis, vin, rcond=None)[0]
    y = np.linalg.lstsq(basis, vout, rcond=None)[0]
    ax = float(np.hypot(x[0], x[1])); ay = float(np.hypot(y[0], y[1]))
    rx = float(np.std(vin-basis@x)); ry = float(np.std(vout-basis@y))
    return {'frequency_hz': frequency, 'samples': len(t), 'input_amplitude_vpk': ax,
            'output_amplitude_vpk': ay, 'input_residual_rms_v': rx,
            'output_residual_rms_v': ry,
            'input_fit_snr_db': float(20*np.log10(ax/(np.sqrt(2)*rx))) if rx else None,
            'output_fit_snr_db': float(20*np.log10(ay/(np.sqrt(2)*ry))) if ry else None}


def summarize_reference(cases):
    arrays = [np.asarray(c['curve'], dtype=float) for c in cases]
    if len(arrays)!=3 or not all(a.shape==arrays[0].shape for a in arrays):
        return {'accepted': False, 'reason': 'Need three complete common-grid captures'}
    if not np.allclose(arrays[0][:,0],arrays[1][:,0]) or not np.allclose(arrays[0][:,0],arrays[2][:,0]):
        return {'accepted': False, 'reason': 'Frequency grids differ'}
    reference_gain = (arrays[0][:,1]+arrays[1][:,1])/2
    phase_vectors = np.exp(1j*np.deg2rad(arrays[0][:,2]))+np.exp(1j*np.deg2rad(arrays[1][:,2]))
    reference_phase = np.angle(phase_vectors,deg=True)
    residual_gain = arrays[2][:,1]-reference_gain
    residual_phase = (arrays[2][:,2]-reference_phase+180)%360-180
    valid = np.isfinite(residual_gain)&np.isfinite(residual_phase)
    result = {'valid_fraction': float(np.mean(valid)), 'points': len(valid),
              'valid_points': int(valid.sum())}
    if not valid.any():
        result.update(accepted=False, reason='No valid held-out points')
        return result
    result.update(gain_abs_p95_db=float(np.percentile(abs(residual_gain[valid]),95)),
                  gain_abs_max_db=float(np.max(abs(residual_gain[valid]))),
                  phase_abs_p95_deg=float(np.percentile(abs(residual_phase[valid]),95)),
                  phase_abs_max_deg=float(np.max(abs(residual_phase[valid]))))
    result['accepted'] = (result['valid_fraction']>=.9 and
                          result['gain_abs_p95_db']<=.5 and result['gain_abs_max_db']<=1 and
                          result['phase_abs_p95_deg']<=2 and result['phase_abs_max_deg']<=5)
    return result


def main():
    global PROFILE
    parser = argparse.ArgumentParser()
    parser.add_argument('--bits', type=int, default=16)
    parser.add_argument('--rate', type=int, default=76226)
    args = parser.parse_args()
    PROFILE = Configuration(args.bits, args.rate)
    report['profile'] = asdict(PROFILE)
    save()
    report['instrument'] = instrument_identity(SERIAL)
    prior, generator = preflight()
    report['prior'] = {'configuration': asdict(prior), 'generator': asdict(generator),
                       'wav_state': 'IDLE', 'mode': 'SPI'}
    save()
    current = {'case': None}
    measurements = []
    original_tone_transfer = bode_module.tone_transfer

    def measured_transfer(t, vin, vout, frequency):
        gain, phase = original_tone_transfer(t, vin, vout, frequency)
        if current['case'] is not None:
            current['case']['fits'].append(fit_diagnostics(t, vin, vout, frequency))
        return gain, phase

    bode_module.tone_transfer = measured_transfer
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)

    class Window(SerialMonitorWindow):
        def __init__(self):
            self.previous_boundary = None
            self.continuity_errors = []
            self.pairs_received = 0
            super().__init__()

        def _acquisition_confirmed(self, bits, rate):
            self.previous_boundary = None
            super()._acquisition_confirmed(bits, rate)

        def handle_batch(self, batch):
            if hasattr(batch, 'columns'):
                index = np.asarray(batch.columns['Muestra'], dtype=np.int64)
                stamp = np.asarray(batch.columns['Tiempo (us)'], dtype=float)
                if len(index):
                    if np.any((np.diff(index)&0xffffffff)!=1):
                        self.continuity_errors.append('GUI index gap within batch')
                    if np.any(abs(np.diff(stamp)-self.applied_configuration.dt_us)>1.1e-6):
                        self.continuity_errors.append('GUI timestamp gap within batch')
                    if self.previous_boundary is not None:
                        old_index, old_stamp = self.previous_boundary
                        if ((int(index[0])-old_index)&0xffffffff)!=1:
                            self.continuity_errors.append('GUI index gap at batch boundary')
                        if abs(float(stamp[0])-old_stamp-self.applied_configuration.dt_us)>1.1e-6:
                            self.continuity_errors.append('GUI timestamp gap at batch boundary')
                    self.previous_boundary = int(index[-1]),float(stamp[-1])
            self.pairs_received += len(batch)
            super().handle_batch(batch)

        def _on_worker_error(self, message):
            report['errors'].append(message)
            save()
            self.stop_input()

    window = Window()
    window.generator_amplitude.setValue(1.0)
    window.generator_offset.setValue(1.65)
    window.generator_enabled.setChecked(False)
    window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(PROFILE.bits))
    window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(PROFILE.rate))
    window._auto_apply_timer.stop()
    window.show()

    def wait(predicate, timeout):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            app.processEvents()
            if report['errors'] or window.continuity_errors:
                raise RuntimeError(str(report['errors']+window.continuity_errors))
            if predicate():
                return
            time.sleep(.002)
        raise TimeoutError('Bode operation timed out')

    try:
        port = window.port_combo.findData(SERIAL)
        if port<0:
            raise RuntimeError('Q unavailable in V16 GUI selector')
        window.port_combo.setCurrentIndex(port)
        window.connect_serial()
        wait(lambda: window.applied_configuration==PROFILE and window._generator_state_known
             and not window.output_pending and window.sample_counter>0, 30)
        panel = window.spectral.bode.panels[0]
        window.spectral.select_bode(0)
        panel.correction.setChecked(True)
        panel.points.setValue(4)
        panel.cycles.setValue(8)
        panel.settle.setValue(300)

        def capture(label, start_hz, end_hz, pair, repetition):
            panel.reference_channel.setCurrentText(pair[0])
            panel.response_channel.setCurrentText(pair[1])
            panel.start.setValue(start_hz)
            panel.end.setValue(end_hz)
            wait(lambda: window._generator_requested is None, 10)
            case = {'label': label, 'pair': list(pair), 'repetition': repetition,
                    'range_hz': [start_hz,end_hz], 'fits': [], 'status': 'RUNNING',
                    'sample_counter_start': window.sample_counter}
            current['case'] = case
            report['cases'].append(case)
            save()
            began = time.monotonic()
            panel.begin()
            if not panel.active:
                raise RuntimeError('Bode did not start: '+panel.status.text())
            wait(lambda: not panel.active, 120)
            wait(lambda: window._generator_requested is None, 10)
            case.update(elapsed_s=time.monotonic()-began,
                        sample_count=window.sample_counter-case['sample_counter_start'],
                        status_text=panel.status.text(),
                        curve=np.asarray(panel.result,dtype=float).tolist(),
                        displayed_curve=panel.display_data(panel.result,len(panel.history),
                                                          panel.result_profile).tolist(),
                        invalid_points=panel.invalid_points)
            case['status'] = ('PASS' if case['status_text'].startswith('Barrido terminado')
                              and len(case['curve'])==len(panel.frequencies)
                              and not window.continuity_errors else 'FAIL')
            current['case'] = None
            save()
            print('BODE', label, repetition, case['status'],
                  len(case['curve']), '/', len(panel.frequencies), flush=True)
            if case['status']!='PASS':
                raise RuntimeError(case['status_text'])
            return case

        baseline = [capture('loopback_20_5000',20,5000,('CH1','CH2'),i)
                    for i in range(1,4)]
        report['held_out_reference'] = summarize_reference(baseline)
        save()
        capture('loopback_high',5000,min(20000,PROFILE.actual_rate*.4),('CH1','CH2'),1)
        window.filter_source.setCurrentText('CH1')
        window.filter_mode.setCurrentIndex(window.filter_mode.findData('lowpass'))
        window.filter_design.setCurrentIndex(window.filter_design.findData('Butterworth'))
        window.filter_order.setValue(2)
        window.filter_upper.setValue(1000)
        filter_case = capture('filter_20_5000',20,5000,('CH1','FILTER'),1)
        curve = np.asarray(filter_case['curve'],dtype=float)
        sos = butter(2,1000,btype='lowpass',fs=PROFILE.actual_rate,output='sos')
        _, transfer = sosfreqz(sos,worN=curve[:,0],fs=PROFILE.actual_rate)
        model_gain = 20*np.log10(abs(transfer))
        model_phase = np.angle(transfer,deg=True)
        valid = np.isfinite(curve[:,1])&np.isfinite(curve[:,2])
        gain_error = curve[valid,1]-model_gain[valid]
        phase_error = (curve[valid,2]-model_phase[valid]+180)%360-180
        report['filter_model'] = {'config': asdict(window.filter_config),
                                  'valid_points': int(valid.sum()), 'points': len(curve),
                                  'gain_abs_p95_db': float(np.percentile(abs(gain_error),95)) if valid.any() else None,
                                  'phase_abs_p95_deg': float(np.percentile(abs(phase_error),95)) if valid.any() else None,
                                  'theory': np.column_stack((curve[:,0],model_gain,model_phase)).tolist()}
        report['integrity_ok'] = not window.continuity_errors and not report['errors']
        report['measurement_complete'] = True
    except Exception as exc:
        report['errors'].append(str(exc))
        if current['case'] is not None:
            current['case'].update(status='FAIL',error=str(exc))
        save()
        raise
    finally:
        for panel in window.spectral.bode.panels:
            if panel.active:
                panel.cancel('Cierre del ensayo')
        bode_module.tone_transfer = original_tone_transfer
        if window.serial_worker is not None:
            window.stop_input(wait=False)
        heartbeat = time.monotonic()+10
        while window.serial_thread is not None and window.serial_thread.isRunning():
            app.processEvents()
            time.sleep(.01)
            if time.monotonic()>=heartbeat:
                print('WAITING FOR GUI WORKER TO CLOSE; no second Q reader opened',flush=True)
                heartbeat=time.monotonic()+10
        report['worker_finished'] = window.serial_thread is None or not window.serial_thread.isRunning()
        if report['worker_finished']:
            try:
                report['restored'] = restore(prior,generator)
            except Exception as exc:
                report['restore_error'] = str(exc)
        window.close()
        report['pairs_received'] = window.pairs_received
        report['continuity_errors'] = window.continuity_errors
        report['ok'] = (report.get('measurement_complete',False) and
                        report.get('integrity_ok',False) and report['restored'] and
                        report.get('held_out_reference',{}).get('accepted',False))
        save()
        print('REPORT',OUTPUT,'OK',report['ok'],'RESTORED',report['restored'],flush=True)


if __name__=='__main__':
    main()
