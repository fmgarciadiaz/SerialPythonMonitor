"""Single-owner continuous DSP, independent of Qt and display histories."""
from dataclasses import dataclass, replace
from time import perf_counter
import numpy as np
from monitor.v17.digital_filter import DigitalFilter, FilterConfig
from monitor.v17.radio_am import RadioConfig, radio_input_supported, radio_tuning_max
from monitor.v17.radio_stream import RadioStream
from monitor.v17.radio_tuning import alias_frequency, tuning_bounds
from monitor.v17.receiver.unoq_acquisition import Configuration

_process_owner = None


def initialize_process_owner():
    global _process_owner
    _process_owner = BatchProcessor()


def process_owner_ready():
    import os
    return os.getpid()


def process_owned_batch(batch, settings):
    return _process_owner.process(batch, settings)


def process_owned_result(batch, settings):
    """Return only DSP output; the parent already owns the RF columns."""
    result = process_owned_batch(batch, settings)
    return result.processing, result.columns.get('FILTER')


@dataclass(frozen=True)
class ProcessingSettings:
    generation: int = 0
    continuity_epoch: int = 0
    acquisition: Configuration = Configuration()
    filter: FilterConfig = FilterConfig(source='OFF')
    radio_enabled: bool = False
    radio_frequency: float = 550000
    audio_rate: int = 40000
    radio_gain: float = 2.0
    radio_offset: float = 1.65
    radio_bandwidth: float = 8000.
    radio_undersampling: bool = False

    @property
    def active(self):
        return self.radio_enabled or self.filter.source != 'OFF'


def same_audio_continuity(previous, current):
    """Level edits preserve audio only within an explicit structural epoch."""
    return (previous.continuity_epoch == current.continuity_epoch
        and replace(previous, generation=current.generation,
                    radio_gain=current.radio_gain, radio_offset=current.radio_offset) == current)


class BatchProcessor:
    """Used serially by one executor; never shares mutable DSP with the GUI."""
    def __init__(self):
        self.key = None
        self.rf_filter = DigitalFilter()
        self.audio_filter = DigitalFilter()
        self.radio = None
        self.previous_time = None

    def process(self, batch, settings):
        config = getattr(batch, 'acquisition', settings.acquisition)
        key = (settings, config)
        if self.key != key:
            previous,previous_config=self.key if self.key is not None else (None,None)
            levels_only=(previous is not None and previous_config==config
                and same_audio_continuity(previous, settings))
            if not levels_only:
                self.rf_filter.reset(); self.audio_filter.reset()
                self.radio = None; self.previous_time = None
            self.key = key
        columns = batch.columns
        timings = {}
        started = perf_counter()
        audio = None
        audio_filter = None
        audio_filter_offset = None
        radio_key = None
        radio_status = None
        audio_first_time_us = None
        if settings.radio_enabled:
            if not radio_input_supported(config):
                radio_status = 'RADIO requiere adquisición de al menos 20 kHz (entrada CH1).'
            elif not tuning_bounds(config.actual_rate,settings.radio_bandwidth,settings.radio_undersampling)[0] <= settings.radio_frequency <= tuning_bounds(config.actual_rate,settings.radio_bandwidth,settings.radio_undersampling)[1]:
                radio_status = 'RADIO · sintonía fuera de la banda de adquisición actual.'
            elif abs(abs((settings.radio_frequency+config.actual_rate/2)%config.actual_rate-config.actual_rate/2)-config.actual_rate/2)<=settings.radio_bandwidth/2:
                radio_status = 'RADIO · canal cruza Nyquist.'
            else:
                radio_key = (config.actual_rate, settings.radio_frequency, settings.audio_rate, settings.radio_bandwidth)
                if self.radio is None:
                    self.radio = RadioStream(RadioConfig(radio_key[0], alias_frequency(radio_key[0],radio_key[1],settings.radio_bandwidth,settings.radio_undersampling),settings.radio_bandwidth), radio_key[2])
                indices = columns.get('Muestra')
                if indices is not None and np.any((np.diff(indices.astype(np.int64)) & 0xffffffff) != 1):
                    raise ValueError('Discontinuidad RF')
                times = columns.get('Tiempo (us)')
                if times is not None and len(times):
                    delta = np.diff(times)
                    if self.previous_time is not None:
                        delta = np.r_[times[0]-self.previous_time, delta]
                    if np.any(abs(delta-1e6/config.actual_rate) > .01):
                        raise ValueError(f'Discontinuidad de tiempo RF: previo {self.previous_time}, primero {float(times[0])}, delta mínimo {float(delta.min())}, máximo {float(delta.max())}')
                    self.previous_time = float(times[-1])
                if not hasattr(self.radio,'rf_time_origin'):
                    self.radio.rf_time_origin=float(times[0]) if times is not None and len(times) else 0.
                audio_start=self.radio.resampler.output_count
                audio_first_time_us=self.radio.rf_time_origin+audio_start*(1e6/settings.audio_rate)
                demod_started = perf_counter()
                baseband = self.radio.demod.process(columns['CH1'], int(indices[0]) if indices is not None else None)
                timings['radio_demod_ms'] = (perf_counter()-demod_started)*1000
                resample_started = perf_counter()
                audio = self.radio.resampler.process(baseband)
                if settings.radio_gain != 1.0 or settings.radio_offset != 0.0:
                    audio = audio * settings.radio_gain + settings.radio_offset
                timings['radio_resample_ms'] = (perf_counter()-resample_started)*1000
                filter_started = perf_counter()
                if settings.filter.source == 'RADIO':
                    audio_filter = self.audio_filter.process(audio, settings.audio_rate,
                        replace(settings.filter, source='CH1'))
                    if len(audio):
                        sos=self.audio_filter.sos
                        dc_gain=1. if sos is None else float(np.prod(sos[:,:3].sum(axis=1)/sos[:,3:].sum(axis=1)))
                        audio_filter_offset=settings.radio_offset*dc_gain
                timings['audio_filter_ms'] = (perf_counter()-filter_started)*1000
        filter_started = perf_counter()
        if settings.filter.source in ('CH1', 'CH2'):
            columns['FILTER'] = self.rf_filter.process(columns[settings.filter.source],
                config.actual_rate, settings.filter, columns.get('Muestra'), columns.get('Tiempo (us)'))
        else:
            # Absence represents OFF/unavailable audio on the RF timeline.
            columns.pop('FILTER', None)
        timings['rf_filter_ms'] = (perf_counter()-filter_started)*1000
        timings['dsp_total_ms'] = (perf_counter()-started)*1000
        batch.processing = dict(generation=settings.generation, settings=settings,
            audio=audio, audio_filter=audio_filter, audio_filter_offset=audio_filter_offset, radio_key=radio_key,
            radio_status=radio_status, audio_first_time_us=audio_first_time_us, timings=timings)
        return batch
