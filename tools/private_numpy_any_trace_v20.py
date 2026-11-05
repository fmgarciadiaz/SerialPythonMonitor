"""Opt-in callsite journal for a native GUI crash inside NumPy logical_or.reduce."""

from contextlib import contextmanager
from functools import wraps
import itertools
import json
import os
from pathlib import Path
import sys
import threading


@contextmanager
def trace_numpy_any(path):
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    original = np.any
    sequence = itertools.count(1)
    main_thread = threading.main_thread()

    def write(stage, call_id, caller, value):
        item = dict(stage=stage, id=call_id, file=caller.f_code.co_filename,
                    line=caller.f_lineno, function=caller.f_code.co_name)
        if stage == 'enter':
            item['shape'] = getattr(value, 'shape', None)
            item['dtype'] = str(getattr(value, 'dtype', ''))
            item['strides'] = getattr(value, 'strides', None)
        os.write(fd, (json.dumps(item, separators=(',', ':')) + '\n').encode())

    @wraps(original)
    def observed(*args, **kwargs):
        if threading.current_thread() is not main_thread:
            return original(*args, **kwargs)
        caller = sys._getframe(1)
        call_id = next(sequence)
        write('enter', call_id, caller, args[0] if args else None)
        try:
            result = original(*args, **kwargs)
        except BaseException:
            write('error', call_id, caller, None)
            raise
        write('exit', call_id, caller, None)
        return result

    np.any = observed
    try:
        yield
    finally:
        np.any = original
        os.close(fd)
