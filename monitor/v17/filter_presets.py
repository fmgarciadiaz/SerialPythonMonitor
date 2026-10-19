"""Named FILTER settings; applying a preset preserves the selected input."""
from dataclasses import replace
from monitor.v17.digital_filter import FilterConfig

# Band-reject edges are -3 dB points, not a guaranteed rejection interval.
FILTER_PRESETS = {
    'reject_50': ('Rechazo 50 Hz', FilterConfig(mode='bandstop', cutoff=49., upper=51.)),
    'reject_60': ('Rechazo 60 Hz', FilterConfig(mode='bandstop', cutoff=59., upper=61.)),
    'voice': ('Voz 300–3400 Hz', FilterConfig(mode='bandpass', cutoff=300., upper=3400.)),
    'audio_5k': ('Audio hasta 5 kHz', FilterConfig(mode='lowpass', cutoff=5000., upper=5000.)),
    'remove_dc': ('Quitar DC · 20 Hz', FilterConfig(mode='highpass', cutoff=20., upper=5000.)),
}


def apply_filter_preset(name, source='OFF'):
    """Return an immutable configuration without implicitly enabling FILTER."""
    return replace(FILTER_PRESETS[name][1], source=source)
