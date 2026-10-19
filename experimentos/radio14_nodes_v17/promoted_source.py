"""Bounded live RADIO audio source for the existing 40 kHz A0 DAC stream."""
from collections import deque
from threading import Lock
import numpy as np
from monitor.v17.radio_loop_guard import RadioLoopGuard


def acquisition_error(config):
    # The maximum ADC14 profile lost a node with RADIO+A0; the candidate
    # CPU/send fix also underruns in repeated physical runs. Do not expose it
    # as a stable combined mode while that qualification remains open.
    if config.bits==14 and config.rate>851063:
        return 'Radio A0: en 14 bits usar adquisición de hasta 851,063 kHz; tasas mayores pendientes de validación conjunta'
    if config.rate>1600000:return 'Radio A0: adquisición máxima de 1,6 MHz'
    return None

class RadioDacSource:
    live = True
    radio_audio = True
    # 30 halfword blocks hold 360 ms: query credits every 40 ms instead of 4 ms.
    poll_interval = .04
    credit_window = 30
    chunk_interval = .006
    chunk_burst = 8
    rate = 40000
    minimum_blocks = 30
    maximum_blocks = 30
    duration_seconds = 24 * 3600

    def __init__(self, volume=.25, buffer_seconds=.5, input_source='RADIO', rate=40000):
        if rate not in (20000,40000):raise ValueError('Radio A0 admite 20 o 40 kHz')
        self.rate=rate
        # Preserve the 2x recovery cadence relative to a 480-sample DAC block.
        self.chunk_interval=240/rate
        if input_source not in ('RADIO','FILTER'):raise ValueError('Entrada Radio A0 inválida')
        self.input_source=input_source
        if not 0 <= volume <= 1:raise ValueError('Volumen Radio fuera de rango')
        if not 0 <= buffer_seconds <= .6:raise ValueError('Reserva Radio fuera de rango')
        self.prebuffer_samples = int(buffer_seconds*self.rate)
        self.buffer_minimum = None
        self.target_blocks = self.minimum_blocks
        self._lock = Lock()
        self._chunks = deque()
        self._available = 0
        self._position = 0
        self._key = None
        self._volume = self._previous_volume = float(volume)
        self.closed = False
        self.error = None
        self.clipped_samples = 0
        self.retunes = 0
        self.played = 0
        self.accepted = 0
        self.loop_guard = RadioLoopGuard(rate)

    def observe_input(self, values, rate):
        with self._lock:
            if self.closed or self.error:return
            if self.loop_guard.observe(values,rate):
                self.error='Radio A0: posible realimentación A0 → CH1; salida detenida'
                self._chunks.clear();self._available=0

    def __len__(self):return self.rate * self.duration_seconds

    def set_volume(self, value):
        if not 0 <= value <= 1:raise ValueError('Volumen Radio fuera de rango')
        with self._lock:self._volume = float(value)

    def observe_status(self, status):
        with self._lock:
            self.played = int(status.played)
            self.accepted = int(status.accepted)

    def feed_result(self, result):
        settings=result['settings']
        config=getattr(settings,'acquisition',None)
        if config is not None:
            error=acquisition_error(config)
            if error:
                with self._lock:
                    self.error=error;self._chunks.clear();self._available=0
                return
        audio = result.get('audio');key = result.get('radio_key')
        offset=settings.radio_offset
        if self.input_source=='FILTER':
            if settings.filter.source!='RADIO':
                with self._lock:self.error='Radio A0: seleccionar RADIO como fuente de FILTER'
                return
            audio=result.get('audio_filter')
            if audio is None or not len(audio):return
            offset=result.get('audio_filter_offset')
            if offset is None:
                with self._lock:self.error='Radio A0: FILTER sin referencia de nivel'
                return
            if key is not None:key=(*key,settings.filter)
        if audio is None or key is None:return
        values = np.asarray(audio, dtype=float) - offset
        with self._lock:
            if self.closed or self.error:return
            if key[2] != self.rate:
                self.error = f'Radio A0 requiere FS SALIDA de RADIO a {self.rate//1000} kHz';return
            if self._key != key:
                if self._key is not None:self.retunes += 1
                # Retuning discards old station audio, preserving the time reserve
                # with neutral output while the new DSP generation catches up.
                reserve=self._available if self._key is not None else 0
                self._chunks.clear()
                if reserve:self._chunks.append(np.zeros(reserve))
                self._key = key
            if not np.isfinite(values).all():
                self.error = 'Radio A0: audio inválido';return
            if self._available + len(values) > self.rate:
                self.error = 'Radio A0 atrasada: buffer de audio completo'
                self._chunks.clear();self._available = 0;return
            if len(values):self._chunks.append(values.copy());self._available += len(values)

    def try_codes(self, start, end, levels=None):
        # This source has its own volume. WAV/Synth amplitude must not scale it.
        with self._lock:
            if self.closed or self.error or self._available < end-start:return None
            if start != self._position:raise ValueError('Posición Radio A0 discontinua')
            count = end-start
            if not self._position and self._available < max(count,self.prebuffer_samples):return None
            parts=[];left=count
            while left:
                chunk=self._chunks.popleft();take=min(left,len(chunk))
                parts.append(chunk[:take]);left-=take
                if take<len(chunk):self._chunks.appendleft(chunk[take:])
            self._available-=count;self._position=end
            self.buffer_minimum=self._available if self.buffer_minimum is None else min(self.buffer_minimum,self._available)
            volume=(self._volume if self._previous_volume==self._volume else
                    np.linspace(self._previous_volume,self._volume,count))
            signal=np.concatenate(parts)*volume+1.65
            self._previous_volume=self._volume
            self.clipped_samples+=int(np.count_nonzero((signal<0)|(signal>3.3)))
            codes=np.rint(np.clip(signal,0,3.3)*(4095/3.3)).astype('<u2')
            self.loop_guard.sent(codes,start)
            return codes

    def render_dac_codes(self,start,end,amplitude,offset):
        return self.try_codes(start,end,(amplitude,offset))

    def diagnostics(self):
        with self._lock:
            return dict(input_source=self.input_source,played=self.played,accepted=self.accepted,
                        buffered_samples=self._available,buffer_minimum=self.buffer_minimum,
                        retunes=self.retunes,error=self.error,closed=self.closed,
                        loop_score=self.loop_guard.score,loop_hits=self.loop_guard.hits)

    def close(self):
        with self._lock:
            self.closed=True;self._chunks.clear();self._available=0


class HighRateRadioDacSource(RadioDacSource):
    """Qualified ADC14/851063 path; other formats retain their refill policy."""
    chunk_burst=16

    def observe_input(self, values, rate):
        # The single DSP owner runs correlation outside the audio buffer lock.
        with self._lock:
            if self.closed or self.error:return
        detected=self.loop_guard.observe(values,rate)
        with self._lock:
            if self.closed or self.error:return
            if detected:
                self.error='Radio A0: posible realimentación A0 → CH1; salida detenida'
                self._chunks.clear();self._available=0

