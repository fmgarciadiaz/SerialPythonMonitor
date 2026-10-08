"""Close each measured area independently, with vertical edges at data gaps."""
import numpy as np


def area_polygons(x, y, baseline):
    x, y = np.asarray(x), np.asarray(y)
    valid = np.isfinite(x) & np.isfinite(y)
    starts = np.flatnonzero(valid & ~np.r_[False, valid[:-1]])
    ends = np.flatnonzero(valid & ~np.r_[valid[1:], False])+1
    xs, ys = [], []
    for start, end in zip(starts, ends):
        if end-start < 2: continue
        xs.extend([x[start], *x[start:end], x[end-1], x[start], np.nan])
        ys.extend([baseline, *y[start:end], baseline, baseline, np.nan])
    return np.asarray(xs), np.asarray(ys)
