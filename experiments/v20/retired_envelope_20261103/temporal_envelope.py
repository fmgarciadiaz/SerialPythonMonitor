"""Display-only min/max columns. Input captures are never modified or reduced."""
import numpy as np

ENTER_SAMPLES_PER_PIXEL=8.
EXIT_SAMPLES_PER_PIXEL=4.
MIN_SAMPLES=100_000


def envelope_mode(count,pixels,active=False):
    threshold=EXIT_SAMPLES_PER_PIXEL if active else ENTER_SAMPLES_PER_PIXEL
    return count>=(MIN_SAMPLES//2 if active else MIN_SAMPLES) and count/max(1,pixels)>=threshold


def envelope_geometry(x,y,xmin,xmax,width,*,step=False,gap_cut=True,time_mode=True,dt=0.):
    """Vertical extrema per column/run, plus original boundary connections.

    NaNs and requested timestamp gaps split runs even inside one pixel.
    Nonmonotonic/nonfinite X falls back to the original point renderer.
    """
    x=np.asarray(x);y=np.asarray(y)
    if len(x)!=len(y) or len(x)<2 or width<1 or xmax<=xmin:return None
    if not np.isfinite(x).all():return None
    dx=np.diff(x)
    if np.any(dx<0):return None
    lo=int(np.searchsorted(x,xmin,'left'));hi=int(np.searchsorted(x,xmax,'right'))
    x=x[lo:hi];y=y[lo:hi];dx=dx[lo:max(lo,hi-1)]
    if len(x)<2:return None
    valid=np.isfinite(y)
    if not valid.any():return None
    columns=np.floor((x-xmin)*(width/(xmax-xmin))).astype(np.intp)
    np.clip(columns,0,width-1,out=columns)
    threshold=max(3.*dt,1500.) if time_mode and dt>0 else 2000. if time_mode else 2.
    cuts=dx>threshold if gap_cut else np.zeros(len(x)-1,dtype=bool)
    boundaries=(columns[1:]!=columns[:-1])|cuts
    starts=np.flatnonzero(valid & np.r_[True,(~valid[:-1])|boundaries])
    ends=np.flatnonzero(valid & np.r_[(~valid[1:])|boundaries,True])+1
    # Alternating start/end reductions skip invalid runs without copying Y or
    # treating NaNs as extrema. Duplicate boundaries are harmless odd entries.
    indices=np.empty(len(starts)*2,dtype=np.intp);indices[::2]=starts;indices[1::2]=ends
    if indices[-1]==len(y):indices=indices[:-1]
    low=np.minimum.reduceat(y,indices)[::2];high=np.maximum.reduceat(y,indices)[::2]
    centers=xmin+(columns[starts]+.5)*((xmax-xmin)/width)
    links=(ends[:-1]==starts[1:])
    if len(links):links &= ~cuts[starts[1:]-1]
    left=ends[:-1][links]-1;right=starts[1:][links]
    if step:
        lx=np.column_stack((x[left],x[right],x[right],x[right])).reshape(-1)
        ly=np.column_stack((y[left],y[left],y[left],y[right])).reshape(-1)
    else:
        lx=np.column_stack((x[left],x[right])).reshape(-1)
        ly=np.column_stack((y[left],y[right])).reshape(-1)
    return centers,low,high,lx,ly
