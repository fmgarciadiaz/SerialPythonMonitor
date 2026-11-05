"""Opt-in macOS thread QoS experiment for a disposable audio-owner child.

No API runs at import. QoS is a scheduling request, not a timing guarantee.
The pthread getter reports requested QoS, not scheduler overrides/effective
priority. Use on the same thread throughout, after process startup::

    with audio_qos('user_interactive') as report:
        run_experiment()

The default uses a reversible override and verifies that requested/base QoS
stays unchanged, including QOS_CLASS_UNSPECIFIED. The optional
assigned_audio_qos() setter variant rejects an unspecified initial class:
Apple's setter cannot restore it. This module is not enabled by the GUI.
"""
import ctypes
import os
import sys
from contextlib import contextmanager


QOS_CLASSES = {
    'user_interactive': 0x21,
    'user_initiated': 0x19,
    'default': 0x15,
    'utility': 0x11,
    'background': 0x09,
}
_CLASS_NAMES = {value: name for name, value in QOS_CLASSES.items()}
_CLASS_NAMES[0] = 'unspecified'


class AudioQoSError(RuntimeError):
    """A rejected/failed experiment; report never implies unverified success."""

    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def _load_library():
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    library.pthread_self.argtypes = []
    library.pthread_self.restype = ctypes.c_void_p
    library.pthread_get_qos_class_np.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_int)]
    library.pthread_get_qos_class_np.restype = ctypes.c_int
    library.pthread_set_qos_class_self_np.argtypes = [ctypes.c_uint, ctypes.c_int]
    library.pthread_set_qos_class_self_np.restype = ctypes.c_int
    library.pthread_override_qos_class_start_np.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.c_int]
    library.pthread_override_qos_class_start_np.restype = ctypes.c_void_p
    library.pthread_override_qos_class_end_np.argtypes = [ctypes.c_void_p]
    library.pthread_override_qos_class_end_np.restype = ctypes.c_int
    return library


def _state(qos_class, relative_priority):
    return dict(qos_class=qos_class, name=_CLASS_NAMES.get(qos_class, 'unknown'),
                relative_priority=relative_priority)


def _fail(report, message):
    report['errors'].append(message)
    raise AudioQoSError(message, report)


def _check(report, operation, result):
    if result:
        _fail(report, f'{operation} failed ({result}): {os.strerror(result)}')


def _read(library, thread, report):
    qos_class = ctypes.c_uint()
    relative = ctypes.c_int()
    result = library.pthread_get_qos_class_np(
        thread, ctypes.byref(qos_class), ctypes.byref(relative))
    _check(report, 'pthread_get_qos_class_np', result)
    return _state(qos_class.value, relative.value)


def _restore(library, thread, before, report):
    if library.pthread_self() != thread:
        _fail(report, 'QoS restoration must run on the original thread')
    result = library.pthread_set_qos_class_self_np(
        before['qos_class'], before['relative_priority'])
    _check(report, 'pthread_set_qos_class_self_np (restore)', result)
    report['after'] = _read(library, thread, report)
    if report['after'] != before:
        _fail(report, 'QoS restoration verification did not match the initial state')
    report['restored'] = True


@contextmanager
def assigned_audio_qos(name, relative_priority=0):
    """Set/verify current-thread QoS, yield report, then restore/verify exactly.

    Unsupported platforms, API failures, unknown/unrestorable initial states,
    and verification failures raise AudioQoSError carrying the partial report.
    If experiment code raises, restoration is still attempted; a restoration
    failure raises explicitly with the experiment exception chained by Python.
    """
    report = dict(mode='assigned', platform=sys.platform, requested=None, before=None,
                  applied=None, after=None, restored=False, errors=[])
    if name not in QOS_CLASSES:
        _fail(report, f'Unsupported QoS class: {name!r}')
    if type(relative_priority) is not int or not -15 <= relative_priority <= 0:
        _fail(report, 'Relative QoS priority must be an integer between -15 and 0')
    requested = _state(QOS_CLASSES[name], relative_priority)
    report['requested'] = requested
    if sys.platform != 'darwin':
        _fail(report, 'Audio QoS experiment requires macOS')
    try:
        library = _load_library()
    except (OSError, AttributeError) as exc:
        _fail(report, f'macOS pthread QoS API unavailable: {exc}')
    thread = library.pthread_self()
    before = _read(library, thread, report)
    report['before'] = before
    if (before['qos_class'] not in _CLASS_NAMES or before['qos_class'] == 0
            or not -15 <= before['relative_priority'] <= 0):
        _fail(report, 'Initial QoS cannot be restored exactly; no change applied')
    result = library.pthread_set_qos_class_self_np(
        requested['qos_class'], requested['relative_priority'])
    _check(report, 'pthread_set_qos_class_self_np (apply)', result)
    try:
        report['applied'] = _read(library, thread, report)
        if report['applied'] != requested:
            _fail(report, 'Applied QoS verification did not match the request')
        yield report
    finally:
        _restore(library, thread, before, report)


@contextmanager
def audio_qos(name, relative_priority=0):
    """Temporarily override current-thread QoS without changing its base class.

    A non-null override handle and successful end are the API confirmations;
    pthread_get_qos_class_np cannot verify effective override priority. The
    report therefore labels its readings as base QoS and never claims a
    scheduler deadline. Any failed start/end/read or changed base is explicit.
    """
    report = dict(mode='override', platform=sys.platform, requested=None,
                  before=None, during=None, after=None, override_started=False,
                  override_ended=False, base_unchanged=False, restored=False,
                  errors=[])
    if name not in QOS_CLASSES:
        _fail(report, f'Unsupported QoS class: {name!r}')
    if type(relative_priority) is not int or not -15 <= relative_priority <= 0:
        _fail(report, 'Relative QoS priority must be an integer between -15 and 0')
    requested = _state(QOS_CLASSES[name], relative_priority)
    report['requested'] = requested
    if sys.platform != 'darwin':
        _fail(report, 'Audio QoS experiment requires macOS')
    try:
        library = _load_library()
    except (OSError, AttributeError) as exc:
        _fail(report, f'macOS pthread QoS API unavailable: {exc}')
    thread = library.pthread_self()
    report['before'] = _read(library, thread, report)
    handle = library.pthread_override_qos_class_start_np(
        thread, requested['qos_class'], requested['relative_priority'])
    if not handle:
        _fail(report, 'pthread_override_qos_class_start_np returned NULL')
    report['override_started'] = True
    try:
        report['during'] = _read(library, thread, report)
        if report['during'] != report['before']:
            _fail(report, 'Base QoS changed while starting the override')
        yield report
    finally:
        result = library.pthread_override_qos_class_end_np(handle)
        _check(report, 'pthread_override_qos_class_end_np', result)
        report['override_ended'] = True
        report['after'] = _read(library, thread, report)
        report['base_unchanged'] = report['after'] == report['before']
        if not report['base_unchanged']:
            _fail(report, 'Base QoS changed during the override experiment')
        report['restored'] = True
