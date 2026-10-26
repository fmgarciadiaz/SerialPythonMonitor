"""Conservative live FFT cadence; data acquisition and FFT resolution are unchanged."""
from math import isfinite


def live_interval(mode,samples,connected,costs=(),*,audio_active=False):
    ordinary=1/30 if mode==1 else .05
    if samples<16384 or not connected:return ordinary
    # Preserve the previous heavy-heatmap budget. FFT starts at the known 10 Hz.
    if mode!=1:return max(ordinary,.1)
    # Physical large-FFT/A0 trials exposed an intermittent underrun. Keep the
    # previous rendering budget during DAC playback until that path qualifies.
    if audio_active:return .1
    recent=tuple(costs)[-8:]
    light=(len(recent)==8 and all(isfinite(cost) and 0<=cost<=.025 for cost in recent))
    return 1/15 if light else .1
