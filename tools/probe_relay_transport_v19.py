#!/usr/bin/env python3
"""Private relay transport screen; same accepted firmware, exact final rollback."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shlex
import signal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_relay_candidate_v19 import CANDIDATE,execute_build
from monitor.v19.q_support.prepare import Journal,_require,atomic_report,load_acceptance
from monitor.v19.q_support.backend import ProductionBackend
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.relay_identity import relay_sources
from monitor.v19.receiver.unoq_acquisition import Configuration
from monitor.v19.io.receiver_lifecycle import ReceiverLifecycle


def checked_artifact(path):
    report=json.loads(path.read_text());artifact=report.get('artifact',{})
    if (report.get('ok') is not True or report.get('restoration',{}).get('ok') is not True
            or artifact.get('compiled_with_pair_stopped') is not True):
        raise ValueError('Verified stopped-pair build and restoration required')
    binary=Path(artifact['path']).resolve()
    if not binary.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        raise ValueError('Private diagnostic artifact required')
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=artifact['sha256']:
        raise ValueError('Candidate binary changed since build')
    sources=Path(artifact.get('source_directory',CANDIDATE)).resolve()
    if not sources.is_relative_to(ROOT/'diagnosticos/resultados_v19') or not sources.is_dir():
        raise ValueError('Private diagnostic sources required')
    paths=relay_sources(sources)
    if any(p.is_symlink() or not p.is_file() for p in paths):raise ValueError('Regular candidate sources required')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if hashes!=artifact['sources']:raise ValueError('Candidate sources changed since build')
    return artifact


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--build-report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=60)
    parser.add_argument('--bits',type=int,default=8);parser.add_argument('--rate',type=int,default=1860465)
    args=parser.parse_args();output=args.output.resolve()
    if not 0<args.seconds<=120:parser.error('seconds must be in (0,120]')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v19'):
        parser.error('Use a new directory under diagnosticos/resultados_v19')
    artifact=checked_artifact(args.build_report)
    config=Configuration(args.bits,args.rate)
    if (config._native or {}).get('internal_only') or (config._native or {}).get('integration_pending'):
        parser.error('Only a public ADC profile may be screened')
    output.mkdir(parents=True)
    report=dict(schema=1,version=19,private=True,promoted=False,gui_audio_tested=False,
                profile=dict(bits=config.bits,rate=config.rate,channels=config.channels),
                source_build_report=str(args.build_report.resolve()))
    save=lambda:atomic_report(output/'report.json',report)
    save();acceptance=load_acceptance(RECEIPT);backend=ProductionBackend(acceptance)
    backend._board().serial=args.serial
    journal=Journal(report,save)
    def probe_body(backend,_sources,_output):
        backend._require_stopped_original()
        b=backend._board();b.shell('mkdir','-p',backend.new_relay)
        b.run('push',artifact['path'],backend.new_relay+'/unoq_stream')
        b.shell('chmod','0755',backend.new_relay+'/unoq_stream')
        if backend._hash(backend.new_relay+'/unoq_stream')!=artifact['sha256']:
            raise RuntimeError('Remote candidate hash differs')
        expected=dict(acceptance['candidate_identity'],relay_sha256=artifact['sha256'])
        prepared=dict(candidate_identity=expected)
        journal.step('start_accepted_firmware',lambda:backend.start_new_app(prepared))
        journal.step('start_private_relay',lambda:backend.start_new_relay({},prepared))
        report['private_candidate_activated']=True;save()
        verification=journal.step('verify_private_pair',lambda:backend.verify_new(
            report['baseline'],dict(acceptance,candidate_identity=expected),prepared,10))
        _require(verification,('accepted_identity_equal','sources_exact','snapshot_equal','continuous',
                               'integrity_ok','cpu_equal','relay_configuration_verified'),'Private pair')
        report['private_verification']=verification;save()
        identity=backend._identity()
        with backend._receiver() as receiver:
            lifecycle=ReceiverLifecycle(receiver,identity,output/'private_sessions')
            snapshot=lifecycle.capture()
            lifecycle.snapshot=replace(snapshot,adc_bits=config.bits,adc_period=config.request_period)
            report['transport']=journal.step('transport_screen',lambda:lifecycle.restore(args.seconds))
            save()
            if not report['transport']['hardware_restored']:
                raise RuntimeError('Private transport screen failed')
        return dict(artifact,transport_screen_passed=True)
    def probe(backend,sources,destination):
        try:return probe_body(backend,sources,destination)
        finally:
            if backend.new_relay_id is not None:
                try:
                    logs=backend._output('sh','-c','docker logs '+shlex.quote(backend.new_relay_id)+' 2>&1')
                    (output/'candidate_relay.log').write_text(logs+'\n')
                    report['candidate_relay_log']='candidate_relay.log'
                    save()
                except Exception as exc:
                    # Diagnostics must never prevent exact restoration.
                    report['candidate_log_error']=repr(exc)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    def interrupted(*_):
        if report.get('restoring'):return
        raise KeyboardInterrupt('Private screen cancelled; restoring accepted pair')
    for sig in previous:signal.signal(sig,interrupted)
    try:
        ok=execute_build(backend,acceptance,CANDIDATE,output,report,save,probe,'private_transport_probe')
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,output=str(output),error=report.get('error'),
                         restored=report.get('restoration',{}).get('ok')),indent=2))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
