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
from PySide6 import QtCore, QtGui, QtWidgets
from monitor.v20.app import SerialMonitorWindow


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
    parser.add_argument('--radio-time-view',action='store_true',help='Display V(t) while exercising RADIO/A0; not an analysis-only probe')
    parser.add_argument('--stall-trace', action='store_true',
        help='Dump all Python thread stacks after a 700 ms Qt heartbeat gap')
    parser.add_argument('--macos-activity',choices=('user','critical'),
        help='Diagnostic NSProcessInfo activity, scoped to this run')
    parser.add_argument('--hold-radio-seconds', type=float, default=0,
        help='Hold actual confirmed RADIO PLAYING for this many seconds before Stop')
    parser.add_argument('--fft-only',action='store_true',help='Raw RF FFT without RADIO playback or A0; requires --fft-size')
    parser.add_argument('--fft-size',type=int,choices=(16384,32768,65536))
    parser.add_argument('--analysis-mode',choices=('vt','fft','heatmap','bode'))
    parser.add_argument('--time-channels',choices=('CH1','CH1+CH2'),help='Explicit RF-only V(t) selection')
    parser.add_argument('--fft-view',choices=('Spectre','Power','Distort','Transfer','Radio'),default='Spectre')
    parser.add_argument('--bode-method',type=int,choices=(0,1,2),default=0)
    parser.add_argument('--window-seconds',type=float,default=0,
        help='Diagnostic V(t) window in seconds; acquisition rate is unchanged')
    parser.add_argument('--detail-percent',type=int,choices=range(1,101),default=None)
    parser.add_argument('--fft-fixed-10',action='store_true',help='Diagnostic A/B only')
    parser.add_argument('--crop-radios',action='store_true')
    parser.add_argument('--restart-a0',action='store_true')
    parser.add_argument('--scan-during-a0',action='store_true')
    parser.add_argument('--no-retune',action='store_true')
    parser.add_argument('--panel-only',action='store_true',help='RADIO and Scan without A0')
    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--us', action='store_true',help='Exercise the multirate US scan')
    parser.add_argument('--wav', action='store_true')
    parser.add_argument('--fm', action='store_true')
    parser.add_argument('--voices', type=int, choices=range(1,21), default=1)
    parser.add_argument('--synth-hold',type=int,choices=(5,30,60),default=5)
    parser.add_argument('--synth-rate',type=int,choices=(20000,40000),default=20000)
    parser.add_argument('--synth-profile',choices=('panel','sustained-fm'),default='panel')
    parser.add_argument('--synth-early-play',action='store_true',help='Click Synth once while acquisition configuration is pending')
    parser.add_argument('--hide-at-seconds',type=float)
    parser.add_argument('--show-at-seconds',type=float)
    args = parser.parse_args()
    if args.time_channels and args.analysis_mode!='vt':parser.error('--time-channels requires --analysis-mode vt')
    if args.scan and args.scan_during_a0:parser.error('Choose Scan before or during A0')
    if args.radio_time_view and (args.analysis_mode or args.fft_only):parser.error('RADIO time view cannot use analysis-only criteria')
    if args.panel_only and (args.restart_a0 or args.scan_during_a0):parser.error('Transitions require A0')
    if args.fft_only and not args.fft_size:parser.error('--fft-only requires --fft-size')
    if (args.hide_at_seconds is None)!=(args.show_at_seconds is None) or (
            args.hide_at_seconds is not None and not 0<args.hide_at_seconds<args.show_at_seconds):
        parser.error('Hide/show times must be supplied together and ordered')
    stall_file=None
    if args.stall_trace:
        import faulthandler
        args.output.parent.mkdir(parents=True,exist_ok=True)
        stall_file=args.output.with_suffix('.stacks.txt').open('w')
        if hasattr(signal,'SIGUSR1'):
            faulthandler.register(signal.SIGUSR1,file=stall_file,all_threads=True)
    def arm_stall_trace():
        if stall_file is not None:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(.7,file=stall_file,repeat=False)
    audio_tail = 17 if args.fm else 11 if args.wav else 5
    import tempfile
    import wave
    import numpy as np
    wav_directory = tempfile.TemporaryDirectory(prefix='scope-v20-smoke-')
    wav_path = Path(wav_directory.name)/'smoke_500hz.wav'
    if args.wav:
        with wave.open(str(wav_path), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(20000)
            stream.writeframes((np.sin(2*np.pi*500*np.arange(80000)/20000)*8000).astype('<i2').tobytes())
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    evidence = dict(started=time.time(), stages=[], errors=[], paint_events=0,
        panel_only=args.panel_only,scan=dict(requested=False, completed=False, candidate_count=None), assertions={})
    from tools.radio_transition_scenario_v20 import RadioTransitions
    transitions=RadioTransitions(args.restart_a0,args.scan_during_a0)
    from tools.synth_transition_scenario_v20 import SynthTransition,preparation_snapshot,source_snapshot,configure_synth_rate
    synth_transition=SynthTransition(prepare_timeout=120.,hold_seconds=args.synth_hold,stop_timeout=10.)
    statuses = deque(maxlen=2048)
    render_metrics=dict(frames=0,wall_seconds=0.,cpu_seconds=0.,max_wall_ms=0.,heartbeat_gap_max_ms=0.)
    import cProfile
    render_profile=cProfile.Profile() if args.profile_render else None
    class Window(SerialMonitorWindow):
        def _render_with_diagnostics(self):
            previous_frame=getattr(self,'_last_display_frame',None)
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
                if (self.spectral.mode==0 and not getattr(getattr(self,'temporal_raster',None),'active',False)
                        and getattr(self,'_last_display_frame',None) is not previous_frame):
                    self._cadence_prepared_epoch=self.sample_counter
        def _publish_radio_scan(self, peaks):
            super()._publish_radio_scan(peaks)
            evidence['scan'].update(completed=True, candidate_count=len(peaks))
            if args.us:
                scan=self._radio_multiscan
                evidence['scan']['multirate']=dict(
                    rates=[c.rate for c in scan.configs],
                    captures=[fs for fs,_ in scan.scans],
                    restored=bool(scan.restore_confirmed and self.applied_configuration==scan.original),
                    error=scan.error)
        def _on_worker_error(self, message):
            self._save_delivery_failure(str(message))
            evidence['errors'].append(str(message))
            scan=getattr(self,'_radio_multiscan',None)
            if scan is not None and scan.active:
                scan.error=f'Flujo interrumpido: {message}; restauración no confirmada'
                scan.restore_confirmed=False
                scan.finish()
            self._set_connection_status(str(message)); self.stop_input()
    window = Window()
    if args.time_channels:
        chosen=args.time_channels.split('+')
        for name,action in window.graph_channel_actions.items():action.setChecked(name in chosen)
    cadence_paints=dict(events=0,new_data=0,last_epoch=None)
    original_paint_observer=window.plot_widget.paint_observer
    def observe_temporal_paint(milliseconds):
        original_paint_observer(milliseconds)
        cadence_paints['events']+=1
        epoch=getattr(window,'_cadence_prepared_epoch',None)
        if epoch is not None and epoch!=cadence_paints['last_epoch']:
            cadence_paints['new_data']+=1;cadence_paints['last_epoch']=epoch
    window.plot_widget.paint_observer=observe_temporal_paint
    if args.analysis_mode:
        mode={'vt':0,'fft':1,'heatmap':2,'bode':3}[args.analysis_mode]
        window.spectral.set_mode(mode)
        window.spectral.fft_mode.setCurrentText(args.fft_view)
        if args.analysis_mode=='fft' and not args.fft_size:
            args.fft_size=16384
            window.spectral.size.setCurrentText(str(args.fft_size))
        if args.analysis_mode=='bode':window.spectral.bode.tabs.setCurrentIndex(args.bode_method)
        if args.analysis_mode=='heatmap':window.spectral.channels[1].setCurrentText('CH2')
        if args.analysis_mode=='fft' and args.fft_view=='Transfer':
            window.spectral.transfer_reference.setCurrentText('CH1')
            window.spectral.transfer_response.setCurrentText('CH2')
    fft_metrics=dict(completed=0,wall_max_ms=0.,first_completed_at=None)
    if args.fft_size:
        display=window.spectral
        if not args.analysis_mode: display.set_mode(0 if args.radio_time_view else 1)
        display.fft_mode.setCurrentText(args.fft_view if args.analysis_mode else 'Radio')
        display.size.setCurrentText(str(args.fft_size));display.channels[0].setCurrentText('CH1')
        if not (args.analysis_mode=='heatmap' or (args.analysis_mode=='fft' and args.fft_view=='Transfer')):
            display.channels[1].setCurrentText('Ninguno')
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
            from monitor.v20 import spectrum as spectrum_module
            normal_interval=spectrum_module.live_interval
            spectrum_module.live_interval=lambda mode,samples,connected,costs=(),**context:.1 if mode==1 and samples>=16384 and connected else normal_interval(mode,samples,connected,costs,**context)
        evidence['fft']=dict(size=args.fft_size,fixed_10=args.fft_fixed_10,crop_requested=args.crop_radios,a0_requested=not args.fft_only)
    if args.render_interval_ms is not None:
        window.render_timer.setInterval(args.render_interval_ms)
    evidence['render_interval_ms']=window.render_timer.interval()
    counter = PaintCounter(window)
    fps_target=window.plot_widget.viewport() if window.spectral.mode==0 else window.spectral.widget.viewport()
    fps_target.installEventFilter(counter)
    evidence['fps_target']='vt_radio' if args.radio_time_view else args.analysis_mode or ('radio_fft' if args.fft_size else 'vt')
    start = time.monotonic()
    evidence['monotonic_started']=start
    state = dict(connected=False, radio=False, a0=False, retuned=False, stopped=False,
                 a0_request_at=None,closing=False, saved=False, scan=False, scan_recorded=False, wav_requested=False,
                 wav_play=False, radio_playing_at=None, radio_session=None, wav_session=None,
                 radio_stop_confirmed=False, radio_played=0, radio_accepted=0,
                 wav_stop_confirmed=False, wav_playing=False,
                 wav_progress=False, last_status_at=0., last_status_key=None, periodic_at=0.,
                 periodic_paints=0, stop_at=None, fm_requested=False, fm_play=False,
                 fm_playing=False, fm_session=None, fm_progress=False, fm_stop_confirmed=False,
                 fm_remote_voice_peak=0,
                 last_tick=time.monotonic(),bode_demo_at=0.,bode_demo_updates=0)
    state['long_window_configured']=False
    def observe_wav(status):
        now = time.monotonic()-start
        value = int(status.state)
        if value==4 and window.serial_worker is not None:
            evidence['pcm_underrun']=getattr(window.serial_worker,'last_pcm_underrun',None)
        if state['a0'] and not state['wav_play'] and value == 2 and status.rate == 40000:
            resumed=transitions.playing(status.session,now,evidence['scan']['completed'])
            if state['radio_playing_at'] is None or resumed:
                state['radio_playing_at'] = now
                state['radio_session'] = status.session
                state['radio_stop_confirmed']=False;state['radio_played']=0;state['radio_accepted']=0
                record('radio_a0_resumed' if resumed else 'radio_a0_playing_confirmed')
        try:fm_event=synth_transition.observe(status,now,(state['radio_session'],state['wav_session']))
        except (RuntimeError,TimeoutError) as exc:
            evidence['errors'].append(str(exc));fm_event=None
        if fm_event=='playing':
            state['fm_playing']=True;state['fm_session']=status.session
            record('fm_playing_confirmed')
        elif fm_event=='stopped':
            state['fm_stop_confirmed']=True
            record('fm_stop_confirmed')
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
        if phase == 'radio' and state['radio_playing_at'] is not None and not state['stopped'] and not transitions.expected_pause and value in (0, 3):
            evidence['errors'].append('Radio A0 stopped before the requested hold completed')

    def record(stage):
        source = window.radio_output_panel.source
        worker = window.serial_worker
        fm_source=source_snapshot(window.fm_panel.source)
        if fm_source is not None:
            state['fm_remote_voice_peak']=max(state['fm_remote_voice_peak'],fm_source['remote_active_voice_count'] or 0)
        finite_curve_points={}
        for name,curve in window.line_items.items():
            x,y=curve.getData()
            finite_curve_points[name]=(int(np.count_nonzero(np.isfinite(x)&np.isfinite(y)))
                                       if x is not None and y is not None else 0)
        raster=getattr(window,'temporal_raster',None)
        raster_visible=bool(raster is not None and raster.active and raster.item.isVisible())
        visible=getattr(window,'_visible_display_frame',None)
        if raster_visible and visible is not None:
            xs,ys,channels=visible
            for name in channels:
                x=xs.get(name,()) if isinstance(xs,dict) else xs;y=ys.get(name,())
                if len(x)==len(y):finite_curve_points[name]=int(np.count_nonzero(np.isfinite(x)&np.isfinite(y)))
        heatmap_finite_pixels=[]
        for image in getattr(window.spectral,'images',()):
            data=getattr(image,'image',None)
            heatmap_finite_pixels.append(int(np.count_nonzero(np.isfinite(data)))
                                         if data is not None else 0)
        fft_finite_points=[int(np.count_nonzero(np.isfinite(item[1])&np.isfinite(item[2])))
                           for item in getattr(window.spectral,'_fft_trace_cache',{}).values()]
        evidence['stages'].append(dict(stage=stage, elapsed=time.monotonic()-start,
            fft_metrics=dict(fft_metrics),fft_live_seconds=(time.monotonic()-start-fft_metrics['first_completed_at']) if fft_metrics['first_completed_at'] is not None else None,fft_costs_ms=[value*1000 for value in window.spectral._fft_render_costs],
            fft_deferred=window.spectral.deferred_live_timer_calls,fft_crop_active=window.spectral.radio_crop_active(0),
            render_metrics=dict(render_metrics),process_cpu_seconds=time.process_time(),
            samples=window.sample_counter, paint_events=counter.events,
            temporal_paints=dict(cadence_paints),
            temporal_prepare_ms=getattr(window,'_temporal_prepare_ms',0.),
            time_window_samples=window.h_scale,time_axis=window.x_axis_time_mode,
            trace_style=window.trace_style_combo.currentText(),trace_mode=window.trace_mode,
            applied_configuration=(dict(bits=window.applied_configuration.bits,
                rate=window.applied_configuration.rate,channels=window.applied_configuration.channels)
                if window.applied_configuration is not None else None),
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
            generator_mode=window.generator_mode.currentIndex(),
            radio_generator_visible=window.radio_output_panel.isVisible(),
            radio_eq_visible=window.radio_output_panel.audio_spectrum.isVisible(),
            radio_controls_visible=window.radio_panel.isVisible(),
            synth_transition=synth_transition.snapshot(),synth_preparation=preparation_snapshot(worker),
            synth_source=fm_source,
            radio_a0_diagnostics=source.diagnostics() if source is not None else None,
            radio_status=window.radio_status.text(),rf_history_samples=len(window.series.get('CH1',())),
            display_curve_points={name:(len(curve.xData) if curve.xData is not None else 0)
                                  for name,curve in window.line_items.items()},
            finite_curve_points=finite_curve_points,
            spectral_last_end=getattr(window.spectral,'last_end',None),
            fft_finite_points=fft_finite_points,
            heatmap_finite_pixels=heatmap_finite_pixels,
            heatmap_nonempty=[bool(image.image is not None and image.image.size)
                              for image in getattr(window.spectral,'images',())],
            raster_published=getattr(raster,'published',0),raster_visible=raster_visible,
            raster_worker_ms=getattr(raster,'last_ms',0),
            raster_capture_points={name:len(values) for name,values in (getattr(window,'_visible_display_frame',None) or (None,{},()))[1].items()},
            raster_worker_nice=getattr(getattr(raster,'worker',None),'last_priorities',None),
            raster_error=getattr(raster,'error_message',None),raster_busy=bool(raster and raster.worker and raster.worker.busy),
            raster_rejected=getattr(raster,'rejected',0),raster_last_rejection=getattr(raster,'last_rejection',[]),
            temporal_paint_ms=getattr(window,'_temporal_paint_ms',0),
            temporal_paint_max_ms=getattr(window,'_temporal_paint_max_ms',0),
            render_interval_ms=window.render_timer.interval(),
            detail=window.detail_slider.value(),trigger_enabled=window.trigger_enabled,
            scan_not_before_sample=getattr(window,'_radio_scan_not_before_sample',None),
            status=window.status_label.text()))
    def save():
        if state['saved']: return
        if stall_file is not None:faulthandler.cancel_dump_traceback_later()
        held = (state['stop_at']-state['radio_playing_at'] if state['stop_at'] is not None and state['radio_playing_at'] is not None else 0.)
        evidence['assertions'] = dict(
            radio_playing_40k=args.panel_only or state['radio_playing_at'] is not None,
            radio_stop_confirmed=args.panel_only or state['radio_stop_confirmed'],
            radio_progress=args.panel_only or state['radio_played']>0,
            radio_hold_completed=held >= args.hold_radio_seconds,
            scan_completed=not (args.scan or args.scan_during_a0) or evidence['scan']['completed'],
            wav_playing=not args.wav or state['wav_playing'],
            wav_progress=not args.wav or state['wav_progress'],
            wav_stop_confirmed=not args.wav or state['wav_stop_confirmed'],
            fm_playing=not args.fm or state['fm_playing'],
            fm_progress=not args.fm or state['fm_progress'],
            fm_stop_confirmed=not args.fm or state['fm_stop_confirmed'],
            fm_hold_completed=not args.fm or synth_transition.hold_completed,
            fm_configured_voices_rendered=not args.fm or args.voices<=1 or state['fm_remote_voice_peak']>=args.voices,
            fm_sustained_voices_observed=not args.fm or args.synth_profile=='panel' or synth_transition.observed_voices_match(args.voices),
            fm_selected_dac_rate=not args.fm or any(row.get('synth_source',{}).get('rate')==args.synth_rate
                for row in evidence['stages'] if row.get('synth_source')),
            shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
            worker_released=window.serial_worker is None)
        if not (args.panel_only or args.fft_only or args.analysis_mode):
            playing=[s for s in evidence['stages'] if s['stage'] in ('radio_a0_playing_confirmed','radio_a0_resumed')]
            evidence['assertions']['radio_generator_panel_visible']=bool(playing) and all(
                s.get('generator_mode')==7 and s.get('radio_generator_visible') and s.get('radio_eq_visible')
                and s.get('radio_controls_visible') for s in playing)
        if args.us:
            scan=evidence['scan'].get('multirate',{})
            evidence['assertions']['us_three_profiles_captured']=len(scan.get('rates',[]))==3 and len(scan.get('captures',[]))==3
            evidence['assertions']['us_original_restored']=scan.get('restored') is True and not scan.get('error')
        if args.restart_a0 or args.scan_during_a0:
            evidence['assertions']['a0_transitions_completed']=transitions.complete
        if args.panel_only:
            evidence['assertions']=dict(
                radio_panel_progress=any(s.get('radio_samples',0)>0 for s in evidence['stages']),
                scan_completed=not (args.scan or args.scan_during_a0) or evidence['scan']['completed'],
                a0_remained_off=not state['a0'],
                shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
                worker_released=window.serial_worker is None)
        if args.analysis_mode:
            periodic=[item for item in evidence['stages'] if item['stage']=='periodic']
            advanced=any(b['samples']>a['samples'] for a,b in zip(periodic,periodic[1:]))
            sampled=[item for item in periodic if item['samples']>0]
            latest=sampled[-1] if sampled else {}
            effective_seconds=(sampled[-1]['elapsed']-sampled[0]['elapsed']) if len(sampled)>1 else 0.
            expected=latest.get('applied_configuration') or {}
            spectral_advanced=any(a.get('spectral_last_end') is not None and
                b.get('spectral_last_end')!=a.get('spectral_last_end')
                for a,b in zip(sampled,sampled[1:]))
            mode_progress={
                'vt':bool(latest.get('finite_curve_points') and any(latest['finite_curve_points'].values())) or (
                    bool(latest.get('raster_visible')) and latest.get('raster_published',0)>0 and not latest.get('raster_error')),
                'fft':spectral_advanced and any(latest.get('fft_finite_points',())),
                'heatmap':spectral_advanced and bool(latest.get('heatmap_finite_pixels')) and (
                    all(latest['heatmap_finite_pixels']) if expected.get('channels')==2 else any(latest['heatmap_finite_pixels'])),
                'bode':state['bode_demo_updates']>0,
            }[args.analysis_mode]
            evidence['assertions']=dict(
                acquisition_configuration_applied=expected.get('bits')==args.bits and expected.get('rate')==args.rate,
                samples_advanced_between_observations=advanced,
                useful_sample_volume=latest.get('samples',0)>=65536,
                effective_acquisition_duration=effective_seconds>=min(5.,args.duration*.5),
                analysis_has_data=mode_progress,
                a0_remained_off=not state['a0'] and not window._wav_active,
                shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
                worker_released=window.serial_worker is None)
            evidence['analysis_effective_seconds']=effective_seconds
        elif args.fft_only:
            evidence['assertions']=dict(
                fft_live_completed=fft_metrics['first_completed_at'] is not None and time.monotonic()-start-fft_metrics['first_completed_at']>=args.hold_radio_seconds,
                fft_progress=fft_metrics['completed']>1,
                a0_remained_off=not state['a0'] and not window._wav_active,
                scan_completed=not (args.scan or args.scan_during_a0) or evidence['scan']['completed'],
                shutdown_confirmed=bool(window._shutdown_status and window._shutdown_status[0]),
                worker_released=window.serial_worker is None)
        if args.window_seconds>0:
            periodic=[s for s in evidence['stages'] if s['stage']=='periodic']
            latest=periodic[-1] if periodic else {}
            evidence['assertions']['requested_time_window_applied']=(
                latest.get('time_window_samples')==round(args.rate*args.window_seconds) and latest.get('time_axis') is True)
            if args.detail_percent is not None:
                evidence['assertions']['requested_detail_applied']=latest.get('detail')==args.detail_percent
        if args.detail_percent==100 and args.window_seconds>0:
            stages=evidence['stages']
            evidence['assertions']['temporal_raster_published']=any(s.get('raster_published',0)>0 and s.get('raster_visible') for s in stages)
            evidence['assertions']['temporal_raster_no_error']=not any(s.get('raster_error') for s in stages)
            if round(args.rate*args.window_seconds)>=100000:
                evidence['assertions']['cursor_frame_full_resolution']=any(s.get('raster_capture_points',{}).get('CH1')==round(args.rate*args.window_seconds) for s in stages)
        for name, passed in evidence['assertions'].items():
            if not passed: evidence['errors'].append(f'Assertion failed: {name}')
        evidence['radio_hold_seconds'] = held
        evidence['radio_played_samples'] = state['radio_played']
        evidence['radio_accepted_samples'] = state['radio_accepted']
        evidence['render_metrics']=dict(render_metrics)
        evidence['synth_transition']=synth_transition.snapshot()
        evidence['synth_remote_voice_peak']=state['fm_remote_voice_peak']
        if args.analysis_mode=='bode':evidence['synthetic_bode_updates']=state['bode_demo_updates']
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
    documentation_path=os.environ.get('MONITOR_V19_RADIO_GIF')
    documentation_at=[0.]
    def tick():
        now=time.monotonic()
        render_metrics['heartbeat_gap_max_ms']=max(render_metrics['heartbeat_gap_max_ms'],(now-state['last_tick'])*1000)
        state['last_tick']=now
        elapsed = now-start
        hold_start=fft_metrics['first_completed_at'] if args.fft_only else state['radio_playing_at']
        end_at = max(args.duration, (hold_start or 0)+args.hold_radio_seconds+audio_tail)
        if args.fm:end_at=synth_transition.end_at(end_at,elapsed)
        try:
            synth_transition.observe_voices(getattr(window.fm_panel.source,'remote_active_voice_count',None))
            if args.analysis_mode=='bode' and elapsed>=state['bode_demo_at']:
                state['bode_demo_at']=elapsed+.1
                phase=state['bode_demo_updates']*.025
                bode=window.spectral.bode.panels[window.spectral.bode.tabs.currentIndex()]
                bode.result=[(20.0*10**(i/48), -3.0-18.0*np.log10(1+(i/160)**2)+.25*np.sin(i*.08+phase),
                              -90.0*np.arctan(i/160)+1.5*np.sin(i*.03+phase)) for i in range(384)]
                bode.draw();state['bode_demo_updates']+=1
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
            if (state['a0'] and state['radio_playing_at'] is None and
                    elapsed-state['a0_request_at']>25):
                evidence['errors'].append('Radio A0 never confirmed PLAYING at 40 kHz')
            if not state['connected']:
                state['connected']=True
                if documentation_path or not (args.panel_only or args.fft_only or args.analysis_mode):
                    window.generator_mode.setCurrentIndex(7)
                if not (args.fft_only or args.analysis_mode):
                    window.trigger_filter_tabs.setCurrentWidget(window.radio_panel)
                window.port_combo.addItem(args.serial, args.serial)
                window.port_combo.setCurrentIndex(window.port_combo.count()-1)
                window.config_bits_combo.setCurrentIndex(window.config_bits_combo.findData(args.bits))
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(args.rate))
                window.radio_output_rate.setCurrentIndex(window.radio_output_rate.findData(40000))
                window.connect_serial()
                if window.serial_worker is not None:
                    window._worker_gui_bridge.connect_signal(window.serial_worker.wav_confirmed,observe_wav)
                record('connect_requested')
            if window.connection_state == 'connected' and not state['radio']:
                state['radio']=True
                if args.us:window.radio_us.setChecked(True)
                window.radio_frequency.setValue(args.frequency_khz)
                if not args.fft_only:window.radio_enabled.setChecked(True)
                record('fft_only' if args.fft_only else 'radio_play')
            if (args.window_seconds>0 and not state['long_window_configured'] and
                    window.connection_state=='connected' and window.applied_configuration is not None and
                    not window.output_pending and not window._auto_apply_timer.isActive()):
                if args.detail_percent is not None:window.detail_slider.setValue(args.detail_percent)
                window.btn_xaxis_toggle.setChecked(True)
                window.on_h_scale_changed(round(window.applied_configuration.rate*args.window_seconds))
                state['long_window_configured']=True
                record('long_time_window_configured')
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
            if not args.fft_only and not args.panel_only and state['radio'] and not state['a0'] and elapsed>=7 and window._wav_capable and window._radio_scan_future is None and (not args.scan or evidence['scan']['completed']) and not (
                    getattr(window,'_radio_multiscan',None) is not None and window._radio_multiscan.active
                    ) and window.applied_configuration.bits==args.bits and window.applied_configuration.rate==args.rate and not window.output_pending and not window._auto_apply_timer.isActive():
                window.radio_output_panel.toggle()
                if window.radio_output_panel.source is not None:
                    state['a0']=True;state['a0_request_at']=elapsed;record('radio_a0_play')
            if (state['a0'] and not args.no_retune and not state['retuned'] and state['radio_playing_at'] is not None
                    and elapsed-state['radio_playing_at']>=5.5 and not documentation_path):
                state['retuned']=True
                window.radio_frequency.setValue(args.frequency_khz+1); record('radio_retune')
            if state['a0'] and not state['stopped']:
                action=transitions.action(elapsed,not window._wav_active and not window.output_pending)
                if action=='stop':window.radio_output_panel.stop(reason='Ensayo STOP/reinicio');record('radio_restart_stop')
                elif action=='start':window.radio_output_panel.toggle();record('radio_restart_play')
                elif action=='scan':
                    state['scan']=True;evidence['scan']['requested']=True
                    window._radio_scan();record('radio_scan_while_a0')
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
            if args.fm and state['stopped'] and not state['fm_requested'] and (args.synth_early_play or not window._wav_active) and (not args.wav or state['wav_playing']):
                state['fm_requested']=True
                window.generator_mode.setCurrentIndex(5)
                window.config_rate_combo.setCurrentIndex(window.config_rate_combo.findData(40000))
                window.apply_output(); record('fm_configure')
            if state['fm_requested'] and not state['fm_play'] and (args.synth_early_play or window.applied_configuration.rate<=40000 and not window.output_pending and not window._auto_apply_timer.isActive()):
                configure_synth_rate(window,args.synth_rate)
                state['fm_play']=True;synth_transition.request(elapsed);window.fm_panel.toggle()
                if window.fm_panel.source is not None and (args.voices>1 or args.synth_profile!='panel'):
                    from tools.synth_transition_scenario_v20 import synth_probe_parameters
                    source=window.fm_panel.source
                    source.update(synth_probe_parameters(source.parameters,args.voices,args.synth_profile))
                record('fm_play_requested')
                evidence['stages'][-1]['requested_voices']=args.voices
                evidence['stages'][-1]['synth_profile']=args.synth_profile
                evidence['stages'][-1]['clicked_while_pending']=window.output_pending or window.applied_configuration.rate>40000
            if (args.synth_early_play and state['fm_play'] and not state.get('fm_parameters_applied')
                    and window.fm_panel.source is not None):
                from tools.synth_transition_scenario_v20 import synth_probe_parameters
                source=window.fm_panel.source
                source.update(synth_probe_parameters(source.parameters,args.voices,args.synth_profile))
                state['fm_parameters_applied']=True
            if synth_transition.action(elapsed)=='stop':
                record('fm_before_stop');window.fm_panel.toggle()
            if not state['closing'] and ((elapsed>=end_at and not synth_transition.pending) or evidence['errors']):
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
    screen=window.screen()
    evidence['display'] = dict(platform=QtGui.QGuiApplication.platformName(),
        dpr=window.devicePixelRatioF(), size=[window.width(),window.height()],
        screen=(screen.name() if screen else None), exposed=bool(window.windowHandle() and window.windowHandle().isExposed()))
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
        if hasattr(signal,'SIGUSR1'):faulthandler.unregister(signal.SIGUSR1)
        stall_file.close()
    wav_directory.cleanup()
    if documentation_path and documentation_frames:
        from PIL import Image
        frames=[]
        for frame in documentation_frames:
            frame=frame.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            ptr=frame.bits()
            frames.append(Image.frombytes('RGBA',(frame.width(),frame.height()),bytes(ptr)).convert('RGB'))
        destination=Path(documentation_path)
        frames[len(frames)//2].save(destination.with_suffix('.png'))
        frames[0].save(destination,save_all=True,append_images=frames[1:],duration=200,loop=0,optimize=True)
    return 1 if evidence['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
