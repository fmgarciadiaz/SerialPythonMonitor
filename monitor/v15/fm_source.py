"""Lazy, phase-continuous mono FM source for the existing credit-based DAC stream."""
from monitor.v15.fm_feedback import modulate, envelope_kernel
from dataclasses import dataclass, replace
from threading import Lock
from types import SimpleNamespace
from functools import lru_cache
import numpy as np
import time
import json
from scipy.signal import butter, sosfilt

# Inspired instrument patches, rather than sampled acoustic instruments.
PRESETS = {
    'Guitarra': (1.0,0,.001,.01,1.0,.12,0.,()),
    'Piano Virtual': (1.0,0,.001,.01,1.0,.22,0.,()),
    'Bass Punch': (1.0,0,.003,.18,.25,.08,0.,()),
    'Lead': (1.0,0,.008,.12,.8,.15,0.,()),
    'Brass': (1.0,0,.04,.28,.7,.2,0.,()),
    'Warm Pad': (1.0,0,.32,.6,.8,1.,0.,()),
    'Pluck': (1.0,0,.002,.38,0.,.12,0.,()),
    'Manual': (None,2.0,.008,.05,1.0,.025,0.0,()),
    'Flauta': (1.0,.22,.035,.12,.85,.18,.3,()),
    'Órgano': (2.0,.45,.008,.05,1.0,.08,0.0,((2,.22),(3,.12),(4,.06))),
    'DX Piano': (1.0,2.0,.003,3.4,0.0,.28,2.4,()),
    'Campana': (2.71,3.2,.002,2.5,0.0,.6,1.2,()),
    'DX Brillo': (1.0,2.8,.003,2.8,0.0,.25,1.8,()),
}

@lru_cache(maxsize=16)
def _sample_positions(count):
    values=np.arange(count,dtype=float);values.setflags(write=False)
    return values

@lru_cache(maxsize=256)
def _constant_values(value,count):
    values=np.full(count,value,dtype=float);values.setflags(write=False)
    return values

# Own subtractive patches: waveform, cutoff Hz, resonance Q, drive, wet mix, reference pitch.
MAX_VOICES = 9

@lru_cache(maxsize=4)
def _antialias_coefficients(rate,oversample):
    return butter(6,.45*rate,fs=rate*oversample,output="sos")

SYNTH_PATCHES = {
    'Bass Punch': ('saw',650,1.4,1.4,1.,110),
    'Lead': ('square',3200,.8,1.1,1.,440),
    'Brass': ('saw',2200,.9,1.1,1.,220),
    'Warm Pad': ('saw',1500,.7,1.,1.,220),
    'Pluck': ('triangle',3200,1.1,1.1,1.,440),
}
PRESETS = {name:PRESETS[name] for name in ('Manual','DX Piano','DX Brillo',*(k for k in PRESETS if k not in ('Manual','DX Piano','DX Brillo')))}



@dataclass(frozen=True)
class FMParameters:
    carrier: float = 440.0
    modulator: float = 220.0
    index: float = 2.0
    level: float = 1.0
    preset: str = 'Manual'
    gate: bool = True
    note_id: int = 0
    envelope: tuple | None = None  # attack/decay seconds, sustain level, release seconds
    notes: tuple | None = None  # (MIDI note, velocity); None selects the continuous voice.
    bell_ratio: float = 3.5
    bell_mix: float = 0.0
    brightness_decay: float = 0.7
    velocity_sensitivity: float = 0.65
    waveform: str = "fm"
    osc2_wave: str = "saw"
    osc2_mix: float = 0.0
    osc2_fm_ratio: float = 1.0
    virtual_model: str = "guitar"
    virtual_sustain: bool = False
    body_mix: float = .55
    bridge_coupling: float = .2
    string_stiffness: float = .0003
    string_decay: float = 3.0
    string_brightness: float = .65
    string_position: float = .22
    feedback: float = 0.0
    osc2_feedback: float = 0.0
    osc3_feedback: float = 0.0
    osc3_mix: float = 0.0
    osc3_ratio: float = 1.0
    osc3_amount: float = 1.4
    osc3_detune: float = -7.0
    osc3_envelope: tuple | None = None
    dx_body_detune: float | None = None
    osc2_fm_amount: float = 1.5
    osc2_detune: float = 0.0
    osc2_octave: int = 0
    filter_type: str = 'off'
    cutoff: float = 2000.
    resonance: float = .707
    drive: float = 1.
    filter_mix: float = 1.
    osc2_envelope: tuple | None = None
    note_ratio: float | None = None
    note_index: float | None = None
    fm_body_envelope: tuple | None = None
    fm_brightness_envelope: tuple | None = None


