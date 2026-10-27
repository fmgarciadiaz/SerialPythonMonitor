"""Verify the accepted V18 pair, or update an existing pair transactionally."""
import argparse
import json
import os
import signal
from pathlib import Path

from monitor.v18.q_support.prepare import load_acceptance, execute, atomic_report
from monitor.v18.q_support.backend import ProductionBackend, APP, APP_CONTAINER, CONTAINER, HELPER
from monitor.v18.io.live_connection import installed_identity

RECEIPT = Path(__file__).with_name('accepted') / 'acceptance.json'


class MissingScopePair(RuntimeError):
    """Missing containers are not proof that the target is safe to overwrite."""


def wake_accepted_pair(backend, acceptance):
    """Recover a stopped accepted installation; never select another app."""
    backend._no_reader()
    running=backend._output('docker','ps','--format','{{.Names}}').splitlines()
    apps=[name for name in running if name.startswith('scope-') and name.endswith('-main-1')]
    if apps not in ([],[APP_CONTAINER]):
        raise RuntimeError('Hay otra app activa; no se reiniciará ni modificará')
    listing=backend._json('arduino-app-cli','app','list','--format','json').get('apps',[])
    if any(app.get('status')=='running' and app.get('name')!='Scope V18' for app in listing):
        raise RuntimeError('Hay otra app activa; no se reiniciará ni modificará')
    try:
        app=backend._inspect(APP_CONTAINER)
        relay=backend._inspect(CONTAINER)
    except Exception as exc:
        raise MissingScopePair('Falta la pareja Scope V18; comprobar instalación inicial') from exc
    expected=acceptance['candidate_identity']
    if (backend._hash(APP+'/.cache/sketch/sketch.ino.bin') != expected['firmware_sha256'] or
            backend._hash(backend._relay_bin(relay)) != expected['relay_sha256']):
        raise RuntimeError('La pareja detenida no coincide con la aceptada; no se inicia automáticamente')
    board=backend._board()
    board.run('push',str(HELPER),backend.helper)
    if backend._sources()!=acceptance['sources']['app']:
        raise RuntimeError('Fuentes de la app detenida distintas de la pareja aceptada')
    print('Recuperando la pareja Scope V18 aceptada…',flush=True)
    if relay['State']['Running']:
        board.shell('docker','stop','--time','3',relay['Id'])
    board.start()
    if backend._hash(APP+'/.cache/sketch/sketch.ino.bin')!=expected['firmware_sha256']:
        raise RuntimeError('El arranque produjo un firmware distinto; relay permanece detenido')
    board.shell('docker','start',relay['Id'])


def prepare(serial, report_path):
    acceptance = load_acceptance(RECEIPT)
    backend = ProductionBackend(acceptance)
    backend._board().serial = serial
    report = dict(version=18, action='verify_or_update', ok=False)
    try:
        with backend.owner():
            try:
                identity = installed_identity(serial)
            except RuntimeError:
                try:
                    wake_accepted_pair(backend,acceptance)
                except MissingScopePair:
                    from monitor.v18.q_support.bootstrap import install_empty
                    install_empty(backend,acceptance,report,
                                  lambda:atomic_report(report_path,report))
                    atomic_report(report_path,report)
                    return report
                identity=installed_identity(serial)
            backend.preflight(acceptance)
            expected = acceptance['candidate_identity']
            exact = all(identity[name] == value for name, value in expected.items())
            if exact:
                print('Verificando pareja V18 y adquisición…', flush=True)
                baseline = backend.capture()
                if baseline['app_sources'] != acceptance['sources']['app']:
                    raise RuntimeError('Las fuentes del Q no coinciden con la pareja aceptada')
                recovery = backend._recover(identity, 10)
                if not all(recovery[key] for key in ('snapshot_equal','continuous','integrity_ok')):
                    raise RuntimeError('La recuperación de adquisición no pasó')
                report.update(ok=True, action='verified', identity=identity, recovery=recovery)
        if not exact:
            print('Actualizando pareja V18 con respaldo y rollback…', flush=True)
            execute(backend, acceptance, report,
                    lambda: atomic_report(report_path, report))
    except Exception as exc:
        report.update(ok=False, error=str(exc))
    atomic_report(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    # Explicit selected USB device takes precedence over a shell override.
    os.environ['UNOQ_SERIAL'] = args.serial
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Preparación interrumpida; restaurando Q')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        result = prepare(args.serial, args.report)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print('Q V18 preparado; pulsar Conectar' if result['ok'] else
          'Error: ' + result.get('error','No se pudo verificar Scope V18'), flush=True)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
