"""Slow digital level control; never changes RF acquisition or A0 volume."""
import numpy as np


def target_gain(audio, gain, offset):
    values=np.asarray(audio,dtype=float)
    if not len(values) or not np.isfinite(values).all() or gain<=0:return None
    headroom=min(offset-.5,2.8-offset)
    if headroom<=0:return None
    peak=float(np.max(abs(values-offset)))/gain
    # Avoid raising gain on silence; this cannot distinguish speech from noise.
    if peak<.001:return None
    desired=min(80.,max(1.,headroom/peak))
    # Fast reduction, slow recovery, dead band to avoid constant generation churn.
    desired=min(desired,gain*1.5)
    return round(desired,1) if abs(desired-gain)>=max(.1,gain*.05) else None
