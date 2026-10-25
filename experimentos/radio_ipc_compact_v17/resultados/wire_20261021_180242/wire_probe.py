"""Passive physical ACK byte-completion audit with standard Q restoration."""
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    from monitor.v17.qt_environment import prepare_platform_plugins
    prepare_platform_plugins()
    from monitor.v17.receiver.unoq_usb import Connection
    from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
    from experimentos.radio_ipc_compact_v17.wire_ack_audit import WireAckAudit
    from diagnosticos.validar_generador_radio_v17 import main as validate
    folder=Path(__file__).parent/'resultados'/datetime.now().strftime('wire_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    audits=[];observer_cpu=0.;original_read=Connection.read;original_trace=OutputReceiver._trace_transport

    def read(connection):
        nonlocal observer_cpu
        data=original_read(connection)
        completed=time.monotonic()
        audit=getattr(connection,'_passive_wire_ack',None)
        if audit is None:
            audit=connection._passive_wire_ack=WireAckAudit()
            # The helper has a fixed small number of sequential connections.
            if len(audits)<8:audits.append(audit)
        started=time.thread_time()
        audit.feed(data,completed)
        observer_cpu+=time.thread_time()-started
        return data

    def trace(receiver,stage,start,end,rid=None,cpu_seconds=None,process_cpu_seconds=None):
        result=original_trace(receiver,stage,start,end,rid,cpu_seconds,process_cpu_seconds)
        if stage=='ack' and getattr(receiver.wav_codes,'radio_audio',False):
            audit=getattr(receiver.connection,'_passive_wire_ack',None)
            pending=receiver.wav_inflight.get(rid)
            if audit is not None:audit.acknowledge(rid,receiver.wav_session,end,pending[0] if pending else None)
        return result

    report=dict(ok=False,argv=sys.argv,source_hashes={},limitations=[
        'Measures host recv completion to callback, not time of arrival at kernel or physical Q ACK generation.',
        'Passive observer adds overhead; CPU is reported. No wire reordering or command generation.',
        'Only RADIO ACK callbacks are matched; parser observes all fixed992byte frames on each connection.',
        'Does not attribute waiting to GIL uniquely; includes intervening decoding, callbacks and scheduling.'])
    for name in ('wire_probe.py','wire_ack_audit.py'):
        content=(Path(__file__).parent/name).read_bytes();(folder/name).write_bytes(content)
        report['source_hashes'][name]=hashlib.sha256(content).hexdigest()
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(Connection,'read',read))
            stack.enter_context(patch.object(OutputReceiver,'_trace_transport',trace))
            physical,evidence=validate()
        report.update(ok=physical['ok'] and physical['restored'],physical_report=str(evidence/'report.json'))
    finally:
        report.update(observer_cpu_seconds=observer_cpu,connections=[a.snapshot() for a in audits])
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('WIRE_REPORT',folder/'report.json',flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
