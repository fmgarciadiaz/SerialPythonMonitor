"""Process-scoped profiles already compiled in the source-bound V20 pair."""
from contextlib import contextmanager
from pathlib import Path
from monitor.v20.receiver.unoq_acquisition import Configuration
ROOT=Path(__file__).resolve().parents[1]

# These tuples already exist in the source-bound installed MCU and relay.
# They are enabled only in this diagnostic process, never in the public catalog.
PRIVATE_PROFILES=((10,116,5568),(12,144,7488),(12,142,7488),(12,140,7488))


@contextmanager
def diagnostic_profiles(bits,rates):
    import re
    from monitor.v20.receiver import unoq_native as native
    original=native.PROFILES
    try:
        additions=[]
        for rate in rates:
            if native.profile(bits,rate) is not None:
                continue
            candidate=next((p for p in PRIVATE_PROFILES if p[0]==bits and 160000000//p[1]==rate),None)
            if candidate is None:
                raise ValueError('Unsupported private candidate')
            b,ticks,node=candidate
            pattern=rf'\{{\s*{b}\s*,\s*1\s*,\s*{ticks}\s*,\s*{node}\s*\}}'
            for header in ('oscilloscope/sketch/native_profiles.h','relay/native_profiles.h'):
                if not re.search(pattern,(ROOT/'arduino/v20'/header).read_text()):
                    raise ValueError('Candidate absent from paired V20 sources')
            additions.append(dict(bits=b,channels=1,ticks=ticks,node_pairs=node,queue_slots=4,
                                  internal_only=True,headroom=False,validation='private diagnostic only'))
        native.PROFILES=original+tuple(additions)
        for rate in rates:
            Configuration(bits,rate)  # Reject invalid requests before acquiring the Q.
        yield
    finally:
        native.PROFILES=original

