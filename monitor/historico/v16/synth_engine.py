"""Motor anterior aislado; SYNTH_ENGINE=legacy selecciona la prueba V15; actual por defecto."""
import os
from dataclasses import fields
import numpy as np
from monitor.historico.v16.fm_source import FMParameters
from monitor.historico.v16.legacy_v15.fm_source import FMSource as LegacySource, FMParameters as LegacyParameters, MAX_VOICES as LEGACY_MAX_VOICES


class PreviousSource(LegacySource):
    def update(self, parameters):
        values = {field.name: getattr(parameters, field.name) for field in fields(LegacyParameters)}
        if values['notes'] is not None:
            values['notes'] = values['notes'][-LEGACY_MAX_VOICES:]
        levels = getattr(parameters, 'oscillator_levels', None)
        self._mix_gain = 1.0
        if levels is not None:
            first, second, third = levels
            self._mix_gain = first + second + third
            values['osc2_mix'] = second / (first + second) if first + second else 0.0
            values['osc3_mix'] = third / self._mix_gain if self._mix_gain else 0.0
        super().update(LegacyParameters(**values))

    def __init__(self, rate=40000, parameters=FMParameters()):
        # The legacy initializer retains its input as the previous parameter set.
        initial = LegacyParameters(**{field.name: getattr(parameters, field.name) for field in fields(LegacyParameters)})
        if initial.notes is not None:
            from dataclasses import replace
            initial = replace(initial, notes=initial.notes[-LEGACY_MAX_VOICES:])
        super().__init__(rate, initial)
        self.update(parameters)
        self.previous = self.parameters

    def render_dac_codes(self, start, end, amplitude, offset):
        return super().render_dac_codes(start, end, np.asarray(amplitude) * self._mix_gain, offset)

    def observe_midi_batch(self, messages):
        pass


ENGINE_NAME = 'actual' if os.environ.get('SYNTH_ENGINE') != 'legacy' else 'anterior V15'
if ENGINE_NAME == 'actual':
    from monitor.historico.v16.fm_source import FMSource, MAX_VOICES
else:
    FMSource = PreviousSource
    MAX_VOICES = LEGACY_MAX_VOICES
