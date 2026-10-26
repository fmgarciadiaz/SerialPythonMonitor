#!/usr/bin/env python3
"""Bounded live GUI smoke. Sole Q owner required; never deploys firmware.

Run only when explicitly authorized. Writes JSON evidence for paint events,
RF/DSP/GUI and Radio A0 transitions; backend handles snapshot/restoration.
"""
import argparse
from collections import deque
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import signal
import os
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from PyQt6 import QtCore, QtWidgets
from monitor.v18.app import SerialMonitorWindow


class PaintCounter(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent); self.events = 0
    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Paint: self.events += 1
        return False


def scan_capture_ready(window):
    # A generator/configuration boundary can arrive after the first RF samples.
    # At audio rates the first three blocks may still straddle that boundary.
    return (window.sample_counter>=3*65536 and
            window.sample_counter-3*65536>=getattr(window,'_radio_scan_not_before_sample',-1))


def close_ready(window):
    """Hidden UI is immediate; the receiver still owns Q until shutdown finishes."""
    thread=getattr(window,'serial_thread',None)
    return (not window.isVisible() and window.serial_worker is None
            and not getattr(window,'_close_pending',False)
            and (thread is None or not thread.isRunning()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--bits', type=int, default=8)
    parser.add_argument('--rate', type=int, default=1600000)
    parser.add_argument('--frequency-khz', type=float, default=550)
    parser.add_argument('--duration', type=float, default=32)
    parser.add_argument('--render-interval-ms', type=int, choices=range(16,251),
        help='Diagnostic override only; leaves product cadence unchanged')
    parser.add_argument('--profile-render',action='store_true',
        help='Profile one in ten render callbacks; diagnostic overhead only')
    parser.add_argument('--stall-trace', action='store_true',
        help='Dump all Python thread stacks after a 700 ms Qt heartbeat gap')
    parser.add_argument('--macos-activity',choices=('user','critical'),
        help='Diagnostic NSProcessInfo activity, scoped to this run')
    parser.add_argument('--hold-radio-seconds', type=float, default=0,
        help='Hold actual confirmed RADIO PLAYING for this many seconds before Stop')
    parser.add_argument('--fft-only',action='store_true',help='Raw RF FFT without RADIO playback or A0; requires --fft-size')
    parser.add_argument('--fft-size',type=int,choices=(16384,32768,65536))
    parser.add_argument('--fft-fixed-10',action='store_true',help='Diagnostic A/B only')
    parser.add_argument('--crop-radios',action='store_true')
    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--us', action='store_true',help='Exercise the multirate US scan')
    parser.add_argument('--wav', action='store_true')
    parser.add_argument('--fm', action='store_true')
    parser.add_argument('--voices', type=int, choices=range(1,21), default=1)
    parser.add_argument('--hide-at-seconds',type=float)
    parser.add_argument('--show-at-seconds',type=float)
    args = parser.parse_args()
    if args.fft_only and not args.fft_size:parser.error('--fft-only requires --fft-size')
    if (args.hide_at_seconds is None)!=(args.show_at_seconds is None) or (
            args.hide_at_seconds is not None and not 0<args.hide_at_seconds<args.show_at_seconds):
        parser.error('Hide/show times must be supplied together and ordered')
    stall_file=None
    if args.stall_trace:
        import faulthandler
        args.output.parent.mkdir(parents=True,exist_ok=True)
        stall_file=args.output.with_suffix('.stacks.txt').open('w')
    def arm_stall_trace():
        if stall_file is not None:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(.7,file=stall_file,repeat=False)
    audio_tail = 17 if args.fm else 11 if args.wav else 5
    import tempfile
    import wave
    import numpy as np
    wav_directory = tempfile.TemporaryDirectory(prefix='scope-v18-smoke-')
    wav_path = Path(wav_directory.name)/'smoke_500hz.wav'
    if args.wav:
        with wave.open(str(wav_path), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(20000)
            stream.writeframes((np.sin(2*np.pi*500*np.arange(80000)/20000)*8000).astype('<i2').tobytes())
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    evidence = dict(started=time.time(), stages=[], errors=[], paint_events=0,
        scan=dict(requested=False, completed=False, candidate_count=None), assertions={})
    statuses = deque(maxlen=2048)
    render_metrics=dict(frames=0,wall_seconds=0.,cpu_seconds=0.,max_wall_ms=0.,heartbeat_gap_max_ms=0.)
    import cProfile
    render_profile=cProfile.Profile() if args.profile_render else None
    class Window(SerialMonitorWindow):
        def _render_with_diagnostics(self):
            began=time.monotonic(); cpu=time.thread_time()
            profiling=render_profile is not None and render_metrics['frames']%10==0
            if profiling:render_profile.enable()
            try:
                return super()._render_with_diagnostics()
            finally:
                if profiling:render_profile.disable()
                wall=time.monotonic()-began
                render_metrics['frames']+=1
                render_metrics['wall_seconds']+=wall
                render_metrics['cpu_seconds']+=time.thread_time()-cpu
                render_metrics['max_wall_ms']=max(render_metrics['max_wall_ms'],wall*1000)
        def _publish_radio_scan(self, peaks):
            super()._publish_radio_scan(peaks)
            evidence['scan'].update(completed=True, candidate_count=len(peaks))
        def _on_worker_error(self, message):
            self._save_delivery_failure(str(message))
            evidence['errors'].append(str(message))
            scan=getattr(self,'_radio_multiscan',None)
            if scan is not None and scan.active:
                scan.error=f'Flujo interrumpido: {message}; restauración no confirmada'
                scan.timer.stop();scan.active=False;scan.future=None
                for widget,enabled in zip(scan.widgets,scan.enabled):widget.setEnabled(enabled)
            self._set_connection_status(str(message)); self.stop_input()
    window = Window()
    fft_metrics=dict(completed=0,wall_max_ms=0.,first_completed_at=None)
    if args.fft_size:
        display=window.spectral
        display.set_mode(1);display.fft_mode.setCurrentText('Radio')
        display.size.setCurrentText(str(args.fft_size));display.channels[0].setCurrentText('CH1');display.channels[1].setCurrentText('Ninguno')
        original_fft=display._render_fft_analysis
        def measured_fft(*values,**options):
            previous=display.last_end;began=time.perf_counter()
            try:return original_fft(*values,**options)
            finally:
                if display.last_end is not None and display.last_end!=previous:
                    fft_metrics['completed']+=1
                    if fft_metrics['first_completed_at'] is None:fft_metrics['first_completed_at']=time.monotonic()-start
                    fft_metrics['wall_max_ms']=max(fft_metrics['wall_max_ms'],(time.perf_counter()-began)*1000)
        display._render_fft_analysis=measured_fft
        if args.fft_fixed_10:
            from monitor.v18 import spectrum as spectrum_module
            normal_interval=spectrum_module.live_interval
            spectrum_module.live_interval=lambda mode,samples,connected,costs=(),**context:.1 if mode==1 and samples>=16384 and connected else normal_interval(mode,samples,connected,costs,**context)
        evidence['fft']=dict(size=args.fft_size,fixed_10=args.fft_fixed_10,crop_requested=args.crop_radios,a0_requested=not args.fft_only)
    if args.render_interval_ms is not None:
        window.render_timer.setInterval(args.render_interval_ms)
    evidence['render_interval_ms']=window.render_timer.interval()
    counter = PaintCounter(window)
    window.plot_widget.viewport().installEventFilter(counter)
    if args.fft_size:window.spectral.widget.viewport().installEventFilter(counter)
    start = time.monotonic()
    state = dict(connected=False, radio=False, a0=False, retuned=False, stopped=False,
                 closing=False, saved=False, scan=False, scan_recorded=False, wav_requested=False,
                 wav_play=False, radio_playing_at=None, radio_session=None, wav_session=None,
                 radio_stop_confirmed=False, radio_played=0, radio_accepted=0,
                 wav_stop_confirmed=False, wav_playing=False,
                 wav_progress=False, last_status_at=0., last_status_key=None, periodic_at=0.,
                 periodic_paints=0, stop_at=None, fm_requested=False, fm_play=False,
                 fm_playing=False, fm_session=None, fm_progress=False, fm_stop_confirmed=False,
                 last_tick=time.monotonic())
    def observe_wav(status):
        now = time.monotonic()-start
        value = int(status.state)
        if value==4 and window.serial_worker is not None:
            evidence['pcm_underrun']=getattr(window.serial_worker,'last_pcm_underrun',None)
        if state['a0'] and not state['wav_play'] and value == 2 and status.rate == 40000:
            if state['radio_playing_at'] is None:
                state['radio_playing_at'] = now
                state['radio_session'] = status.session
                record('radio_a0_playing_confirmed')
        if state['fm_play'] and value == 2 and status.session not in (state['radio_session'], state['wav_session']):
            if not state['fm_playing']: record('fm_playing_confirmed')
            state['fm_playing'] = True; state['fm_session'] = status.session
        if state['wav_play'] and not state['fm_play'] and value == 2 and status.session != state['radio_session']:
            if not state['wav_playing']: record('wav_playing_confirmed')
            state['wav_playing'] = True; state['wav_session'] = status.session
        if status.session == state['radio_session']:
            state['radio_played']=max(state['radio_played'], status.played)
            state['radio_accepted']=max(state['radio_accepted'], status.accepted)
        if status.session == state['radio_session'] and state['stopped'] and value in (0, 3):
            state['radio_stop_confirmed'] = True
        if status.session == state['wav_session']:
            state['wav_progress'] |= status.played > 0
            if value in (0, 3): state['wav_stop_confirmed'] = True
        if status.session == state['fm_session']:
            state['fm_progress'] |= status.played > 0
            if value in (0, 3): state['fm_stop_confirmed'] = True
        phase = ('fm' if status.session == state['fm_session'] else
                 'radio' if status.session == state['radio_session'] else
                 'wav' if status.session == state['wav_session'] else 'initial')
        key = (status.session, value, status.reason, phase)
        if key != state['last_status_key'] or now-state['last_status_at'] >= .5:
            statuses.append(dict(elapsed=now, phase=phase, **asdict(status)))
            state['last_status_key']=key; state['last_status_at']=now
        if phase in ('radio', 'wav', 'fm') and (value in (4, 5) or status.reason):
            evidence['errors'].append(f'{phase} status state={value} reason={status.reason}')
        if phase == 'radio' and state['radio_playing_at'] is not None and not state['stopped'] and value in (0, 3):
            evidence['errors'].append('Radio A0 stopped before the requested hold completed')

    def record(stage):
        source = window.radio_output_panel.source
        worker = window.serial_worker
        evidence['stages'].append(dict(stage=stage, elapsed=time.monotonic()-start,
            fft_metrics=dict(fft_metrics),fft_live_seconds=(time.monotonic()-start-fft_metrics['first_completed_at']) if fft_metrics['first_completed_at'] is not None else None,fft_costs_ms=[value*1000 for value in window.spectral._fft_render_costs],
            fft_deferred=window.spectral.deferred_live_timer_calls,fft_crop_active=window.spectral.radio_crop_active(0),
            render_metrics=dict(render_metrics),process_cpu_seconds=time.process_time(),
            samples=window.sample_counter, paint_events=counter.events,
            exposed=window.windowHandle().isExposed() if window.windowHandle() else False,
            radio_samples=getattr(window.radio_stream, 'counter', 0),
            batch_processing_count=window.batch_processing_count,
            pending_gui=getattr(worker, 'pending_batches', 0),
            rf_ipc_kind=getattr(worker,'last_rf_ipc_kind',None),
            pending_dsp=getattr(worker, 'pending_dsp', 0),
            pending_gui_peak=getattr(worker, 'pending_batches_peak', 0),
            pending_dsp_peak=getattr(worker, 'pending_dsp_peak', 0),
            gui_delay_max_ms=window.batch_queue_delay_max_ms,
            retained_seconds=getattr(getattr(worker, 'delivery_budget', None), 'seconds', 0),
            radio_playing_seconds=(time.monotonic()-start-state['radio_playing_at']) if state['radio_playing_at'] is not None and not state['stopped'] else None,
            wav_active=window._wav_active, radio_a0=source is not None,
            radio_a0_diagnostics=source.diagnostics() if source is not None else None,
            radio_status=window.radio_status.text(),rf_history_samples=len(window.series.get('CH1',())),
            scan_not_before_sample=getattr(window,'_radio_scan_not_before_sample',None),
            status=window.status_label.text()))
    def save():
        if state['saved']: return
        if stall_file is not None:faulthandler.cancel_dump_traceback_later()
        held = (state['stop_at']-state['radio_playing_at'] if state['stop_at'] is not None and state['radio_playing_at'] is not None else 0.)
        evidence['assertions'] = dict(
            radio_playing_40k=state['radio_playing_at'] is not None,
            radio_stop_confirmed=state['radio_stop_confirmed'],
            radio_progress=state['radio_played']>0,
            radio_hold_completed=held >= args.hold_radio_seconds,
            scan_completed=not args.scan or evidence['scan']['completed'],
            wav_playing=not args.wav or state['wav_playing'],
            wav_progress=not args.wav or state['wav_progress'],
            wav_stop_confirmed=not args.wav or state['wav_stop_confirmed'],
            fm_playing=not args.fm or state['fm_playing'],
            fm_progress=not args.fm or state['fm_progress'],
            fm_stop_confirmed=not args.fm or state['fm_stop_confirmed'],
            shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
            worker_released=window.serial_worker is None)
        if args.fft_only:
            evidence['assertions']=dict(
                fft_live_completed=fft_metrics['first_completed_at'] is not None and time.monotonic()-start-fft_metrics['first_completed_at']>=args.hold_radio_seconds,
                fft_progress=fft_metrics['completed']>1,
                a0_remained_off=not state['a0'] and not window._wav_active,
                scan_completed=not args.scan or evidence['scan']['completed'],
                shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
                worker_released=window.serial_worker is None)
        for name, passed in evidence['assertions'].items():
            if not passed: evidence['errors'].append(f'Assertion failed: {name}')
        evidence['radio_hold_seconds'] = held
        evidence['radio_played_samples'] = state['radio_played']
        evidence['radio_accepted_samples'] = state['radio_accepted']
        evidence['render_metrics']=dict(render_metrics)
        if render_profile is not None:
            import io,pstats
            profile_path=args.output.with_suffix('.render.pstats')
            render_profile.dump_stats(str(profile_path))
            summary=io.StringIO()
            pstats.Stats(render_profile,stream=summary).sort_stats('cumulative').print_stats(35)
            args.output.with_suffix('.render.txt').write_text(summary.getvalue())
            evidence['render_profile']=str(profile_path)
        evidence['wav_statuses'] = list(statuses)
        evidence.update(finished=time.time(), paint_events=counter.events,
            exposed=window.windowHandle().isExposed() if window.windowHandle() else False,
            shutdown_status=window._shutdown_status,
            closed=not window.isVisible(), worker_released=window.serial_worker is None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2, default=str)+'\n')
        print(json.dumps(dict(output=str(args.output), errors=evidence['errors'],
            paint_events=counter.events, shutdown_status=window._shutdown_status)), flush=True)
        state['saved']=True
        app.quit()
    save_complete=save
    def save():
        try:save_complete()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            evidence['errors'].append(f'Unable to save complete evidence: {type(exc).__name__}: {exc}')
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(evidence,indent=2,default=str)+'\n')
            state['saved']=True
            app.quit()
    documentation_frames=[]
    documentation_path=os.environ.get('MONITOR_V18_RADIO_GIF')
    documentation_at=[0.]
    def tick():
        now=time.monotonic()
        render_metrics['heartbeat_gap_max_ms']=max(render_metrics['heartbeat_gap_max_ms'],(now-state['last_tick'])*1000)
        state['last_tick']=now
        elapsed = now-start
        hold_start=fft_metrics['first_completed_at'] if args.fft_only else state['radio_playing_at']
        end_at = max(args.duration, (hold_start or 0)+args.hold_radio_seconds+audio_tail)
        try:
            if not state['closing'] and args.hide_at_seconds is not None:
                if elapsed>=args.hide_at_seconds and not state.get('occlusion_hidden'):
                    state['occlusion_hidden']=True;window.hide();record('occlusion_hidden')
                if elapsed>=args.show_at_seconds and not state.get('occlusion_shown'):
                    state['occlusion_shown']=True;window.show();record('occlusion_shown')
            if state['closing']:
                if stall_file is not None:faulthandler.cancel_dump_traceback_later()
                if close_ready(window):
                    save()
                elif elapsed>end_at+65 and not state['saved']:
                    if not state.get('close_timeout'):
                        state['close_timeout']=True
                        evidence['errors'].append('GUI close exceeded restoration deadline')
                        record('close_timeout')
                return
            arm_stall_trace()
            if (documentation_path and len(documentation_frames)<24 and
                    state['scan_recorded'] and window._wav_active and
                    window.spectral.radio_crop.isChecked() and elapsed-documentation_at[0]>=.2):
                documentation_at[0]=elapsed
                window.radio_frequency.setValue(args.frequency_khz)
                layout=window.spectral.radio_crop_columns()
                if layout:
                    station=min(layout,key=lambda column:abs(column.carrier-args.frequency_khz*1000))
                    full=layout[-1].left+1
                    width=min(full,5.4)
                    center=min(max(station.center,width/2),full-width/2)
                    # Use the normal persistent zoom controls: direct setXRange
                    # is overwritten by the next FFT frame and made the GIF jump.
                    window.spectral.change_view(h_scale=width/full,h_pos=center/full-.5)
                for index in range(window.trigger_filter_tabs.count()):
                    if window.trigger_filter_tabs.tabText(index).strip().lower()=='radio':
                        window.trigger_filter_tabs.setCurrentIndex(index)
                documentation_frames.append(window.grab().scaledToWidth(1000,QtCore.Qt.TransformationMode.SmoothTransformation).toImage())
            if elapsed-state['periodic_at'] >= 5:
                interval=elapsed-state['periodic_at']
                record('periodic')
                evidence['stages'][-1]['paint_fps_interval']=(counter.events-state['periodic_paints'])/interval
                with args.output.with_suffix('.progress.jsonl').open('a') as stream:
                    stream.write(json.dumps(evidence['stages'][-1],default=str)+'\n')
                state['periodic_at']=elapsed; state['periodic_paints']=counter.events
            if state['a0'] and state['radio_playing_at'] is None and elapsed>25:
                evidence['errors'].append('Radio A0 never confirmed PLAYING at 40 kHz')
            if not state['connected']:
                state['connected']=True
                if documentation_path:window.generator_mode.setCurrentIndex(7)
                window.port_combo.addItem(args.serial, args.serial)
                window.port_combo.setCurrentIndex(window.port_combo.count()-1)
                window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(args.bits))
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(args.rate))
                window.radio_output_rate.setCurrentIndex(window.radio_output_rate.findData(40000))
                window.connect_serial()
                if window.serial_worker is not None:
                    window.serial_worker.wav_confirmed.connect(observe_wav)
                record('connect_requested')
            if window.connection_state == 'connected' and not state['radio']:
                state['radio']=True
                if args.us:window.radio_us.setChecked(True)
                window.radio_frequency.setValue(args.frequency_khz)
                if not args.fft_only:window.radio_enabled.setChecked(True)
                record('fft_only' if args.fft_only else 'radio_play')
            if (args.scan and state['radio'] and not state['scan'] and elapsed>=5
                    and scan_capture_ready(window)):
                state['scan']=True; evidence['scan']['requested']=True
                window._radio_scan(); record('radio_scan')
            if evidence['scan']['completed'] and not state['scan_recorded']:
                state['scan_recorded']=True
                if args.crop_radios:
                    if window.spectral.radio_crop.isEnabled():window.spectral.radio_crop.setChecked(True)
                    else:evidence['errors'].append('Recorte no disponible: Scan no detectó emisoras válidas')
                record('radio_scan_completed')
                evidence['stages'][-1]['candidate_count']=evidence['scan']['candidate_count']
            if not args.fft_only and state['radio'] and not state['a0'] and elapsed>=7 and window._wav_capable and window._radio_scan_future is None and (not args.scan or evidence['scan']['completed']):
                state['a0']=True; window.radio_output_panel.toggle(); record('radio_a0_play')
            if state['a0'] and not state['retuned'] and elapsed>=13 and not documentation_path:
                state['retuned']=True
                window.radio_frequency.setValue(args.frequency_khz+1); record('radio_retune')
            if not state['stopped'] and elapsed>=end_at-audio_tail:
                state['stopped']=True; state['stop_at']=elapsed; record('before_stop')
                window.radio_output_panel.stop(); window.radio_enabled.setChecked(False)
            if args.wav and state['stopped'] and not state['wav_requested'] and not window._wav_active:
                state['wav_requested']=True
                window.generator_mode.setCurrentIndex(4)
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(40000))
                window.apply_output(); window._wav_file_selected(str(wav_path)); record('wav_configure')
            if state['wav_requested'] and not state['wav_play'] and window.applied_configuration.rate<=100000 and not window.output_pending and not window._auto_apply_timer.isActive():
                state['wav_play']=True; window._play_wav(); record('wav_play_requested')
            if args.wav and state['wav_play'] and elapsed>=end_at-(9 if args.fm else 2) and window._wav_active and not state['fm_requested']:
                record('wav_before_stop'); window._stop_wav()
            if args.fm and state['stopped'] and not state['fm_requested'] and not window._wav_active and (not args.wav or state['wav_playing']):
                state['fm_requested']=True
                window.generator_mode.setCurrentIndex(5)
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(40000))
                window.apply_output(); record('fm_configure')
            if state['fm_requested'] and not state['fm_play'] and window.applied_configuration.rate<=40000 and not window.output_pending and not window._auto_apply_timer.isActive():
                state['fm_play']=True; window.fm_panel.toggle()
                if window.fm_panel.source is not None and args.voices>1:
                    from dataclasses import replace
                    source=window.fm_panel.source
                    source.update(replace(source.parameters,notes=tuple((note,100) for note in range(48,48+args.voices))))
                record('fm_play_requested')
                evidence['stages'][-1]['requested_voices']=args.voices
            if state['fm_play'] and elapsed>=end_at-2 and window._wav_active:
                record('fm_before_stop'); window.fm_panel.toggle()
            if not state['closing'] and (elapsed>=end_at or evidence['errors']):
                # Keep the close-pending window visible until its worker has
                # restored Q, even if an error ended an occlusion experiment.
                if not window.isVisible():window.show()
                state['closing']=True; record('before_close'); window.close()
            if state['closing'] and close_ready(window): save()
            # Never terminate the owner while restoration is running; report a
            # timeout and keep waiting for its bounded backend shutdown.
            if elapsed>end_at+65 and not state['saved']:
                if not state.get('close_timeout'):
                    state['close_timeout']=True
                    evidence['errors'].append('GUI close exceeded restoration deadline')
                    record('close_timeout')
        except Exception as exc:
            evidence['errors'].append(f'{type(exc).__name__}: {exc}')
            state['closing']=True; window.close()
    activity=None
    if args.macos_activity:
        from tools.macos_activity_v18 import MacActivity
        activity=MacActivity(args.macos_activity)
        evidence['macos_activity']=dict(mode=args.macos_activity,active=activity.active)
    window.show()
    window.raise_()
    window.activateWindow()
    timer = QtCore.QTimer(); timer.timeout.connect(tick); timer.start(100)
    def interrupted(signum, frame):
        evidence['errors'].append(f'Interrupted by signal {signum}')
        state['closing']=True
        QtCore.QTimer.singleShot(0,window.close)
    previous_handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        app.exec()
    finally:
        if activity is not None:
            activity.close()
            evidence['macos_activity']['released']=not activity.active
            if state['saved']:
                args.output.write_text(json.dumps(evidence,indent=2,default=str)+'\n')
        for sig,handler in previous_handlers.items():signal.signal(sig,handler)
    if stall_file is not None:
        faulthandler.cancel_dump_traceback_later()
        stall_file.close()
    wav_directory.cleanup()
    if documentation_path and documentation_frames:
        from PIL import Image
        from PyQt6 import QtGui
        frames=[]
        for frame in documentation_frames:
            frame=frame.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            ptr=frame.bits();ptr.setsize(frame.sizeInBytes())
            frames.append(Image.frombytes('RGBA',(frame.width(),frame.height()),bytes(ptr)).convert('RGB'))
        destination=Path(documentation_path)
        frames[len(frames)//2].save(destination.with_suffix('.png'))
        frames[0].save(destination,save_all=True,append_images=frames[1:],duration=200,loop=0,optimize=True)
    return 1 if evidence['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
