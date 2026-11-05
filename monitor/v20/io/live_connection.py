"""Installed-only Q connection. Never deploys, starts, resets or builds Q apps.

Enter in the receiver child; its advisory lock spans all I/O and cleanup.
The caller must restore acquisition/output before leaving this context.
"""
from contextlib import contextmanager
import json
import re
import shlex
import socket
import time
from pathlib import Path

from monitor.v20.board_owner import board_owner
from monitor.v20.io.adb_tunnel import AdbTunnel
from monitor.v20.receiver.unoq_usb import adb


def accepted_identity():
    path=Path(__file__).resolve().parents[1]/'q_support/accepted/acceptance.json'
    receipt=json.loads(path.read_text())
    expected=receipt.get('candidate_identity',{})
    if (receipt.get('version')!=20 or receipt.get('accepted') is not True or
            any(not re.fullmatch('[0-9a-f]{64}',expected.get(name,''))
                for name in ('firmware_sha256','relay_sha256'))):
        raise RuntimeError('Recibo aceptado V20 inválido')
    return {name:expected[name] for name in ('firmware_sha256','relay_sha256')}


def installed_identity(serial, runner=adb, *, expected_app='scope-v20-main-1', require_accepted=True, recovery_internal=False):
    if not recovery_internal:
        from monitor.v20.q_support.recovery import assert_no_pending
        assert_no_pending(serial)
    working=None
    check_default=require_accepted and expected_app=='scope-v20-main-1'
    if check_default:
        from monitor.v20.q_support.working_pair import RECEIPT,working_identity
        if RECEIPT.exists():
            working=working_identity(serial,runner)
            expected_app=working['app']
    def remote(*args):
        return runner('-s', serial, 'shell', shlex.join(args))
    names = remote('docker', 'ps', '--format', '{{.Names}}').splitlines()
    apps = [name for name in names if name.startswith('scope-') and name.endswith('-main-1')]
    if apps != [expected_app] or 'serialmonitor-usb-stream-v20' not in names:
        raise RuntimeError('V20 requiere Scope V20 y su relay ya activos; usar Restablecer Q con la adquisición desconectada.')
    app = apps[0]
    info = json.loads(remote('docker', 'inspect', app))[0]
    root = info['Config']['Labels']['com.docker.compose.project.working_dir']
    if (not root.startswith('/home/arduino/ArduinoApps/') or not root.endswith('/.cache')
            or working is not None and root!='/home/arduino/ArduinoApps/'+expected_app.removesuffix('-main-1')+'/.cache'):
        raise RuntimeError('No se pudo identificar el firmware instalado.')
    firmware = remote('sha256sum', root + '/sketch/sketch.ino.bin').split()[0]
    relay_info = json.loads(remote('docker', 'inspect', 'serialmonitor-usb-stream-v20'))[0]
    mounts = [m['Source'] for m in relay_info.get('Mounts', []) if m.get('Destination') == '/work/unoq_stream']
    if len(mounts) != 1 or not mounts[0].startswith('/home/arduino/.cache/serialmonitor/'):
        raise RuntimeError('No se pudo identificar el relay instalado.')
    relay = remote('sha256sum', mounts[0]).split()[0]
    if any(not re.fullmatch('[0-9a-f]{64}', value) for value in (firmware, relay)):
        raise RuntimeError('Identidad SHA256 inválida.')
    if check_default:
        expected=working if working is not None else accepted_identity()
        if firmware!=expected['firmware_sha256'] or relay!=expected['relay_sha256']:
            raise RuntimeError('La pareja V20 instalada difiere del recibo local; comprobar la identidad antes de conectar.')
    return dict(board_serial=serial, app=app, firmware_sha256=firmware, relay_sha256=relay)


class LiveConnection:
    """Receiver-compatible socket view; the lease alone owns forward cleanup."""
    wav_firmware = True
    scope_restarted = False

    def __init__(self, connected, serial):
        self.socket = connected
        self.serial = serial
        self.last_data = time.monotonic()
        connected.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        connected.settimeout(.1)

    def read(self):
        try:
            data = self.socket.recv(65536)
        except socket.timeout:
            if time.monotonic() - self.last_data > 2:
                raise RuntimeError('El Q dejó de entregar muestras durante más de 2 segundos.')
            return b''
        if not data:
            raise RuntimeError('El Q cerró el flujo.')
        self.last_data = time.monotonic()
        return data

    def close(self):
        if self.socket is not None:
            connected, self.socket = self.socket, None
            connected.close()


@contextmanager
def installed_connection(serial, progress=lambda text: None, running=lambda: True,
                         *, runner=adb, identity=None, connect=socket.create_connection):
    identity = identity or (lambda device: installed_identity(device, runner))
    with board_owner(serial, 'monitor V20 receiver child'):
        if not running():
            raise InterruptedError('Conexión cancelada')
        progress('Comprobando Q instalado; sin reiniciar ni programar…')
        expected = identity(serial)
        lease = AdbTunnel(serial, expected, adb=runner, identity=identity,
                          exclusive=lambda: True, connect=connect)
        connection = None
        owned_socket = None
        try:
            lease.open()
            owned_socket = lease.take_socket()
            connection = LiveConnection(owned_socket, serial)
            connection.identity = expected
            yield connection
        finally:
            cleanup_errors = []
            if owned_socket is not None:
                try:
                    if connection is not None:
                        connection.close()
                    else:
                        owned_socket.close()
                except Exception as exc:
                    cleanup_errors.append(repr(exc))
                finally:
                    # This context is the socket owner, including setup failure.
                    lease.confirm_owner_exit(True)
            result = lease.close()
            if result['errors'] or not result['forward_released']:
                cleanup_errors.append(repr(result))
            if lease.identity_before is not None and result['forward_released']:
                try:
                    lease.verify_identity_after()
                except Exception as exc:
                    cleanup_errors.append(repr(exc))
            if cleanup_errors:
                raise RuntimeError('Cierre de conexión sin confirmar: ' + '; '.join(cleanup_errors))
