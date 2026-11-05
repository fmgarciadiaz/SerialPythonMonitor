#!/usr/bin/env python3
"""Activate the proven private V20 base; keep it running, rollback V19 on failure."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_v20_pair import checked_proof,APP_CONTAINER
from tools.probe_v20_gui import TrialBackend,activate
from monitor.v19.q_support.prepare import Journal,_require,atomic_report,load_acceptance,rollback_once,source_changes
from monitor.v19.q_support.service import RECEIPT as ACCEPTANCE
from monitor.v20.q_support.working_pair import CHECKS,PROOF,RECEIPT,receipt_from_report


def execute_working(backend,acceptance,candidate,report,save,publish,activate_pair=activate):
    journal=Journal(report,save);baseline=backup=changes=None;dirty=committed=False
    report.update(ok=False,private=True,promoted=False,state_uncertain=False)
    backend.selected=candidate;backend._candidate_compile_cleared=True
    with backend.owner():
        try:
            qualified=journal.step('preflight',lambda:backend.preflight(acceptance))
            _require(qualified,('production_backend_qualified','rollback_rehearsal_verified','cached_launcher_verified'),'Qualified backend')
            baseline=journal.step('capture',backend.capture);report['baseline']=baseline
            _require(baseline,('generator_off','wav_idle','receiver_closed','identity_verified','source_manifest_verified'),'Accepted baseline')
            if any(baseline['identity'].get(k)!=v for k,v in acceptance['candidate_identity'].items()):
                raise RuntimeError('Accepted V19 baseline required')
            backup=journal.step('backup',lambda:backend.backup(baseline));report['backup']=backup
            _require(backup,('export_verified','source_archive_verified','full_cache_verified',
                            'firmware_elf_bin_verified','relay_verified','paired_manifest_persisted'),'Paired backup')
            changes=source_changes(baseline['app_sources'],baseline['app_sources']);report['source_changes']=changes
            dirty=True;report['state_uncertain']=True;save()
            for name,args in (('quiesce',(baseline,)),('stop_old_relay',(baseline,)),
                              ('rename_old_relay',(baseline,)),('stop_app',())):
                journal.step(name,lambda name=name,args=args:getattr(backend,name)(*args))
            result=journal.step('activate_working_v20',lambda:activate_pair(backend,acceptance,candidate,baseline,journal))
            _require(result,CHECKS,'Private V20 working pair')
            identity=backend._identity()
            expected=dict(board_serial=backend._board().serial,app=APP_CONTAINER,
                          firmware_sha256=candidate['firmware_sha256'],relay_sha256=candidate['relay_sha256'])
            if identity!=expected:raise RuntimeError('Working V20 exact identity differs')
            report.update(private_verification=result,private_identity=identity,private_firmware_activated=True,
                          state_uncertain=False,ok=True)
            save();publish();committed=True
        except BaseException as exc:
            report.update(error=repr(exc),ok=False)
        finally:
            if dirty and not committed:
                report.update(restoring=True,state_uncertain=True);save()
                try:
                    backend._no_reader()
                    report['restoration']=rollback_once(backend,baseline,backup,None,changes,journal)
                except BaseException as exc:
                    report['restoration']=dict(ok=False,errors=[repr(exc)],blocked=True)
                report.update(restoring=False,private_firmware_activated=False,
                              state_uncertain=not report['restoration']['ok'])
            if not committed:save()
    return committed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True);parser.add_argument('--proof',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if args.proof.resolve()!=(ROOT/PROOF).resolve():parser.error('Original storage_lifetime_cycle proof required')
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('New output under diagnosticos/resultados_v20 required')
    if RECEIPT.exists():parser.error('Working V20 receipt already exists; review it before another activation')
    candidate=checked_proof(args.proof);acceptance=load_acceptance(ACCEPTANCE)
    if json.loads(args.proof.read_text()).get('tcp_queue_recovery',False) is not False:
        parser.error('Original relay only; TCP candidate cannot be activated here')
    output.mkdir(parents=True);binding=output/'report.json'
    receipt_copy=output/'accepted_v19_receipt.json';receipt_copy.write_bytes(Path(acceptance['receipt_path']).read_bytes())
    if hashlib.sha256(receipt_copy.read_bytes()).hexdigest()!=acceptance['receipt_sha256']:
        raise RuntimeError('Backup acceptance receipt changed')
    report=dict(schema=1,version=20,private=True,promoted=False,public_rates_changed=False,
                purpose='Keep private V20 active; V19 retained only for recovery',
                accepted_v19_receipt=dict(path=str(receipt_copy),sha256=acceptance['receipt_sha256']),
                working_receipt=str(RECEIPT),**candidate)
    from monitor.v20.q_support.board import source_files
    report['tool_sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           (Path(__file__).resolve(),ROOT/'tools/probe_v20_gui.py',ROOT/'tools/private_v20_pair.py',
                            ROOT/'monitor/v20/q_support/working_pair.py',ROOT/'monitor/v20/io/live_connection.py')}
    monitor=ROOT/'monitor/v20'
    report['monitor_sources']={p.relative_to(monitor).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in source_files(monitor) if p!=RECEIPT}
    save=lambda:atomic_report(binding,report);save()
    backend=TrialBackend(acceptance,output=output);backend._board().serial=args.serial
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def cancelled(*_):
        if not report.get('restoring') and not report.get('ok'):raise KeyboardInterrupt('V20 activation cancelled; rollback V19')
    for sig in previous:signal.signal(sig,cancelled)
    try:
        ok=execute_working(backend,acceptance,candidate,report,save,
                           lambda:atomic_report(RECEIPT,receipt_from_report(binding,args.serial)))
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,v20_left_running=ok,error=report.get('error'),report=str(binding))))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
