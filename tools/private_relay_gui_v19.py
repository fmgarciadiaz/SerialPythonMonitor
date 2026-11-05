"""Explicit private relay binding for a diagnostic GUI receiver child only.

The normal monitor still rejects every relay outside its accepted receipt.
This module is imported only by gui_relay_candidate_v19.py.
"""
from contextlib import contextmanager,ExitStack
import json
import os
from pathlib import Path
from tools.probe_relay_transport_v19 import checked_artifact
from monitor.v19.io.live_connection import accepted_identity,installed_identity,installed_connection

ENV='ARDUSCOPIO_PRIVATE_RELAY_BINDING'
ACK_ENV='ARDUSCOPIO_PRIVATE_RELAY_ACK_REFRESH'


def binding_identity(serial):
    path=Path(os.environ[ENV]).resolve()
    report=json.loads(path.read_text())
    if (report.get('private') is not True or report.get('promoted') is not False
            or report.get('private_candidate_activated') is not True or report.get('restoring')
            or report.get('restoration')):
        raise RuntimeError('Private relay binding is not active')
    artifact=checked_artifact(Path(report['source_build_report']))
    expected=report['private_identity']
    baseline=report['baseline']['identity']
    if (expected.get('board_serial')!=serial or expected.get('app')!='scope-v19-main-1'
            or expected.get('firmware_sha256')!=accepted_identity()['firmware_sha256']
            or expected.get('firmware_sha256')!=baseline.get('firmware_sha256')
            or expected.get('relay_sha256')!=artifact['sha256']):
        raise RuntimeError('Private relay binding identity differs')
    return expected


def private_identity(serial):
    expected=binding_identity(serial)
    actual=installed_identity(serial,require_accepted=False)
    if actual!=expected:raise RuntimeError('Installed pair differs from exact private binding')
    return actual


@contextmanager
def private_connection(serial):
    # The receiver child owns this lock through its restoration and exit.
    with installed_connection(serial,identity=private_identity) as connection:
        from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV,observe_connection
        path=os.environ.get(METRICS_ENV)
        with ExitStack() as stack:
            from tools.radio_burst_inline_v19 import ENV as BURST_ENV,INTERVAL_ENV,STARTUP_ENV,inline_burst
            burst=os.environ.get(BURST_ENV)
            if burst is not None:
                if os.environ.get(ACK_ENV)=='1':raise RuntimeError('Inline cadence arm cannot use legacy ACK replay')
                interval=os.environ.get(INTERVAL_ENV)
                stack.enter_context(inline_burst(int(burst),None if interval is None else int(interval),
                                                os.environ.get(STARTUP_ENV)=='1'))
            if os.environ.get(ACK_ENV)=='1':
                from tools.radio_query_candidate_v19 import refresh_query_after_chunk_ack
                stack.enter_context(refresh_query_after_chunk_ack())
            if path:stack.enter_context(observe_connection(connection,Path(path)))
            yield connection
