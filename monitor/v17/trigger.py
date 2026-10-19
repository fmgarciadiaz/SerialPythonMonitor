"""Trigger crossing selection shared by the RF and audio display paths."""
import numpy as np


def last_trigger_crossing(values, level, rising, hysteresis):
    """Return the last crossing armed by up to ten preceding samples.

    Match the original min/max lookback, including rejection of windows
    containing NaN. Keep the common case of an immediately armed last crossing
    cheap; vectorize the fallback for noise with many unarmed crossings.
    """
    crosses = np.flatnonzero(
        ((values[1:] >= level) & (values[:-1] < level)) if rising else
        ((values[1:] <= level) & (values[:-1] > level))) + 1
    if not len(crosses):
        return None
    latest = int(crosses[-1])
    prior = values[max(0, latest-10):latest]
    if (np.min(prior) <= level-hysteresis if rising else
            np.max(prior) >= level+hysteresis):
        return latest
    candidates = crosses[:-1]
    armed = np.zeros(len(candidates), dtype=bool)
    has_nan = np.zeros(len(candidates), dtype=bool)
    for back in range(1, 11):
        indices = candidates-back
        valid = indices >= 0
        prior = values[np.maximum(indices, 0)]
        armed |= valid & ((prior <= level-hysteresis) if rising else
                          (prior >= level+hysteresis))
        has_nan |= valid & np.isnan(prior)
    accepted = np.flatnonzero(armed & ~has_nan)
    return int(candidates[accepted[-1]]) if len(accepted) else None
