"""Isolated RADIO callback coalescing with passive ACK audit and Q restore."""
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def install(stack, receiver_type, registry):
    from experimentos.radio_ipc_compact_v17.sample_coalescer import SampleCoalescer
    original_emit=receiver_type._emit
    original_events=receiver_type._process_decoder_events
    original_pump=receiver_type.pump

    def state(receiver):
        result=getattr(receiver,'_sample_coalescer',None)
        if result is None:
            result=receiver._sample_coalescer=SampleCoalescer()
            registry.append(result)
        return result

    def emit(receiver,rows,*,validated_spi=False):
        grouped=state(receiver)
        enabled=(validated_spi and getattr(receiver.wav_codes,'radio_audio',False)
            and (receiver.config.bits,receiver.config.rate)==(8,1600000)
            and not getattr(receiver,'_coalescer_boundary',False))
        if not enabled:
            grouped.flush('bypass')
            return original_emit(receiver,rows,validated_spi=validated_spi)
        callback=receiver.on_samples
        context=(receiver.config,receiver.mode,receiver.visible)
        def collect(records):grouped.push(records,callback,context)
        receiver.on_samples=collect
        try:return original_emit(receiver,rows,validated_spi=validated_spi)
        finally:receiver.on_samples=callback

    def events(receiver):
        boundary=any(kind!='samples' for kind,_ in receiver.decoder.events)
        previous=getattr(receiver,'_coalescer_boundary',False)
        if boundary:state(receiver).flush('events:'+','.join(kind for kind,_ in receiver.decoder.events if kind!='samples'))
        receiver._coalescer_boundary=previous or boundary
        try:return original_events(receiver)
        finally:receiver._coalescer_boundary=previous

    def pump(receiver):
        state(receiver).expire()
        result=original_pump(receiver)
        state(receiver).expire()
        return result

    def boundary(function):
        def call(receiver,*args,**kwargs):
            state(receiver).flush(function.__name__)
            return function(receiver,*args,**kwargs)
        return call

    stack.enter_context(patch.object(receiver_type,'_emit',emit))
    stack.enter_context(patch.object(receiver_type,'_process_decoder_events',events))
    stack.enter_context(patch.object(receiver_type,'pump',pump))
    for name in ('configure','generator','wav_request','shutdown_output','close','_switch'):
        stack.enter_context(patch.object(receiver_type,name,boundary(getattr(receiver_type,name))))


def main():
    from monitor.v17.qt_environment import prepare_platform_plugins
    prepare_platform_plugins()
    from monitor.v17.receiver.unoq_config_receiver import OutputReceiver
    from experimentos.radio_ipc_compact_v17.wire_probe import main as validate
    folder=Path(__file__).parent/'resultados'/datetime.now().strftime('coalesce_%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    enabled='--control' not in sys.argv
    registry=[];report=dict(ok=False,enabled=enabled,argv=sys.argv,source_hashes={},limitations=[
        'Experimental ADC8/1.6M RADIO only, bounded16000samples and32parts.',
        '10ms deadline checked cooperatively; blocked read/callback scheduling can exceed it.',
        'Standard receiver validates every frame; control events and shutdown flush older samples first.',
        'No codec, adaptive refresh, firmware or credit modifications. Passive observer adds overhead.'])
    for name in ('coalesce_probe.py','sample_coalescer.py','wire_probe.py','wire_ack_audit.py'):
        content=(Path(__file__).parent/name).read_bytes();(folder/name).write_bytes(content)
        report['source_hashes'][name]=hashlib.sha256(content).hexdigest()
    try:
        with ExitStack() as stack:
            if enabled:install(stack,OutputReceiver,registry)
            result=validate(report_hook=lambda wire,evidence:report.update(
                wire_report=str(evidence/'report.json'),physical_report=wire.get('physical_report')))
        report['ok']=result==0
    finally:
        report['coalescers']=[dict(**c.stats,pending_samples=c.count,pending_parts=len(c.parts),slow_top=c.slow_top) for c in registry]
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('COALESCE_REPORT',folder/'report.json',flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
