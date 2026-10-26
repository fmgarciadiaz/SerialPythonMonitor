"""Compile private relay with installed ADC at low load; restore exact state."""
import json,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from experimentos.relay_telemetry_v18.prepare import ROOT,HERE,manifest
from monitor.v18.q_support.board import Board,CONFIG
from monitor.v18.io.live_connection import installed_connection
from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
from monitor.v18.receiver.unoq_acquisition import Configuration
BUILD_IMAGE='debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a'

def main():
    source=HERE/'candidate_v4';receipt=json.loads((HERE/'candidate_v4.manifest.json').read_text())
    assert manifest(source)==receipt['candidate'] and manifest(ROOT/'arduino/v18/relay')==receipt['baseline']
    key=hashlib.sha256(json.dumps(receipt['candidate'],sort_keys=True).encode()).hexdigest()[:20]
    remote='/home/arduino/.cache/serialmonitor/v18-telemetry-'+key
    folder=HERE/('build_'+time.strftime('%Y%m%d_%H%M%S'));folder.mkdir()
    report=dict(ok=False,remote=remote,source=receipt,candidate_installed=False)
    def save():(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();print(folder,flush=True)
    b=Board(json.loads(CONFIG.read_text()))
    with installed_connection(b.serial) as connection:
        receiver=OutputReceiver(connection,lambda records:None);receiver.decoder.numeric=True
        life=ReceiverLifecycle(receiver,connection.identity,folder);snapshot=life.capture();report['identity']=connection.identity
        try:
            receiver.configure(Configuration(14,40000))
            def build():
                b.shell('mkdir','-p',remote)
                for p in source.iterdir():
                    if p.is_file():b.run('push',str(p),remote+'/'+p.name)
                b.shell('docker','run','--rm','--user','0:0','--security-opt','no-new-privileges',
                    '--mount',f'type=bind,src={remote},dst=/build','--entrypoint','sh',BUILD_IMAGE,'-c',
                    'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && cc -O2 -std=c11 -Wall -Wextra -Werror /build/unoq_config_stream.c -lm -o /build/unoq_stream')
                return b.shell('sha256sum',remote+'/unoq_stream',capture=True).stdout.split()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(build)
                while not future.done():receiver.pump()
                report['relay_sha256']=future.result();report['compiled']=True
        except BaseException as exc:report['error']=repr(exc)
        finally:
            report['restoration']=life.restore(10);receiver.close()
            report['ok']=bool(report.get('compiled') and report['restoration']['hardware_restored']);save()
    print('FINAL',report['ok'],folder,flush=True)
    return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
