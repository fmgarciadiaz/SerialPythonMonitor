"""Gradual digital level control, with immediate attenuation near DAC rails."""
import math
import numpy as np

RISE_DB_PER_SECOND=1.
FALL_DB_PER_SECOND=2.
UPDATE_SECONDS=.1
MAX_RAMP_SECONDS=.5
RAIL_MARGIN_VOLTS=.05


def target_gain(audio, gain, offset, *, elapsed=.2, allow_normal=True):
    values=np.asarray(audio,dtype=float)
    if (not len(values) or not np.isfinite(values).all()
            or not np.isfinite([gain,offset]).all() or gain<=0):return None
    headroom=min(offset-.5,2.8-offset)
    if headroom<=0:return None
    peak=float(np.max(abs(values-offset)))/gain
    # Avoid raising gain on silence; this cannot distinguish speech from noise.
    if peak<.001:return None
    desired=min(80.,max(1.,headroom/peak))
    emergency=float(np.min(values))<=RAIL_MARGIN_VOLTS or float(np.max(values))>=3.3-RAIL_MARGIN_VOLTS
    if emergency and desired<gain:
        # Round down: attenuation must not overshoot the requested headroom.
        reduced=max(1.,math.floor(desired*10)/10)
        return reduced if reduced<gain else None
    if not allow_normal or abs(desired-gain)<max(.1,gain*.05):return None
    if not math.isfinite(elapsed) or elapsed<=0:return None
    elapsed=min(elapsed,MAX_RAMP_SECONDS)
    speed=RISE_DB_PER_SECOND if desired>gain else -FALL_DB_PER_SECOND
    stepped=gain*10**(speed*elapsed/20)
    stepped=min(desired,stepped) if desired>gain else max(desired,stepped)
    value=round(stepped,1)
    return value if value!=gain else None
