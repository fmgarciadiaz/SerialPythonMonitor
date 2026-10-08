"""Start an installed scope app/relay without deploying repository sources."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
from monitor.v13.receiver.unoq_usb import adb_path

ROOT = Path(__file__).resolve().parents[3]
APPS = {'Scope Pulse US V13 Experimental': 'v13_pulse', 'Scope WAV V12 Audio': 'v12_audio', 'Scope Acquisition P992 V11': 'v11_p992'}


def run_command(args, running=lambda: True, timeout=180):
    if not running(): raise InterruptedError('Inicio del Q cancelado')
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.monotonic() + timeout
    try:
        while running() and time.monotonic() < deadline:
            try:
                output, _ = process.communicate(timeout=.2)
            except subprocess.TimeoutExpired:
                continue
            if process.returncode:
                lines = [line.strip() for line in output.splitlines() if line.strip()]
                summary = lines[-1].removeprefix('RuntimeError: ') if lines else 'No se pudo iniciar el Q'
                if any('READY wait: Connection timed out' in line for line in lines):
                    summary = 'App iniciada, pero el MCU no entrega READY al relay. Revisar el arranque del Q.'
                from datetime import datetime
                folder = ROOT / 'diagnosticos' / 'resultados_autoload'
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    log = folder / ('autoinicio_error_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
                    log.write_text(output)
                except OSError:
                    pass
                raise RuntimeError(summary[:400])
            return output
        if not running(): raise InterruptedError('Inicio del Q cancelado')
        raise TimeoutError('El Q no terminó de iniciar en el tiempo previsto')
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)


def ensure_scope(serial, progress=lambda text: None, running=lambda: True, runner=run_command):
    def remote(*args):
        return runner([adb_path(), '-s', serial, 'shell', shlex.join(args)], running, 10)
    progress('Comprobando aplicación y relay del Q…')
    listing=json.loads(remote('arduino-app-cli','app','list','--format','json'))
    apps=listing.get('apps', [])
    active=[app for app in apps if app.get('status')=='running']
    if len(active)>1 or any(app.get('name') not in APPS for app in active):
        raise RuntimeError('Hay otra aplicación activa en el Q; detenerla antes de usar Autoiniciar Q.')
    available=[app for app in apps if app.get('name') in APPS and app.get('status') in ('running','stopped')]
    if active:
        version=APPS[active[0]['name']]
        if os.environ.get('MONITOR_V13_WAV_FIRMWARE')=='v12_audio' and version not in ('v12_audio','v13_pulse'):
            raise RuntimeError('Se seleccionó V12 Audio, pero está activo V11 P992; cambiar la aplicación del Q antes de conectar.')
    else:
        version=next((v for v in ('v12_audio','v11_p992') if any(APPS[a['name']]==v for a in available)),None)
    if version is None:
        raise RuntimeError('Instalar primero V12 Audio o V11 P992 en el Q; el inicio automático no carga fuentes.')
    sources=[ROOT/f'arduino/{version}/relay/{name}' for name in ('unoq_config_stream.c','base_verifier.c','config_relay_protocol.h')]
    digest=hashlib.sha256(b''.join(path.read_bytes() for path in sources)).hexdigest()[:20]
    binary=f'/home/arduino/.cache/serialmonitor/usb-stream-{digest}/unoq_stream'
    names=remote('docker','ps','-a','--format','{{.Names}}').splitlines()
    if 'serialmonitor-usb-stream' in names:
        info=json.loads(remote('docker','inspect','serialmonitor-usb-stream'))[0]
        if active and info['State'].get('Running') and any(m.get('Source')==binary for m in info.get('Mounts',[])):
            progress('Aplicación y relay del Q ya activos')
            return version
    # Require a previously built native relay; never install/build implicitly.
    try:
        remote('test','-x',binary)
    except RuntimeError as exc:
        raise RuntimeError(f'Relay no preparado: ejecutar python tools/usb_stream.py build --firmware {version}') from exc
    progress(f'Iniciando Q y relay ({version}); esperar confirmación…')
    # The selected USB device must win over any global UNOQ_SERIAL override.
    # Pass it through a small child launcher rather than mutating process env.
    launcher='import os,runpy,sys; os.environ["UNOQ_SERIAL"]=sys.argv.pop(1); sys.argv.pop(0); sys.path.insert(0,os.path.dirname(sys.argv[0])); runpy.run_path(sys.argv[0],run_name="__main__")'
    runner([sys.executable,'-c',launcher,serial,str(ROOT/'tools/usb_stream.py'),'start','--firmware',version],running,180)
    progress('Q y relay iniciados; conectando lector…')
    return version


from contextlib import contextmanager
from monitor.v13.receiver.unoq_usb import Connection


@contextmanager
def connect_scope(serial, progress=lambda text: None, running=lambda: True):
    """Use the live transport first; start the installed stack only if absent."""
    connection = Connection(serial)

    def open_live():
        connection.open()
        # ADB can accept the local tunnel even when the remote port is closed.
        # Peek without consuming protocol bytes before declaring it connected.
        connection.socket.settimeout(.2)
        deadline = time.monotonic() + 2
        while running():
            try:
                if not connection.socket.recv(1, socket.MSG_PEEK):
                    raise RuntimeError('El túnel USB no tiene un relay activo')
                connection.socket.settimeout(1)
                return
            except socket.timeout:
                if time.monotonic() >= deadline:
                    raise TimeoutError('El relay no entrega datos')
        raise InterruptedError('Conexión cancelada')

    try:
        progress('Conectando Q…')
        try:
            open_live()
        except InterruptedError:
            raise
        except (OSError, RuntimeError):
            connection.close()
            progress('Sin datos del Q; comprobando app y relay…')
            ensure_scope(serial, progress, running)
            if not running():
                raise InterruptedError('Conexión cancelada')
            open_live()
        yield connection
    finally:
        connection.close()
