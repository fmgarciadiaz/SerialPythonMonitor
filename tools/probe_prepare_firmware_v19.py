#!/usr/bin/env python3
"""Private O2 load/integrity screen; accepted relay and exact paired rollback."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import shlex
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_relay_candidate_v19 import execute_build
from tools.private_firmware_v19 import ENV,checked_firmware,private_identity
from tools.relay_wire_metrics_v19 import observe_connection
from monitor.v19.q_support.backend import ProductionBackend,APP
from monitor.v19.q_support.prepare import Journal,_require,atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v19.receiver.unoq_acquisition import Configuration


def activate(backend,acceptance,candidate,baseline,journal):
    """Normal launcher rebuild; never inject an unverified temporary cache."""
    backend._require_stopped_original();board=backend._board()
    expected_sources=dict(acceptance['sources']['app'])
    if candidate.get('diagnostic_schema'):
        from tools.wav_timing_candidate_v19 import SCHEMA
        if candidate['diagnostic_schema']!=SCHEMA or set(candidate['source_files'])!={'sketch.ino','wav.h','wav_dma.h'}:
            raise ValueError('Exact private WAV timing source set required')
        for relative,item in candidate['source_files'].items():
            board.run('push',item['path'],APP+'/sketch/'+relative)
            expected_sources['sketch/'+relative]=item['sha256']
    else:
        relative=candidate.get('source_relative','sketch.ino')
        if relative not in ('sketch.ino','wav.h','wav_dma.h'):raise ValueError('Unknown reviewed firmware source')
        board.run('push',candidate['source'],APP+'/sketch/'+relative)
        expected_sources['sketch/'+relative]=candidate['source_sha256']
    if backend._sources()!=expected_sources:raise RuntimeError('Private source replacement differs')
    board.shell('mkdir','-p',backend.new_relay)
    board.run('push',candidate.get('relay_path',acceptance['artifacts']['relay']['path']),backend.new_relay+'/unoq_stream')
    board.shell('chmod','0755',backend.new_relay+'/unoq_stream')
    if backend._hash(backend.new_relay+'/unoq_stream')!=candidate['relay_sha256']:
        raise RuntimeError('Exact private/accepted relay staging hash differs')
    identity=dict(acceptance['candidate_identity'],firmware_sha256=candidate['firmware_sha256'],
                  relay_sha256=candidate['relay_sha256'])
    prepared=dict(candidate_identity=identity)
    journal.step('normal_launcher_rebuild_private_firmware',lambda:backend.start_new_app(prepared))
    if backend._hash(APP+'/.cache/sketch/sketch.ino.elf')!=candidate['elf_sha256']:
        raise RuntimeError('Launcher ELF differs from compared candidate')
    journal.step('start_private_relay' if candidate.get('relay_path') else 'start_accepted_relay',
                 lambda:backend.start_new_relay(baseline,prepared))
    private_acceptance=dict(acceptance,candidate_identity=identity,
                            sources=dict(acceptance['sources'],app=expected_sources))
    verification=journal.step('verify_private_load',lambda:backend.verify_new(baseline,private_acceptance,prepared,10))
    _require(verification,('accepted_identity_equal','sources_exact','snapshot_equal','continuous','integrity_ok',
                          'cpu_equal','relay_configuration_verified'),'Private firmware load')
    return verification


def main():
    import os
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--build-report',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--seconds',type=float,default=10)
    args=parser.parse_args();output=args.output.resolve()
    if not 0<args.seconds<=60:parser.error('seconds must be in (0,60]')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('New private diagnostic directory required')
    candidate=checked_firmware(args.build_report);acceptance=load_acceptance(RECEIPT)
    output.mkdir(parents=True);report=dict(private=True,promoted=False,private_firmware_activated=False,
        source_build_report=candidate['build_report'],candidate=candidate,scope='load and RF integrity; no GUI/audio/stack acceptance')
    save=lambda:atomic_report(output/'report.json',report);save()
    backend=ProductionBackend(acceptance);backend._board().serial=args.serial;journal=Journal(report,save)
    def probe(backend,_sources,_output):
        try:
            report['private_load']=activate(backend,acceptance,candidate,report['baseline'],journal)
            report['private_firmware_activated']=True;report['private_identity']=backend._identity();save()
            os.environ[ENV]=str(output/'report.json')
            private_identity(args.serial) # Explicit exact binding, never production receipt relaxation.
            config=Configuration(8,1860465)
            with backend._receiver() as receiver:
                with observe_connection(receiver.connection,output/'wire_metrics.json',wav_timing=bool(candidate.get('diagnostic_schema'))):
                    life=ReceiverLifecycle(receiver,report['private_identity'],output/'private_sessions')
                    snapshot=life.capture()
                    life.snapshot=replace(snapshot,adc_bits=config.bits,adc_period=config.request_period)
                    report['transport']=journal.step('target_RF_integrity',lambda:life.restore(args.seconds))
                    if not report['transport'].get('hardware_restored'):raise RuntimeError('Private RF integrity failed')
            return dict(candidate,load_pass=True,transport_pass=True,production_installed=False)
        finally:
            if backend.new_relay_id is not None:
                try:
                    text=backend._output('sh','-c','docker logs '+shlex.quote(backend.new_relay_id)+' 2>&1')
                    (output/'private_relay.log').write_text(text)
                except Exception as exc:report['log_error']=repr(exc)
    previous={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def interrupted(*_):
        if report.get('restoring'):return
        raise KeyboardInterrupt('Private firmware cancelled; restoring accepted pair')
    for sig in previous:signal.signal(sig,interrupted)
    try:
        ok=execute_build(backend,acceptance,ROOT/'arduino/v19/oscilloscope/sketch',output,report,save,
                         builder=probe,operation_name='private_firmware_load_and_RF')
    finally:
        os.environ.pop(ENV,None)
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,error=report.get('error'),restored=report.get('restoration',{}).get('ok'))))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
