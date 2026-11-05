"""Explicit restart of the receipt-verified private V20 pair, never an update.

The app launcher compiles/uploads existing sources. Its durable remote job must
finish before releasing the board lock; an interrupted host reconciles the same
job on retry. An uncertain launch blocks connection and another upload.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile
import time
import uuid

from monitor.v20.board_owner import board_owner
from monitor.v20.q_support.prepare import atomic_report
from monitor.v20.q_support.working_pair import ROOT, RECEIPT, working_identity
from monitor.v20.receiver.unoq_usb import adb

RELAY = 'serialmonitor-usb-stream-v20'


class RemoteJobFailed(RuntimeError):
    pass


def pending_path(serial):
    key = hashlib.sha256(str(serial).encode()).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / f'serialmonitor-v20-recovery-{os.getuid()}-{key}.json'


def assert_no_pending(serial):
    if pending_path(serial).exists():
        raise RuntimeError('Restablecimiento Q pendiente; usar Restablecer Q para reconciliarlo antes de Conectar.')


# Runs entirely on Q. Persist terminal status even when upload fails. No shell
# command is reconstructed from untrusted output; paths/IDs passed as arguments.
JOB = '''import fcntl,json,os,pathlib,subprocess,sys
folder=pathlib.Path(sys.argv[1]); app=sys.argv[2]; relay=sys.argv[3]; boot=json.loads(sys.argv[4])
def state(**values):
 p=folder/'status.tmp'; p.write_text(json.dumps(dict(pid=os.getpid(),**values))); p.replace(folder/'status.json')
def run(*args): subprocess.run(args,check=True)
lock=open('/tmp/serialmonitor-v20-recovery.lock','a+')
try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
 state(state='done',exit_status=75,error='Another remote recovery owns Q')
 sys.exit(75)
state(state='running')
try:
 run('docker','stop','--time','3',relay)
 run('arduino-app-cli','app','stop',app)
 run('gpioset','-c',boot['chip'],'-t0',str(boot['reset_line'])+'=0')
 try: run('gpioset','-c',boot['chip'],'-t0',str(boot['ready_line'])+'=1')
 finally: run('gpioset','-c',boot['chip'],'-t0',str(boot['reset_line'])+'=1')
 run('arduino-app-cli','app','start',app,'--no-prepare')
 state(state='done',exit_status=0)
except BaseException as exc:
 state(state='done',exit_status=1,error=repr(exc))
 raise
'''


class RecoveryBackend:
    def __init__(self, serial, *, runner=adb, verifier=working_identity, progress=print,
                 sleep=time.sleep):
        self.serial, self.runner, self.verifier = serial, runner, verifier
        self.progress, self.sleep = progress, sleep

    def remote(self, *args):
        return self.runner('-s', self.serial, 'shell', shlex.join(map(str, args)))

    def inspect(self, name):
        values = json.loads(self.remote('docker', 'inspect', name))
        if len(values) != 1 or values[0].get('Name', '').lstrip('/') != name:
            raise RuntimeError('Contenedor ambiguo: ' + name)
        return values[0]

    def sha(self, path):
        return self.remote('sha256sum', path).split()[0]

    def preflight(self):
        expected = self.verifier(self.serial, self.runner)
        receipt = json.loads(RECEIPT.read_text())
        app = self.inspect(expected['app'])
        relay = self.inspect(RELAY)
        running = self.remote('docker', 'ps', '--format', '{{.Names}}').splitlines()
        if any(n.startswith('scope-') and n.endswith('-main-1') and n != expected['app'] for n in running):
            raise RuntimeError('Otra Scope activa; no se restablecerá el Q')
        apps = json.loads(self.remote('arduino-app-cli', 'app', 'list', '--format', 'json')).get('apps', [])
        if any(a.get('status') == 'running' and a.get('name') != 'Scope V20' for a in apps):
            raise RuntimeError('Otra app activa; no se restablecerá el Q')
        if 'ESTAB' in self.remote('ss', '-tn', 'sport', '=', ':8766'):
            raise RuntimeError('Otro lector TCP activo; cerrar adquisición antes de Restablecer Q')
        root = '/home/arduino/ArduinoApps/' + expected['app'].removesuffix('-main-1')
        labels = app.get('Config', {}).get('Labels') or {}
        if labels.get('com.docker.compose.project.working_dir') != root + '/.cache':
            raise RuntimeError('Ruta de app distinta del recibo')
        mounts = [m['Source'] for m in relay.get('Mounts', []) if m.get('Destination') == '/work/unoq_stream']
        if len(mounts) != 1 or not mounts[0].startswith('/home/arduino/.cache/serialmonitor/'):
            raise RuntimeError('Ruta del relay inválida')
        # Read-only source manifest; no helper is uploaded and no source touched.
        script = '''import hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]); excluded={'.git','.cache','__pycache__','data','.venv'}
paths=[p for p in r.rglob('*') if not any(x in excluded for x in p.relative_to(r).parts) and p.name!='.DS_Store' and p.suffix!='.pyc']
if any(p.is_symlink() for p in paths): raise RuntimeError('Source symlink')
print(json.dumps({p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}))'''
        sources = json.loads(self.remote('python3', '-c', script, root))
        if sources != receipt['v20_sources']:
            raise RuntimeError('Fuentes remotas distintas del recibo V20')
        firmware = root + '/.cache/sketch/sketch.ino.bin'
        if self.sha(firmware) != expected['firmware_sha256'] or self.sha(mounts[0]) != expected['relay_sha256']:
            raise RuntimeError('Binarios instalados distintos del recibo V20')
        return dict(identity=expected, app_root=root, firmware=firmware,
                    relay_binary=mounts[0], app=app, relay=relay)

    def evidence(self, baseline):
        logs = {}
        for name, info in (('app', baseline['app']), ('relay', baseline['relay'])):
            logs[name] = self.remote('sh', '-c', 'docker logs --tail 200 ' + shlex.quote(info['Id']) + ' 2>&1')
        return logs

    def launch(self, baseline, folder):
        cfg = json.loads((ROOT / 'arduino/v20/unoq.json').read_text())
        args = ['python3', '-u', '-c', JOB, folder, baseline['app_root'], baseline['relay']['Id'], json.dumps(cfg['ready_boot'])]
        # Launch uncertainty is retained locally; never assume ADB timeout means
        # the remote uploader stopped. The unique folder is never reused.
        command = 'mkdir ' + shlex.quote(folder) + ' && nohup ' + shlex.join(args)
        command += ' >' + shlex.quote(folder + '/job.log') + ' 2>&1 </dev/null &'
        self.remote('sh', '-c', command)

    def wait(self, folder):
        last = 0
        missing_since = None
        while True:
            try:
                status = json.loads(self.remote('cat', folder + '/status.json'))
            except Exception as exc:
                # A lost status cannot prove the uploader is gone. Preserve the
                # pending marker; retry reconciles instead of starting a job.
                if missing_since is None:
                    missing_since = time.monotonic()
                if time.monotonic() - missing_since >= 15:
                    raise RuntimeError('Estado remoto incierto durante 15 s; recuperación pendiente, reintentar Restablecer Q') from exc
                if time.monotonic() - last > 30:
                    self.progress('Estado remoto pendiente; esperando sin iniciar otra carga…', flush=True)
                    last = time.monotonic()
                self.sleep(1)
                continue
            missing_since = None
            if status.get('state') == 'done':
                if status.get('exit_status') == 75:
                    raise RuntimeError('Otra recuperación remota activa; conservar pendiente')
                if status.get('exit_status') != 0:
                    raise RemoteJobFailed('Carga remota falló: ' + status.get('error', 'ver job.log'))
                return status
            if status.get('state') != 'running':
                raise RuntimeError('Estado remoto inválido; recuperación pendiente')
            pid = status.get('pid')
            if type(pid) is not int or pid <= 1:
                raise RuntimeError('PID remoto inválido; recuperación pendiente')
            # A stale running receipt is not proof of a live uploader.
            probe = 'import os,sys; os.kill(int(sys.argv[1]),0); print("alive")'
            try:
                self.remote('python3', '-c', probe, pid)
            except Exception as exc:
                raise RuntimeError('Proceso remoto no confirmado; conservar pendiente y reconciliar') from exc
            if time.monotonic() - last > 30:
                self.progress('Recargando misma pareja; esperando compilación/carga remota…', flush=True)
                last = time.monotonic()
            self.sleep(1)

    def finish(self, baseline):
        if self.sha(baseline['firmware']) != baseline['identity']['firmware_sha256']:
            raise RuntimeError('El launcher cambió el BIN; relay permanece detenido')
        if self.sha(baseline['relay_binary']) != baseline['identity']['relay_sha256']:
            raise RuntimeError('El binario relay cambió; no se inicia')
        if self.inspect(RELAY)['Id'] != baseline['relay']['Id']:
            raise RuntimeError('Identidad de contenedor relay cambió')
        self.remote('docker', 'start', baseline['relay']['Id'])
        from monitor.v20.io.live_connection import installed_identity
        # Only this internal verification bypasses the pending guard.
        identity = installed_identity(self.serial, self.runner, recovery_internal=True)
        if identity != baseline['identity']:
            raise RuntimeError('Identidad final diferente')
        result = self.safe_profile(identity)
        if installed_identity(self.serial, self.runner, recovery_internal=True) != identity:
            raise RuntimeError('Identidad cambió durante los 10 segundos de verificación')
        return result

    def safe_profile(self, identity):
        from monitor.v20.q_support.backend import ProductionBackend
        from monitor.v20.q_support.board import Board
        from monitor.v20.io.receiver_lifecycle import ReceiverLifecycle
        from monitor.v20.io.device_snapshot import DeviceIdentity, DeviceSnapshot
        from monitor.v20.receiver.unoq_acquisition import Configuration
        from monitor.v20.receiver.unoq_generator import GeneratorConfig
        from monitor.v20.receiver.unoq_wav import State
        cfg = json.loads((ROOT / 'arduino/v20/unoq.json').read_text())
        class QueryBoard(Board):
            def run(self, *args, capture=False):
                import subprocess
                return subprocess.run([self.adb, '-s', self.serial, *args], check=True,
                                      text=True, stdout=subprocess.PIPE if capture else None,
                                      timeout=10)
        board = QueryBoard(cfg)
        board.serial = self.serial
        backend = ProductionBackend({}, board=board)
        with backend._receiver() as receiver:
            lifecycle = ReceiverLifecycle(receiver, identity)
            safe = Configuration(14, 40000)
            lifecycle.snapshot = DeviceSnapshot(DeviceIdentity(**identity), safe.bits,
                                                safe.request_period, GeneratorConfig(enabled=0))
            result = lifecycle.restore(10)
            if not result['hardware_restored'] or receiver.wav_status.state != State.IDLE:
                raise RuntimeError('Perfil seguro/continuidad no confirmado: ' + repr(result))
            # Decoder raises ProtocolError on every CRC failure; restore cannot
            # succeed after a CRC error. The profile is deliberately new.
            return dict(profile=lifecycle.snapshot.to_dict(), wav='IDLE', crc_errors=0,
                        **result)


def recover(serial, report_path, *, backend=None):
    backend = backend or RecoveryBackend(serial)
    report = dict(version=20, action='restart_same_working_pair', ok=False,
                  recompiles_uploads_existing_sources=True, restores_failed_profile=False)
    marker = pending_path(serial)
    try:
        with board_owner(serial, 'Arduscopio Q: Restablecer Q'):
            if marker.exists():
                pending = json.loads(marker.read_text())
                token = pending.get('token', '')
                if (len(token) != 32 or any(c not in '0123456789abcdef' for c in token)
                        or pending.get('serial') != serial):
                    raise RuntimeError('Marcador de recuperación inválido; no se iniciará otra carga')
                folder = '/tmp/serialmonitor-v20-recovery-' + token
                report['reconciled'] = True
                report['job'] = folder
                backend.wait(folder)
                baseline = backend.preflight()
                if baseline['identity'] != pending['identity'] or baseline['relay']['Id'] != pending['relay_id']:
                    raise RuntimeError('Pareja cambió durante recuperación pendiente')
            else:
                baseline = backend.preflight()
                report.update(baseline=baseline, before_logs=backend.evidence(baseline))
                atomic_report(report_path, report)  # Evidence precedes reset.
                token = uuid.uuid4().hex
                folder = '/tmp/serialmonitor-v20-recovery-' + token
                pending = dict(token=token, serial=serial, identity=baseline['identity'], relay_id=baseline['relay']['Id'])
                atomic_report(marker, pending)  # Persist BEFORE remote launch.
                report['job'] = folder
                backend.launch(baseline, folder)
                backend.sleep(.3)
                backend.wait(folder)
            report['verification'] = backend.finish(baseline)
            report['ok'] = True
            marker.unlink()
    except RemoteJobFailed as exc:
        marker.unlink(missing_ok=True)
        report.update(error=str(exc), pending=False, remote_job_finished=True)
    except Exception as exc:
        report.update(error=str(exc), pending=marker.exists())
    atomic_report(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = recover(args.serial, args.report)
    print('Q restablecido en perfil seguro; pulsar Conectar' if result['ok'] else 'Error: ' + result['error'], flush=True)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