class FMSource:
    live = True
    # Protocol counters are uint32. One session lasts up to 24 h at 40 kHz.
    duration_seconds = 24 * 3600

    def __init__(self, rate=40000, parameters=FMParameters()):
        self.rate = rate
        self.oversample = 2 if rate>=40000 else 4
        self.lock = Lock()
        self.parameters = parameters
        self.update(parameters)
        self.previous = parameters
        self.carrier_phase = self.modulator_phase = self.bell_phase = self.osc2_phase = 0.0
        self.osc2_mod_phase=0.
        self.string=None
        self.physical_body=None
        self._string_model=None
        self.position = 0
        self.voices = {}
        self.finished_notes = set()
        self.compressor_gain = 1.0
        self.max_render_ms=0.
        self.slow_render_blocks=0
        self.filter_key = None
        self.filter_sos = None
        self.filter_zi = np.zeros((1,2))
        self.minimum_blocks = 5 if rate == 20000 else 16
        self.target_blocks = self.minimum_blocks
        # 120 ms at 20 kHz with a bounded two-chunk transport window.
        self.sos = _antialias_coefficients(rate,self.oversample)
        self.zi = np.zeros((len(self.sos),2))
        self.envelope_stage = 'attack' if parameters.gate else 'idle'
        self.envelope_position = 0
        self.envelope_start = self.envelope_value = 0.0
        self.osc2_envelope_state = SimpleNamespace(envelope_stage=self.envelope_stage,
            envelope_position=0,envelope_start=0.,envelope_value=0.)
        self.feedback_states=[np.zeros(2) for _ in range(3)]
        self.osc3_phase=self.osc3_mod_phase=0.0
        self.osc3_state=SimpleNamespace(envelope_stage=self.envelope_stage,envelope_position=0,envelope_start=0.,envelope_value=0.)
        self.fm_states=[SimpleNamespace(envelope_stage=self.envelope_stage,envelope_position=0,envelope_start=0.,envelope_value=0.) for _ in range(2)]
        self.note_age = 0
        self.note_level = parameters.level
        self.diagnostic_path = None
        self._last_ack = None
        self._last_log = -float('inf')
        self._max_ack_gap = 0.0
        self._min_queued = 16

    def observe_status(self, status):
        now=time.monotonic()
        if int(status.state)==2 and self._last_ack is not None:
            self._max_ack_gap=max(self._max_ack_gap,now-self._last_ack)
        self._last_ack=now if int(status.state)==2 else None
        if int(status.state)==2:self._min_queued=min(self._min_queued,16-status.free_blocks)
        if self.diagnostic_path is not None and (now-self._last_log>=5 or int(status.state) in (3,4,5) or status.reason):
            record=dict(time=now,state=int(status.state),reason=status.reason,accepted=status.accepted,
                        played=status.played,free_blocks=status.free_blocks,min_queued=self._min_queued,
                        queued_audio_ms=round((status.accepted-status.played)/self.rate*1000,3),
                        target_blocks=self.target_blocks,max_render_ms=round(self.max_render_ms,3),
                        slow_render_blocks=self.slow_render_blocks,
                        max_ack_gap_ms=round(self._max_ack_gap*1000,3),rate=status.rate)
            try:
                with self.diagnostic_path.open('a') as output:output.write(json.dumps(record)+'\n')
            except OSError: pass
            self._last_log=now

    def __len__(self): return self.rate * self.duration_seconds

    def update(self, parameters):
        if (parameters.filter_type not in ('off','lowpass','highpass','bandpass','notch') or
                not all(np.isfinite((parameters.cutoff,parameters.resonance,parameters.drive,parameters.filter_mix))) or
                not (20<=parameters.cutoff<=20000 and .5<=parameters.resonance<=8 and
                     1<=parameters.drive<=8 and 0<=parameters.filter_mix<=1)):
            raise ValueError('Filtro Synth fuera de rango')
        if parameters.virtual_model not in ("guitar","piano") or not (0<=parameters.body_mix<=1 and 0<=parameters.bridge_coupling<=1 and 0<=parameters.string_stiffness<=.002):
            raise ValueError("Modelo Virtual fuera de rango")
        if not (.05<=parameters.string_position<=.95 and .05<=parameters.string_brightness<=.95 and .1<=parameters.string_decay<=10):
            raise ValueError('Cuerda Virtual fuera de rango')
        if parameters.note_ratio is not None and not (np.isfinite(parameters.note_ratio) and .1<=parameters.note_ratio<=8):
            raise ValueError('Relación MIDI fuera de rango')
        if parameters.note_index is not None and not (np.isfinite(parameters.note_index) and 0<=parameters.note_index<=20):
            raise ValueError('Índice MIDI fuera de rango')
        if not (0<=parameters.osc3_mix<=1 and .1<=parameters.osc3_ratio<=31 and 0<=parameters.osc3_amount<=20 and -20<=parameters.osc3_detune<=20 and all(np.isfinite(f) and 0<=f<=7 for f in (parameters.feedback,parameters.osc2_feedback,parameters.osc3_feedback))):
            raise ValueError('Oscilador 3 o feedback fuera de rango')
        values = (parameters.carrier,parameters.modulator,parameters.index,parameters.level)
        if parameters.dx_body_detune is not None and not (np.isfinite(parameters.dx_body_detune) and -40<=parameters.dx_body_detune<=40):
            raise ValueError('Detune del cuerpo DX fuera de rango')
        if (parameters.osc2_wave not in ('fm','sine','square','triangle','saw') or
                not np.isfinite(parameters.osc2_fm_ratio) or not .1<=parameters.osc2_fm_ratio<=31 or
                not np.isfinite(parameters.osc2_fm_amount) or not 0<=parameters.osc2_fm_amount<=20 or
                not np.isfinite(parameters.osc2_mix) or not 0<=parameters.osc2_mix<=1 or
                not np.isfinite(parameters.osc2_detune) or not -20<=parameters.osc2_detune<=20 or
                parameters.osc2_octave not in (-1,0,1)):
            raise ValueError('Oscilador 2 fuera de rango')
        if parameters.waveform not in ("fm","sine","square","triangle","saw","virtual"):
            raise ValueError("Forma de onda Synth inválida")
        if parameters.preset not in PRESETS or not all(np.isfinite(values)) or not (0 <= parameters.carrier <= 10000 and
                0 < parameters.modulator <= 10000 and 0 <= parameters.index <= 20 and 0 <= parameters.level <= 1):
            raise ValueError('Parámetros FM fuera de rango')
        if (parameters.carrier + ((parameters.index+1)*parameters.modulator
                if parameters.waveform=="fm" else 0)) > self.rate*.4:
            raise ValueError('Banda FM demasiado amplia: bajar portadora, moduladora o índice')
        if not (0.1 <= parameters.bell_ratio <= 8 and 0 <= parameters.bell_mix <= 1
                and .001 <= parameters.brightness_decay <= 10 and 0 <= parameters.velocity_sensitivity <= 1):
            raise ValueError('Timbre FM fuera de rango')
        if parameters.notes is not None and (len(parameters.notes)>MAX_VOICES or
                any(not (0<=note<=127 and 0<velocity<=127) for note,velocity in parameters.notes)):
            raise ValueError('Notas FM fuera de rango')
        for envelope in (parameters.envelope,parameters.osc2_envelope,parameters.osc3_envelope,parameters.fm_body_envelope,parameters.fm_brightness_envelope):
            if envelope is None:continue
            if len(envelope) != 4 or not all(np.isfinite(envelope)):
                raise ValueError('Envolvente FM inválida')
            attack,decay,sustain,release = envelope
            if not (0 < attack <= 10 and 0 < decay <= 10 and 0 <= sustain <= 1 and 0 < release <= 10):
                raise ValueError('Envolvente FM fuera de rango')
        with self.lock: self.parameters = parameters

    def _envelope(self, count, parameters, state=None, envelope_override=None):
        state=self if state is None else state
        _,_,attack,decay,sustain,release,_,_ = PRESETS[parameters.preset]
        envelope=parameters.envelope if envelope_override is None else envelope_override
        if envelope is not None:
            attack,decay,sustain,release = envelope
        if parameters.preset in ('DX Piano','DX Brillo'):
            # Reference ADSR values are for A4; lower keys ring longer.
            key_scale=min(1.8,max(.6,(440/max(parameters.carrier,.1))**.35))
            decay*=key_scale*(.8+.2*self.note_level)
            release*=key_scale
        if envelope_kernel is not None:
            stages=('attack','decay','sustain','release','idle')
            result,stage,position,start,value=envelope_kernel(count,stages.index(state.envelope_stage),state.envelope_position,float(state.envelope_start),float(state.envelope_value),max(1,round(attack*self.rate*self.oversample)),max(1,round(decay*self.rate*self.oversample)),float(sustain),max(1,round(release*self.rate*self.oversample)))
            state.envelope_stage=stages[stage];state.envelope_position=position
            state.envelope_start=start;state.envelope_value=value
            return result
        output = np.empty(count)
        cursor = 0
        stages = {'attack':(attack,1.0,'decay'), 'decay':(decay,sustain,'sustain'),
                  'release':(release,0.0,'idle')}
        while cursor < count:
            stage = state.envelope_stage
            if stage in ('sustain','idle'):
                state.envelope_value = sustain if stage=='sustain' else 0
                output[cursor:] = state.envelope_value;break
            duration,target,next_stage = stages[stage]
            length = max(1,round(duration*self.rate*self.oversample))
            if state.envelope_position >= length:
                state.envelope_stage = next_stage
                state.envelope_position = 0
                state.envelope_start = state.envelope_value = target
                continue
            take = min(count-cursor,length-state.envelope_position)
            fraction = (state.envelope_position+np.arange(1,take+1))/length
            output[cursor:cursor+take] = state.envelope_start+(target-state.envelope_start)*fraction
            state.envelope_value = output[cursor+take-1]
            state.envelope_position += take;cursor += take
            if state.envelope_position >= length:
                state.envelope_stage = next_stage;state.envelope_position=0;state.envelope_start=target
        return output

    def __getitem__(self, selection):
        return self._render(selection)

    def _render(self, selection, quantize=True, internal=False):
        if not isinstance(selection,slice) or selection.step not in (None,1):
            raise ValueError('FM requiere bloques consecutivos')
        start,stop = selection.start,selection.stop
        if start != self.position or stop < start or stop > len(self):
            raise ValueError('Bloque FM fuera de secuencia')
        with self.lock: parameters = self.parameters
        if stop==start:return np.empty(0,dtype="<u2")
        if parameters.notes is not None:
            return self._poly_block(start,stop,parameters,quantize)
        count = (stop-start)*self.oversample
        if not count: return np.empty(0,dtype='<u2')
        # Live envelope edits must start from the actual current level, not an
        # elapsed index belonging to a longer stage in the previous patch.
        if (parameters.preset != self.previous.preset or
                parameters.envelope != self.previous.envelope):
            self.envelope_start = self.envelope_value
            self.envelope_position = 0
        changed_note = parameters.note_id != self.previous.note_id
        if parameters.gate and (changed_note or not self.previous.gate):
            self.envelope_stage='attack';self.envelope_start=self.envelope_value
            self.envelope_position=0;self.note_age=0
        elif not parameters.gate and self.previous.gate:
            self.envelope_stage='release';self.envelope_start=self.envelope_value;self.envelope_position=0
        state2=self.osc2_envelope_state
        if parameters.osc2_envelope!=self.previous.osc2_envelope or parameters.preset!=self.previous.preset:
            state2.envelope_start=state2.envelope_value;state2.envelope_position=0
        if parameters.gate and (changed_note or not self.previous.gate):
            state2.envelope_stage='attack';state2.envelope_start=state2.envelope_value;state2.envelope_position=0
        elif not parameters.gate and self.previous.gate:
            state2.envelope_stage='release';state2.envelope_start=state2.envelope_value;state2.envelope_position=0
        envelope1=self._envelope(count,parameters)
        if parameters.osc2_mix or self.previous.osc2_mix:
            envelope2=self._envelope(count,parameters,state2,parameters.osc2_envelope or parameters.envelope)
        else:
            envelope2=None
            state2.envelope_stage='idle';state2.envelope_value=0.
        if parameters.gate:self.note_level=parameters.level
        positions=_sample_positions(count)
        def ramp(a,b):
            return _constant_values(a,count) if a==b else np.linspace(a,b,count,endpoint=True)
        def phase(previous,a,b):
            if a==b:return previous+(positions+1)*(2*np.pi*b/(self.rate*self.oversample))
            return previous+np.cumsum(2*np.pi*ramp(a,b)/(self.rate*self.oversample))
        carrier = ramp(self.previous.carrier,parameters.carrier)
        modulator = ramp(self.previous.modulator,parameters.modulator)
        pc = phase(self.carrier_phase,self.previous.carrier,parameters.carrier)
        pm = phase(self.modulator_phase,self.previous.modulator,parameters.modulator)
        if parameters.waveform=='fm' or self.previous.waveform=='fm':
            _,_,_,_,_,_,brightness,harmonics = PRESETS[parameters.preset]
            index = ramp(self.previous.index,parameters.index).copy()
            brightness_curve=None
            if parameters.preset != 'Manual':
                index *= 1-parameters.velocity_sensitivity+parameters.velocity_sensitivity*self.note_level
                if brightness:
                    brightness=parameters.brightness_decay
                    age = (self.note_age+positions)/(self.rate*self.oversample)
                    brightness_curve=np.exp(-age/brightness)
                    index *= (.35+.65*brightness_curve if parameters.preset in ('DX Piano','DX Brillo') else .15+.85*brightness_curve)
            if parameters.preset in ('DX Piano','DX Brillo'):
                # Softer lower-register body; a harder strike adds harmonics.
                key_brightness=np.clip((440/max(parameters.carrier,.1))**.2,.65,1.35) if self.previous.carrier==parameters.carrier else np.clip((440/np.maximum(carrier,.1))**.2,.65,1.35)
                index*=key_brightness*(.55+.45*self.note_level)
            operator_envelopes=[]
            for name,state in zip(('fm_body_envelope','fm_brightness_envelope'),self.fm_states):
                envelope=getattr(parameters,name)
                if envelope is None:operator_envelopes.append(None);continue
                if envelope==parameters.envelope:
                    # Unified ADSR: share the already rendered curve instead of
                    # evaluating identical volume/body/brightness envelopes.
                    for field in ('envelope_stage','envelope_position','envelope_start','envelope_value'):
                        setattr(state,field,getattr(self,field))
                    operator_envelopes.append(envelope1)
                    continue
                if envelope!=getattr(self.previous,name):
                    state.envelope_start=state.envelope_value;state.envelope_position=0
                if parameters.gate and (changed_note or not self.previous.gate):
                    state.envelope_stage='attack';state.envelope_start=state.envelope_value;state.envelope_position=0
                elif not parameters.gate and self.previous.gate:
                    state.envelope_stage='release';state.envelope_start=state.envelope_value;state.envelope_position=0
                operator_envelopes.append(self._envelope(count,parameters,state,envelope))
            body_mod=index*modulate(pm,parameters.feedback,self.feedback_states[0])
            if operator_envelopes[0] is not None:body_mod*=operator_envelopes[0]
            mix=ramp(self.previous.bell_mix,parameters.bell_mix)
            three_operator=(parameters.preset in ('DX Piano','DX Brillo') and operator_envelopes[1] is not None and np.any(mix))
            signal=None if three_operator else np.sin(pc+body_mod)
            if parameters.dx_body_detune is not None and parameters.bell_ratio==1 and np.any(mix):
                # E.PIANO 1's extra 1:1 pair supplies beating beneath the
                # independent 14:1 tine pair. Cents are an approximation,
                # not Yamaha's discrete detune parameter units.
                body_ratio=2**(parameters.dx_body_detune/1200)
                body_phase=phase(self.bell_phase,self.previous.carrier*body_ratio,parameters.carrier*body_ratio)
                self.bell_phase=body_phase[-1]%(2*np.pi)
                detuned=np.sin(body_phase+.7*index*envelope1*np.sin(body_phase))
                signal=(1-mix)*signal+mix*detuned
            elif np.any(mix):
                # A second FM pair adds a fast metallic tine transient.
                age=(self.note_age+positions)/(self.rate*self.oversample)
                if self.previous.modulator==parameters.modulator and self.previous.bell_ratio==parameters.bell_ratio:
                    bell_phase=phase(self.bell_phase,parameters.modulator*parameters.bell_ratio,parameters.modulator*parameters.bell_ratio)
                else:
                    bell_phase=self.bell_phase+np.cumsum(2*np.pi*modulator*
                               ramp(self.previous.bell_ratio,parameters.bell_ratio)/(self.rate*self.oversample))
                self.bell_phase=bell_phase[-1]%(2*np.pi)
                piano=parameters.preset in ('DX Piano','DX Brillo')
                tine_carrier=carrier*(2 if piano else 1)
                # Tine sits an octave above the body. Fade it out before the
                # antialias margin in the high register, without changing pitch.
                headroom=np.clip((self.rate*.4-tine_carrier)/(self.rate*.08),0,1) if piano else 1
                bell_index=np.minimum(index, np.maximum(0,(self.rate*.4-tine_carrier)/
                                            np.maximum(modulator*parameters.bell_ratio,.1)-1))
                if piano and operator_envelopes[1] is not None:
                    # Three operators: one carrier and two parallel modulators.
                    metal=bell_index*operator_envelopes[1]*np.sin(bell_phase)
                    if brightness_curve is not None:metal*=brightness_curve
                    metal*=1-parameters.velocity_sensitivity+parameters.velocity_sensitivity*self.note_level
                    signal=np.sin(pc+(1-mix)*body_mod+mix*metal)
                else:
                    tine=np.sin(pc*(2 if piano else 1)+bell_index*np.exp(-age/parameters.brightness_decay)*np.sin(bell_phase))
                    if piano:
                        key_scale=np.clip(np.sqrt(440/max(parameters.carrier,.1)),.5,2) if self.previous.carrier==parameters.carrier else np.clip(np.sqrt(440/np.maximum(carrier,.1)),.5,2)
                        tine*=(1-np.exp(-age/.003))*np.exp(-age/(parameters.brightness_decay*key_scale))*headroom
                        tine*=1-parameters.velocity_sensitivity+parameters.velocity_sensitivity*self.note_level**2
                    signal=(1-mix)*signal+mix*tine
            for order,weight in harmonics:signal += weight*np.sin(order*pc)
            signal /= 1+sum(weight for _,weight in harmonics)
            fm_signal=signal
        else:
            fm_signal=None
        virtual_signal=None
        if parameters.waveform=='virtual' or self.previous.waveform=='virtual':
            from monitor.v15.virtual_string import PluckedString
            if self.string is None or changed_note or parameters.carrier!=self.string.frequency or self._string_model!=parameters.virtual_model or (parameters.gate and not self.previous.gate):
                if parameters.virtual_model=='piano':
                    from monitor.v15.virtual_instruments import PianoStrings
                    self.string=PianoStrings(self.rate,parameters.carrier,parameters.string_position,self.note_level,self.rate*.42)
                else:
                    from monitor.v15.virtual_instruments import GuitarStrings
                    self.string=GuitarStrings(self.rate*self.oversample,parameters.carrier,parameters.string_position,self.note_level)
                self._string_model=parameters.virtual_model
            if parameters.virtual_model=='piano':
                virtual_signal=self.string.render(count//self.oversample,parameters.string_brightness,parameters.string_decay,parameters.string_stiffness,parameters.bridge_coupling)
                virtual_signal=np.repeat(virtual_signal,self.oversample)
            else:virtual_signal=self.string.render(count,parameters.string_brightness,parameters.string_decay,parameters.bridge_coupling)
        signal=virtual_signal if parameters.waveform=='virtual' else self._oscillator(parameters.waveform,pc,carrier,fm_signal)
        if parameters.waveform != self.previous.waveform:
            previous=virtual_signal if self.previous.waveform=='virtual' else self._oscillator(self.previous.waveform,pc,carrier,fm_signal)
            blend=np.linspace(0,1,count)
            signal=previous+(signal-previous)*blend
        signal*=envelope1
        if parameters.osc2_mix or self.previous.osc2_mix:
            # Independent phase and smoothed tuning produce actual beat frequencies.
            old_ratio=2**(self.previous.osc2_octave+self.previous.osc2_detune/1200)
            ratio=2**(parameters.osc2_octave+parameters.osc2_detune/1200)
            frequency2=np.minimum(carrier*ramp(old_ratio,ratio),self.rate*.4)
            if self.previous.carrier==parameters.carrier and old_ratio==ratio:
                phase2=phase(self.osc2_phase,float(frequency2[0]),float(frequency2[0]))
            else:
                phase2=self.osc2_phase+np.cumsum(2*np.pi*frequency2/(self.rate*self.oversample))
            fm2=None
            if parameters.osc2_wave=='fm' or self.previous.osc2_wave=='fm':
                # Modulators are internal signals: using output Nyquist here
                # erased the 14:1 piano attack. Bound FM at the oversampled
                # rate and remove out-of-band output with the shared filter.
                fm_limit=self.rate*self.oversample*.4
                mod2=np.minimum(frequency2*ramp(self.previous.osc2_fm_ratio,parameters.osc2_fm_ratio),fm_limit)
                if self.previous.carrier==parameters.carrier and old_ratio==ratio and self.previous.osc2_fm_ratio==parameters.osc2_fm_ratio:
                    mod_phase2=phase(self.osc2_mod_phase,float(mod2[0]),float(mod2[0]))
                else:mod_phase2=self.osc2_mod_phase+np.cumsum(2*np.pi*mod2/(self.rate*self.oversample))
                amount2=np.minimum(ramp(self.previous.osc2_fm_amount,parameters.osc2_fm_amount),
                                   np.maximum(0,(fm_limit-frequency2)/np.maximum(mod2,.1)-1))
                if parameters.preset in ('DX Piano','DX Brillo'):
                    amount2*=1-parameters.velocity_sensitivity+parameters.velocity_sensitivity*self.note_level
                # Add tine attack below A3 without changing the middle register.
                low_depth=min(1.0,max(0.0,np.log2(220/max(parameters.carrier,.1))/2))
                if low_depth:
                    age=(self.note_age+positions)/(self.rate*self.oversample)
                    amount2*=1+.8*low_depth*np.exp(-age/.12)
                fm2=np.sin(phase2+amount2*envelope2*modulate(mod_phase2,parameters.osc2_feedback,self.feedback_states[1]))
                self.osc2_mod_phase=mod_phase2[-1]%(2*np.pi)
            second=self._oscillator(parameters.osc2_wave,phase2,frequency2,fm2)
            if parameters.osc2_wave!=self.previous.osc2_wave:
                old=self._oscillator(self.previous.osc2_wave,phase2,frequency2,fm2)
                second=old+(second-old)*ramp(0,1)
            mix=ramp(self.previous.osc2_mix,parameters.osc2_mix)
            signal=signal*(1-mix)+second*envelope2*mix
            self.osc2_phase=phase2[-1]%(2*np.pi)
        if parameters.osc3_mix or self.previous.osc3_mix:
            state=self.osc3_state
            if parameters.osc3_envelope!=self.previous.osc3_envelope:
                state.envelope_start=state.envelope_value;state.envelope_position=0
            if parameters.gate and (changed_note or not self.previous.gate):
                state.envelope_stage='attack';state.envelope_start=state.envelope_value;state.envelope_position=0
            elif not parameters.gate and self.previous.gate:
                state.envelope_stage='release';state.envelope_start=state.envelope_value;state.envelope_position=0
            env3=self._envelope(count,parameters,state,parameters.osc3_envelope or parameters.envelope)
            f3=carrier*ramp(2**(self.previous.osc3_detune/1200),2**(parameters.osc3_detune/1200))
            m3=np.minimum(f3*ramp(self.previous.osc3_ratio,parameters.osc3_ratio),self.rate*self.oversample*.4)
            if self.previous.carrier==parameters.carrier and self.previous.osc3_detune==parameters.osc3_detune:
                c3=phase(self.osc3_phase,float(f3[0]),float(f3[0]))
                if self.previous.osc3_ratio==parameters.osc3_ratio:
                    p3=phase(self.osc3_mod_phase,float(m3[0]),float(m3[0]))
                else:p3=self.osc3_mod_phase+np.cumsum(2*np.pi*m3/(self.rate*self.oversample))
            else:
                c3=self.osc3_phase+np.cumsum(2*np.pi*f3/(self.rate*self.oversample))
                p3=self.osc3_mod_phase+np.cumsum(2*np.pi*m3/(self.rate*self.oversample))
            a3=np.minimum(ramp(self.previous.osc3_amount,parameters.osc3_amount),np.maximum(0,(self.rate*self.oversample*.4-f3)/np.maximum(m3,.1)-1))
            if parameters.preset in ('DX Piano','DX Brillo') and parameters.carrier<220:
                low_depth=min(1.0,max(0.0,np.log2(220/max(parameters.carrier,.1))/2))
                a3*=1+.25*low_depth
            third=np.sin(c3+a3*env3*modulate(p3,parameters.osc3_feedback,self.feedback_states[2]))*env3
            mix3=ramp(self.previous.osc3_mix,parameters.osc3_mix)
            signal=(1-mix3)*signal+mix3*third
            self.osc3_phase=c3[-1]%(2*np.pi);self.osc3_mod_phase=p3[-1]%(2*np.pi)
        else:
            self.osc3_state.envelope_stage='idle';self.osc3_state.envelope_value=0.
        level = parameters.level if parameters.gate else self.note_level
        previous_level = self.previous.level if self.previous.gate else self.note_level
        signal *= ramp(previous_level,level)
        self.note_age += count
        if not internal:signal,self.zi = sosfilt(self.sos,signal,zi=self.zi)
        self.carrier_phase,self.modulator_phase = pc[-1]%(2*np.pi),pm[-1]%(2*np.pi)
        self.position = stop
        if internal:
            self.previous=parameters
            return signal
        signal=self._filter_audio(signal[::self.oversample],parameters)
        self.previous = parameters
        if not quantize:return signal
        return np.rint((signal.clip(-1,1)+1)*2047.5).astype('<u2')

    def _filter_audio(self,signal,parameters):
        if parameters.waveform=='virtual':
            from monitor.v15.virtual_instruments import InstrumentBody
            if self.physical_body is None or self.physical_body.model!=parameters.virtual_model:
                self.physical_body=InstrumentBody(self.rate,parameters.virtual_model)
            signal=self.physical_body.render(signal,parameters.body_mix,parameters.bridge_coupling,parameters.virtual_sustain)
        else:self.physical_body=None
        # One master biquad after voice mixing: four voices do not multiply its cost.
        if not len(signal):return signal
        if parameters.filter_type=='off' and self.filter_sos is None:
            self.filter_key=('off',min(parameters.cutoff,self.rate*.45),parameters.resonance)
            self._rendered_filter_key=self.filter_key
            return signal
        transition=np.minimum(np.arange(len(signal))/max(1,round(self.rate*.005)-1),1)
        cutoff=min(parameters.cutoff,self.rate*.45)
        key=(parameters.filter_type,cutoff,parameters.resonance)
        old_sos=self.filter_sos
        if key!=self.filter_key:
            if parameters.filter_type=='off':new_sos=None
            else:
                w=2*np.pi*cutoff/self.rate;c=np.cos(w);alpha=np.sin(w)/(2*parameters.resonance)
                if parameters.filter_type=='lowpass':b=((1-c)/2,1-c,(1-c)/2)
                elif parameters.filter_type=='highpass':b=((1+c)/2,-1-c,(1+c)/2)
                elif parameters.filter_type=='bandpass':b=(alpha,0,-alpha)
                else:b=(1,-2*c,1)
                new_sos=np.array([(*b,1+alpha,-2*c,1-alpha)])/(1+alpha)
            self.filter_sos=new_sos;self.filter_key=key
        if self.filter_sos is None:
            filtered=signal.copy()
            if old_sos is not None:
                old,_=sosfilt(old_sos,signal,zi=self.filter_zi)
                blend=transition;filtered=old+(signal-old)*blend
                self.filter_zi.fill(0)
        else:
            drive=np.linspace(self.previous.drive,parameters.drive,len(signal))
            driven=signal if np.all(drive==1) else np.tanh(signal*drive)/np.tanh(drive)
            filtered,zi=sosfilt(self.filter_sos,driven,zi=self.filter_zi)
            if key!=getattr(self,'_rendered_filter_key',None):
                old=signal if old_sos is None else sosfilt(old_sos,driven,zi=self.filter_zi)[0]
                blend=transition;filtered=old+(filtered-old)*blend
            self.filter_zi=zi
        self._rendered_filter_key=key
        wet=np.linspace(self.previous.filter_mix,parameters.filter_mix,len(signal))
        return signal+(filtered-signal)*wet

    def _oscillator(self,waveform,phase,frequency,fm_signal):
        if waveform=='fm':return fm_signal
        if waveform=='sine':return np.sin(phase)
        if waveform=='triangle':return 2/np.pi*np.arcsin(np.sin(phase))
        t=(phase/(2*np.pi))%1
        dt=np.maximum(frequency/(self.rate*self.oversample),1e-12)
        def blep(position):
            result=np.zeros_like(position)
            left=position<dt;right=position>1-dt
            x=position[left]/dt[left];result[left]=2*x-x*x-1
            x=(position[right]-1)/dt[right];result[right]=x*x+2*x+1
            return result
        if waveform=='saw':return 2*t-1-blep(t)
        return np.where(t<.5,1.,-1.)+blep(t)-blep((t+.5)%1)

    def render_dac_codes(self, start, end, amplitude, offset):
        # Apply volume before limiting, so quiet signals keep their exact shape.
        began=time.perf_counter()
        audio=self._render(slice(start,end),quantize=False)
        ac=audio*amplitude/2
        peak=float(np.max(np.abs(ac))) if len(ac) else 0.
        target=1. if peak<=.95 else (.95+(peak-.95)/6)/peak
        seconds=.003 if target<self.compressor_gain else .15
        gain=target+(self.compressor_gain-target)*np.exp(-np.arange(1,len(ac)+1)/(self.rate*seconds))
        if len(gain):self.compressor_gain=float(gain[-1])
        volts=ac*gain+offset
        low=volts<.35;high=volts>2.95
        volts[low]=.35-.05*np.tanh((.35-volts[low])/.05)
        volts[high]=2.95+.05*np.tanh((volts[high]-2.95)/.05)
        result=np.rint(volts*4095/3.3).clip(0,4095).astype('<u2')
        elapsed=time.perf_counter()-began
        self.max_render_ms=max(self.max_render_ms,elapsed*1000)
        self.slow_render_blocks+=int(elapsed>(end-start)/self.rate)
        return result

    def _poly_block(self,start,stop,parameters,quantize=True):
        held=dict(parameters.notes)
        self.finished_notes.intersection_update(held)
        retrigger=parameters.note_id!=self.previous.note_id
        newest=parameters.notes[-1][0] if parameters.notes else None
        if retrigger:self.finished_notes.discard(newest)
        created=set()
        ratio=parameters.note_ratio if parameters.note_ratio is not None else parameters.modulator/max(parameters.carrier,.1)
        requested_index=parameters.note_index if parameters.note_index is not None else parameters.index
        for note in held:
            if note in self.finished_notes:continue
            if note not in self.voices:
                if len(self.voices)>=MAX_VOICES:
                    victim=next((key for key in self.voices if key not in held),next(iter(self.voices)))
                    del self.voices[victim]
                frequency=min(10000,self.rate*.4-.1,440*2**((note-69)/12))
                modulator=min(10000,frequency*ratio,max(.1,self.rate*.4-frequency))
                index=min(requested_index,max(0,(self.rate*.4-frequency)/modulator-1))
                params=replace(parameters,notes=None,carrier=frequency,modulator=modulator,
                               index=index,level=held[note]/127,gate=True,note_id=0,filter_type="off")
                self.voices[note]=FMSource(self.rate,params)
                created.add(note)
        output=np.zeros((stop-start)*self.oversample)
        for note,voice in list(self.voices.items()):
            if parameters!=getattr(voice,'_parent_parameters',None):
                frequency=voice.parameters.carrier
                modulator=min(10000,frequency*ratio,max(.1,self.rate*.4-frequency))
                index=min(requested_index,max(0,(self.rate*.4-frequency)/modulator-1))
                voice_parameters=replace(parameters,notes=None,carrier=frequency,modulator=modulator,
                                     index=index,level=held.get(note,0)/127,gate=note in held,note_id=voice.parameters.note_id+int(retrigger and note==newest and note not in created),filter_type="off")
                if voice_parameters!=voice.parameters:voice.update(voice_parameters)
                voice._parent_parameters=parameters
            output+=voice._render(slice(voice.position,voice.position+stop-start),quantize=False,internal=True)
            silent1=voice.envelope_stage in ('idle','sustain') and voice.envelope_value==0
            silent2=not parameters.osc2_mix or (voice.osc2_envelope_state.envelope_stage in ('idle','sustain') and voice.osc2_envelope_state.envelope_value==0)
            silent3=not parameters.osc3_mix or (voice.osc3_state.envelope_stage in ('idle','sustain') and voice.osc3_state.envelope_value==0)
            if silent1 and silent2 and silent3:
                del self.voices[note]
                if note in held:self.finished_notes.add(note)
        # Fixed headroom prevents volume pumping as notes start and end.
        self.position=stop
        output,self.zi=sosfilt(self.sos,output,zi=self.zi)
        output=self._filter_audio(output[::self.oversample]*.9,parameters)
        self.previous=parameters
        if not quantize:return output
        return np.rint((np.clip(output,-1,1)+1)*2047.5).astype('<u2')
