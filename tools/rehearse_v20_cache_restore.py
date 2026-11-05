#!/usr/bin/env python3
"""Rehearse exact V20 source/cache self-restore while V19 is safely stopped."""
import argparse,hashlib,json,signal,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_v20_pair import checked_proof,APP,APP_CONTAINER
from tools.probe_v20_sram3 import MANIFEST,CONTAINER
from tools.build_relay_candidate_v19 import execute_build
from tools.v20_memory_fix import cache_inventory,undo
from tools.v20_trial_cleanup import app_is_stopped
from monitor.v20.memory_contract import verify_board
from monitor.v19.q_support.prepare import atomic_report,load_acceptance
from monitor.v19.q_support.service import RECEIPT
from monitor.v19.q_support.backend import ProductionBackend


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serial',required=True)
    p.add_argument('--proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'diagnosticos/resultados_v20'):p.error('New V20 evidence directory required')
    candidate=checked_proof(args.proof);output.mkdir(parents=True);report=dict(private=True,promoted=False,version=20,kind='cache_self_restore',**candidate)
    save=lambda:atomic_report(output/'report.json',report);save();acceptance=load_acceptance(RECEIPT)
    backend=ProductionBackend(acceptance);backend._board().serial=args.serial
    def trial(b,*_):
        board=b._board();verify_board(board)
        if not app_is_stopped(b,APP_CONTAINER) or CONTAINER in b._output('docker','ps','-a','--format','{{.Names}}').splitlines():
            raise RuntimeError('V20 private app/relay must be stopped for cache rehearsal')
        b._candidate_compile_cleared=True
        actual=json.loads(board.shell('python3','-c',MANIFEST,APP,json.dumps(list(candidate['v20_sources'])),capture=True).stdout)
        if actual!=candidate['v20_sources'] or b._hash(APP+'/.cache/sketch/sketch.ino.bin')!=candidate['firmware_sha256']:
            raise RuntimeError('Exact V20 candidate required')
        stage='/tmp/v20-cache-rehearsal-'+b.token;board.shell('mkdir','-p',stage);archive=stage+'/v20_current.tar'
        board.shell('tar','-C',APP,'-cf',archive,'app.yaml','python','sketch','.cache/sketch')
        board.run('pull',archive,str(output/'v20_current.tar'))
        saved=dict(remote_archive=archive,sha256=hashlib.sha256((output/'v20_current.tar').read_bytes()).hexdigest(),
                   previous_firmware=candidate['firmware_sha256'],old_sources=actual,old_cache_manifest=cache_inventory(board,'archive',archive))
        if b._hash(archive)!=saved['sha256'] or cache_inventory(board,'directory',APP)!=saved['old_cache_manifest']:
            raise RuntimeError('V20 paired cache backup not verified')
        atomic_report(output/'v20_backup.json',saved)
        report['v20_state_uncertain']=True;save()
        try:verification=undo(b,APP,saved)
        except BaseException:
            # One bounded retry from the already verified archive. Always report
            # the original failure; do not turn recovery into a passing rehearsal.
            try:report['v20_retry_verification']=undo(b,APP,saved);report['v20_state_uncertain']=False
            finally:save()
            raise
        report['v20_state_uncertain']=False;report['v20_verification']=verification;save()
        return dict(operation='same-version source/cache self-restore',verification=verification,firmware_changed=False)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def cancel(*_):
        if not report.get('restoring') and not report.get('v20_state_uncertain'):raise KeyboardInterrupt('Rehearsal cancelled; restoring V19')
    for sig in previous:signal.signal(sig,cancel)
    try:ok=execute_build(backend,acceptance,ROOT/'arduino/v20/oscilloscope/sketch',output,report,save,builder=trial,operation_name='v20_cache_self_restore')
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)
    print(json.dumps(dict(ok=ok,v20=report.get('v20_verification'),v19_restored=report.get('restoration',{}).get('ok'))))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
