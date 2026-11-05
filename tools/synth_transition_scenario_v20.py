"""Bounded Synth acceptance clock for GUI probes; no product or Q operations."""
class SynthTransition:
    def __init__(self,prepare_timeout=120.,hold_seconds=5.,stop_timeout=10.):
        if hold_seconds not in (5,30,60):raise ValueError('Synth hold must be 5, 30 or 60 seconds')
        self.voice_observations=0;self.voice_min=None;self.voice_max=None
        self.prepare_timeout=prepare_timeout;self.hold_seconds=hold_seconds;self.stop_timeout=stop_timeout
        self.phase='idle';self.requested_at=None;self.playing_at=None;self.stop_requested_at=None
        self.stopped_at=None;self.session=None;self.deadline=None;self.played=0
    @property
    def pending(self):return self.phase in ('wait-play','playing','wait-stop')
    @property
    def complete(self):return self.phase=='complete'
    @property
    def hold_completed(self):
        return self.playing_at is not None and self.stop_requested_at is not None and self.stop_requested_at-self.playing_at>=self.hold_seconds
    def request(self,now):
        if self.phase!='idle':raise RuntimeError('Synth probe already requested')
        self.phase='wait-play';self.requested_at=now;self.deadline=now+self.prepare_timeout
    def observe(self,status,now,excluded_sessions=()):
        self._check_deadline(now)
        value=int(status.state)
        if self.phase=='wait-play':
            if status.session in excluded_sessions:return None
            if value in (4,5) or status.reason:
                raise RuntimeError(f'Synth startup state={value} reason={status.reason}')
            if value!=2:return None
            self.phase='playing';self.session=status.session;self.playing_at=now;self.deadline=None
            self.played=max(0,status.played);return 'playing'
        if status.session!=self.session:return None
        self.played=max(self.played,status.played)
        if self.phase in ('playing','wait-stop') and (value in (4,5) or status.reason):
            raise RuntimeError(f'Synth status state={value} reason={status.reason}')
        if self.phase=='playing' and value in (0,3):
            raise RuntimeError('Synth stopped before confirmed hold completed')
        if self.phase=='wait-stop' and value in (0,3):
            self.phase='complete';self.stopped_at=now;self.deadline=None;return 'stopped'
        return None
    def _check_deadline(self,now):
        if self.phase in ('wait-play','wait-stop') and now>self.deadline:
            label='nuevo PLAY tras preparación' if self.phase=='wait-play' else 'STOP confirmado'
            raise TimeoutError('Synth: plazo agotado esperando '+label)
    def action(self,now):
        self._check_deadline(now)
        if self.phase=='playing' and now-self.playing_at>=self.hold_seconds:
            self.phase='wait-stop';self.stop_requested_at=now;self.deadline=now+self.stop_timeout
            return 'stop'
        return None
    def observe_voices(self,count):
        if self.phase!='playing' or type(count) is not int or count<0:return
        self.voice_observations+=1
        self.voice_min=count if self.voice_min is None else min(self.voice_min,count)
        self.voice_max=count if self.voice_max is None else max(self.voice_max,count)
    def observed_voices_match(self,count):
        return self.voice_observations>0 and self.voice_min==count and self.voice_max==count
    def end_at(self,base,now):
        if self.pending:return max(base,now+2.)
        return max(base,(self.stopped_at+2.) if self.complete else base)
    def snapshot(self):
        return dict(phase=self.phase,requested_at=self.requested_at,playing_at=self.playing_at,
            stop_requested_at=self.stop_requested_at,stopped_at=self.stopped_at,session=self.session,
            played=self.played,prepare_timeout=self.prepare_timeout,hold_seconds=self.hold_seconds,
            stop_timeout=self.stop_timeout,hold_completed=self.hold_completed,complete=self.complete,
            voice_observations=self.voice_observations,voice_min=self.voice_min,voice_max=self.voice_max)


def preparation_snapshot(worker):
    task=getattr(worker,'_wav_prepare_task',None)
    requested=getattr(worker,'_wav_prepare_request',None);active=getattr(worker,'_wav_prepare_active',None)
    return dict(request_pending=requested is not None,task_present=task is not None,
        task_done=task.done() if task is not None else None,active=active is not None,
        requested_rate=requested[1] if requested is not None else None,
        active_rate=active[1] if active is not None else None,
        synth_process_created=getattr(worker,'_synth_process',None) is not None)


def source_snapshot(source):
    if source is None:return None
    return dict(preset=getattr(getattr(source,'parameters',None),'preset',None),
        waveform=getattr(getattr(source,'parameters',None),'waveform',None),
        oscillator_levels=getattr(getattr(source,'parameters',None),'oscillator_levels',None),
        rate=getattr(source,'rate',None),position=getattr(source,'position',None),
        configured_notes=len(getattr(getattr(source,'parameters',None),'notes',())),
        remote_active_voice_count=getattr(source,'remote_active_voice_count',None),
        max_render_ms=getattr(source,'max_render_ms',None),slow_render_blocks=getattr(source,'slow_render_blocks',None))


def configure_synth_rate(window,rate):
    """Select the real Synth UI rate only when its firmware capability is enabled."""
    if rate not in (20000,40000):raise ValueError('Synth DAC rate must be 20000 or 40000')
    combo=window.fm_panel.output_rate;index=combo.findData(rate)
    firmware=window.wav_rate;capability=firmware.findData(rate)
    if (index<0 or capability<0 or not combo.model().item(index).isEnabled()
            or not firmware.model().item(capability).isEnabled()):
        raise RuntimeError(f'Synth: tasa DAC {rate} no habilitada por la UI/firmware')
    combo.setCurrentIndex(index)
    if combo.currentData()!=rate:raise RuntimeError('Synth: selección de tasa DAC no aplicada')
    return combo.currentData()


def synth_probe_parameters(parameters,voices,profile='panel'):
    """Private load profile: defaults preserve the panel's percussive envelope."""
    from dataclasses import replace
    if type(voices) is not int or not 1<=voices<=20:
        raise ValueError('Synth probe voices must be 1..20')
    notes=tuple((note,100) for note in range(48,48+voices))
    if profile=='panel':return replace(parameters,notes=notes)
    if profile!='sustained-fm':raise ValueError('Unknown Synth probe profile')
    from monitor.v20.fm_source import FMParameters
    envelope=(.01,.05,.7,.1)
    return FMParameters(preset='Manual',waveform='fm',gate=True,notes=notes,
        envelope=envelope,fm_body_envelope=envelope,fm_brightness_envelope=envelope,
        oscillator_levels=(1.,0.,0.))
