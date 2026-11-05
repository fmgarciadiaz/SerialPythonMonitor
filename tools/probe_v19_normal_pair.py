#!/usr/bin/env python3
"""Private V19 normal-firmware rate probe; restore and verify the Q afterward."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monitor.v19.board_owner import board_owner
from monitor.v19.receiver.unoq_acquisition import (Configuration, acquisition_reply,
                                                  acquisition_request)
from monitor.v19.receiver.unoq_control import status_request
from monitor.v19.receiver.unoq_usb import Connection
from tools.read_stack_diag_v19 import FrameReader, active_config
from tools.run_stack_diag_v19 import (Q, V17_APP, V17_BACKUP_BIN,
                                      V17_BACKUP_RELAY, V18_APP, V18_RECEIPT,
                                      RELAY_IMAGE, GOVERNOR, ROOT as PROJECT_ROOT,
                                      atomic_json, cleanup_relay, digest,
                                      import_app, load_v18_restore_reference,
                                      open_connection_when_ready, restore_v17_original_pair,
                                      source_manifest, stop_destroy_app, write_app_yaml)

PAIR_DIR = ROOT / 'diagnosticos/resultados_v19/build_pair_20261027'
PAIR_MANIFEST = PAIR_DIR / 'build-v19-pair.json'
V19_APP_SOURCE = ROOT / 'arduino/v19/oscilloscope'
V19_PRODUCTION_NAME = 'Scope V19'
V19_TEST_RATE = 1860465
V19_TEST_BITS = 8
NORMAL_BUILD_SOURCE_DRIFT = {
    'sketch/acquisition.h', 'sketch/scope_config.h',
    'sketch/sketch.ino', 'sketch/sketch.yaml',
}


def start_relay(q, name, local_bin, remote_bin, expected_hash):
    q.shell('mkdir', '-p', remote_bin.rsplit('/', 1)[0])
    q.run('push', str(local_bin), remote_bin)
    q.shell('chmod', '0755', remote_bin)
    if q.sha(remote_bin) != expected_hash:
        raise RuntimeError('El relay temporal V19 difiere del artefacto normal')
    q.shell('docker', 'run', '-d', '--name', name,
            '--label', 'arduscopio.scope.stack-diagnostic=true',
            '--network', 'host', '--read-only', '--cap-drop', 'ALL', '--cap-add', 'SYS_NICE',
            '--security-opt', 'no-new-privileges', '--user', '0:0',
            '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
            '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
            '--mount', 'type=bind,src=' + remote_bin + ',dst=/work/unoq_stream,readonly',
            '--mount', 'type=bind,src=' + GOVERNOR + ',dst=/scope_cpu_governor',
            '--entrypoint', '/work/unoq_stream', RELAY_IMAGE, timeout=60)
    info = q.inspect(name)
    mounts = [item['Source'] for item in info.get('Mounts', [])
              if item.get('Destination') == '/work/unoq_stream']
    if not info.get('State', {}).get('Running') or len(mounts) != 1 or q.sha(mounts[0]) != expected_hash:
        raise RuntimeError('Identidad o estado del relay temporal incorrectos')
    return info['Id']


def validate_inputs(q, manifest, receipt):
    if manifest.get('installed') is not False or manifest.get('candidate_only') is not True:
        raise RuntimeError('El manifiesto V19 no está marcado como candidato privado')
    for kind, file_name in (('firmware', 'firmware-v19.bin'), ('relay', 'relay-v19-unoq_stream')):
        expected = manifest['artifacts'][kind]['sha256']
        if digest(PAIR_DIR / file_name) != expected:
            raise RuntimeError('Cambió el artefacto normal V19: ' + kind)
        if expected != receipt['candidate_identity'][kind + '_sha256']:
            raise RuntimeError('La pareja normal V19 ya no coincide con la referencia V18 aceptada')
    changed_sources = [rel for rel, expected in manifest['sources']['firmware'].items()
                       if digest(V19_APP_SOURCE / rel) != expected]
    unexpected = set(changed_sources) - NORMAL_BUILD_SOURCE_DRIFT
    if unexpected:
        raise RuntimeError('Cambió una fuente V19 fuera de los cuatro archivos con instrumentación/documentación: '
                           + ', '.join(sorted(unexpected)))
    relay_sources = ROOT / 'arduino/v19/relay'
    for rel, expected in manifest['sources']['relay'].items():
        if digest(relay_sources / rel) != expected:
            raise RuntimeError('Cambió una fuente del relay V19 desde la compilación: ' + rel)

    apps = q.apps()
    if any(row.get('status') == 'running' for row in apps):
        raise RuntimeError('Hay una app activa en el Q')
    if any(row.get('name') == V19_PRODUCTION_NAME for row in apps):
        raise RuntimeError('Scope V19 de producción existe; no se usa ni se sobrescribe')
    running = q.containers(all_=False)
    if running:
        raise RuntimeError('Hay contenedores activos: ' + ', '.join(running))

    v17_hash = q.sha(V17_APP + '/.cache/sketch/sketch.ino.bin')
    if v17_hash != digest(V17_BACKUP_BIN):
        raise RuntimeError('El firmware V17 actual no coincide con el respaldo pareado')
    v17_relay = q.inspect('serialmonitor-usb-stream')
    mount = [m['Source'] for m in v17_relay.get('Mounts', [])
             if m.get('Destination') == '/work/unoq_stream']
    if (v17_relay.get('State', {}).get('Running') or len(mount) != 1 or
            q.sha(mount[0]) != digest(V17_BACKUP_RELAY)):
        raise RuntimeError('Relay V17 original no coincide con su respaldo o sigue activo')
    v17_sources = q.remote_manifest(V17_APP)
    v18_sources = q.remote_manifest(V18_APP)
    if v18_sources != receipt['sources']['app']:
        raise RuntimeError('Scope V18 del Q difiere de su recibo aceptado')
    if q.exists(V18_APP + '/.cache/sketch/sketch.ino.bin'):
        raise RuntimeError('La app Scope V18 tiene un BIN cacheado inesperado')
    relay18 = q.inspect('serialmonitor-usb-stream-v18')
    mount18 = [m['Source'] for m in relay18.get('Mounts', [])
               if m.get('Destination') == '/work/unoq_stream']
    if len(mount18) != 1 or q.sha(mount18[0]) != receipt['candidate_identity']['relay_sha256']:
        raise RuntimeError('El relay V18 detenido difiere del recibo aceptado')

    containers = {name: q.inspect(name)['Id'] for name in q.containers(all_=True)}
    return dict(apps=[{k: row.get(k) for k in ('id', 'name', 'status', 'default')} for row in apps],
                containers=containers, v17_sources=v17_sources, v18_sources=v18_sources,
                v17_cached_firmware_sha256=v17_hash,
                v19_firmware_sha256=manifest['artifacts']['firmware']['sha256'],
                v19_relay_sha256=manifest['artifacts']['relay']['sha256'],
                source_drift_requiring_binary_hash_check=changed_sources,
                v19_pair_matches_accepted_v18=True)


def configure_and_measure(connection, duration, capture_path):
    reader = FrameReader(connection)
    startup_deadline = time.monotonic() + 5.0
    while len(reader.buffer) < 992 and time.monotonic() < startup_deadline:
        data = connection.read()
        if data:
            reader.buffer.extend(data)
    if len(reader.buffer) < 992:
        startup = dict(bytes_received=len(reader.buffer),
                       prefix_hex=bytes(reader.buffer[:64]).hex(),
                       timeout_seconds=5.0)
        atomic_json(capture_path, dict(schema=1, version=19,
                                       firmware_kind='normal',
                                       startup_diagnostic=startup,
                                       capture_error='No llegó un frame SCP1 completo en 5 s'))
        raise TimeoutError('No llegó un frame SCP1 completo en 5 s: ' +
                           f"{startup['bytes_received']} bytes; " +
                           startup['prefix_hex'])
    first_packet, first_kind = reader.next_packet()
    previous = active_config(first_packet, first_kind)
    for _ in range(10):
        if previous is not None:
            break
        first_packet, first_kind = reader.next_packet()
        previous = active_config(first_packet, first_kind)
    if previous is None:
        raise RuntimeError('No se pudo determinar el perfil V19 inicial para restaurarlo')

    target = Configuration(V19_TEST_BITS, V19_TEST_RATE)
    request_id = 0x80000041
    connection.socket.sendall(acquisition_request(request_id, target))
    deadline = time.monotonic() + 10
    applied = False
    replies = []
    while time.monotonic() < deadline:
        packet, kind = reader.next_packet()
        if kind != 7:
            continue
        reply = acquisition_reply(packet)
        replies.append(dict(phase=reply.phase.name, reason=reply.reason.name,
                            active_bits=reply.active.bits, active_rate=reply.active.rate))
        if reply.request_id != request_id:
            continue
        if reply.phase.name == 'REJECTED':
            raise RuntimeError(f'V19 rechazó 8 bits/1,860 MS/s: {reply.reason.name}')
        if reply.phase.name != 'APPLIED':
            continue
        if reply.active != target:
            raise RuntimeError(f'V19 confirmó APPLIED con {reply.active}, se solicitó {target}; '
                               f'reply={replies[-1]}')
        applied = True
        break
    if not applied:
        raise TimeoutError('V19 no confirmó APPLIED para 8 bits/1,860 MS/s')

    rows = []
    frames = empty_native_frames = queue_peak = dropped_max = fatal_max = spi_errors = 0
    start = time.monotonic()
    end = start + duration
    next_status = start
    ping_id = 0x80001001
    wrong_kind = {}
    capture_error = None
    try:
        while time.monotonic() < end:
            now = time.monotonic()
            if now >= next_status:
                connection.socket.sendall(status_request(ping_id))
                ping_id = ((ping_id + 1) & 0x7fffffff) | 0x80000000
                next_status = now + 1
            packet, kind = reader.next_packet()
            if kind in (5, 7, 9, 12):
                continue
            if kind != 20:
                wrong_kind[kind] = wrong_kind.get(kind, 0) + 1
                continue
            ack, spi, commands, short, result, error = struct.unpack_from('<IIIIii', packet, 16)
            rate, index, dropped, fatal, count, bits, channels, period, node, flags = struct.unpack_from('<IIIIHBBIII', packet, 48)
            node_pairs, queue, peak, copy_ticks, poll_ticks, slack_ticks = struct.unpack_from('<6I', packet, 84)
            if (rate, bits, channels, period) != (V19_TEST_RATE, V19_TEST_BITS, 1, target.period):
                raise RuntimeError(f'Frame normal V19 con perfil inesperado: {rate=}, {bits=}, {channels=}, {period=}')
            # The relay can emit a native status packet with no payload while
            # the ADC starts or between batches. It is not a lost-data frame.
            if not node_pairs:
                raise RuntimeError('V19 informó un frame sin pares de nodos')
            if not count:
                empty_native_frames += 1
                continue
            if spi or commands or short or error or result not in (0, 992):
                spi_errors += spi + commands + short + (error != 0)
            frames += 1
            dropped_max = max(dropped_max, dropped)
            fatal_max = max(fatal_max, fatal)
            queue_peak = max(queue_peak, peak, queue)
            if now - start >= len(rows):
                rows.append(dict(elapsed_seconds=now-start,
                                 sequence=struct.unpack_from('<I', packet, 8)[0],
                                 queue=queue, queue_peak=peak, copy_ticks=copy_ticks,
                                 poll_ticks=poll_ticks, slack_ticks=slack_ticks,
                                 dropped=dropped, fatal=fatal))
    except Exception as exc:
        capture_error = str(exc)
    capture_duration = time.monotonic() - start

    restored = False
    restore_error = None
    try:
        connection.socket.sendall(acquisition_request(request_id + 1, previous))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            packet, kind = reader.next_packet()
            if kind != 7:
                continue
            reply = acquisition_reply(packet)
            if reply.request_id == request_id + 1 and reply.phase.name == 'APPLIED' and reply.active == previous:
                restored = True
                break
    except Exception as exc:
        restore_error = str(exc)

    result = dict(schema=1, version=19, firmware_kind='normal',
                  tested_configuration=dict(bits=target.bits, rate_sps=target.rate,
                                            channels=target.channels, ticks=target.period,
                                            node_pairs=target.node_pairs),
                  initial_configuration=dict(bits=previous.bits, rate_sps=previous.rate,
                                             channels=previous.channels, ticks=previous.period),
                  first_frame_kind=first_kind, acquisition_applied=applied,
                  acquisition_replies=replies, duration_seconds=capture_duration,
                  native_frames=frames, empty_native_frames=empty_native_frames,
                  queue_peak=queue_peak,
                  dropped_nodes_max=dropped_max, fatal_errors_max=fatal_max,
                  spi_error_total=spi_errors, unexpected_frame_kinds=wrong_kind,
                  adc_configuration_restored=restored, capture_error=capture_error,
                  restore_error=restore_error, rows=rows, physical_acceptance='pending')
    atomic_json(capture_path, result)
    return result


def run(args):
    raise RuntimeError('Herramienta histórica retirada: restauraba V17. '
                       'Usar tools/probe_radio_rate_v19.py para la pareja V19 instalada.')


def _historical_run(args):
    token = uuid.uuid4().hex[:8]
    q = Q(args.serial)
    manifest = json.loads(PAIR_MANIFEST.read_text(encoding='utf-8'))
    receipt = load_v18_restore_reference()
    report = dict(schema=1, version=19,
                  purpose='normal V19 firmware pair private rate probe; not production acceptance',
                  started_utc=datetime.now(timezone.utc).isoformat(), serial=args.serial,
                  candidate_only=True, production_scope_v19_used=False,
                  temporary_apps=[], temporary_relay=None, restored=False, errors=[])
    atomic_json(args.output, report)
    with board_owner(args.serial, 'private normal V19 pair probe with V17 rollback'):
        baseline = validate_inputs(q, manifest, receipt)
        report['baseline'] = baseline
        atomic_json(args.output, report)
        temp_app = None
        temp_manifest = None
        temp_name = 'Scope V19 Normal Pair Probe ' + token
        relay_name = 'serialmonitor-usb-stream-v19-normal-probe-' + token
        relay_remote = '/home/arduino/.cache/serialmonitor/' + relay_name + '/unoq_stream'
        relay_remote_dir = relay_remote.rsplit('/', 1)[0]
        relay_id = None
        firmware_may_have_changed = False
        restore_verified = False
        try:
            import tempfile
            with tempfile.TemporaryDirectory(prefix='arduscopio-v19-normal-probe-') as local_tmp:
                local_app = Path(local_tmp) / 'v19-normal-probe'
                import shutil
                shutil.copytree(V19_APP_SOURCE, local_app)
                write_app_yaml(local_app / 'app.yaml', temp_name)
                temp_manifest = source_manifest(local_app)
                expected_sources = manifest['sources']['firmware']
                if (set(temp_manifest) != set(expected_sources) or
                        any(temp_manifest[name] != expected for name, expected in expected_sources.items()
                            if name != 'app.yaml' and name not in NORMAL_BUILD_SOURCE_DRIFT)):
                    raise RuntimeError('Fuentes temporales V19 cambiaron fuera de los cuatro archivos conocidos')
                slug = 'scope-v19-normal-probe-' + token
                temp_app, temp_id = import_app(q, local_app, slug, temp_name)
                if q.remote_manifest(temp_app) != temp_manifest:
                    raise RuntimeError('App temporal V19 importada no coincide con las fuentes verificadas')
                report['temporary_apps'].append(dict(role='normal_v19_probe', id=temp_id, path=temp_app))
                atomic_json(args.output, report)

                firmware_may_have_changed = True
                q.cli('app', 'stop', temp_app, timeout=120)
                q.pulse_loader()
                q.cli('app', 'start', temp_app, timeout=600)
                actual_firmware = q.sha(temp_app + '/.cache/sketch/sketch.ino.bin')
                if actual_firmware != manifest['artifacts']['firmware']['sha256']:
                    raise RuntimeError('App Lab generó BIN distinto al firmware normal V19')
                report['normal_v19_firmware_sha256'] = actual_firmware
                report['normal_v19_app_status_after_start'] = next(
                    (row.get('status') for row in q.apps() if row.get('name') == temp_name), None)
                atomic_json(args.output, report)

                relay_id = start_relay(q, relay_name, PAIR_DIR / 'relay-v19-unoq_stream',
                                       relay_remote, manifest['artifacts']['relay']['sha256'])
                report['temporary_relay'] = dict(name=relay_name, id=relay_id,
                                                 sha256=manifest['artifacts']['relay']['sha256'])
                try:
                    report['relay_logs_before_capture'] = q.output(
                        'docker', 'logs', '--tail', '30', relay_name, timeout=15)
                except Exception as exc:
                    report['relay_logs_error'] = str(exc)
                atomic_json(args.output, report)
                connection = open_connection_when_ready(args.serial)
                try:
                    capture = configure_and_measure(connection, args.duration, args.capture_output)
                    report['capture'] = {k: capture.get(k) for k in
                                         ('tested_configuration', 'initial_configuration',
                                          'first_frame_kind', 'acquisition_applied',
                                          'duration_seconds', 'native_frames', 'empty_native_frames', 'queue_peak',
                                          'dropped_nodes_max', 'fatal_errors_max', 'spi_error_total',
                                          'unexpected_frame_kinds', 'adc_configuration_restored',
                                          'capture_error', 'restore_error')}
                    atomic_json(args.output, report)
                finally:
                    connection.close()
        except Exception as exc:
            report['errors'].append(str(exc))
        finally:
            report['cleanup_relay_errors'] = cleanup_relay(q, relay_name, relay_id)
            try:
                script = r'''import pathlib,shutil,sys
p=pathlib.Path(sys.argv[1]); root=pathlib.Path('/home/arduino/.cache/serialmonitor')
if p.parent != root or not p.name.startswith('serialmonitor-usb-stream-v19-normal-probe-'):
 raise SystemExit('ruta cache relay no valida')
shutil.rmtree(p,ignore_errors=True)
if p.exists(): raise SystemExit('no se pudo retirar cache relay temporal')
'''
                q.shell('python3', '-c', script, relay_remote_dir)
                report['cleanup_relay_cache_error'] = None
            except Exception as exc:
                report['cleanup_relay_cache_error'] = str(exc)
            if temp_app:
                report['cleanup_probe_app_errors'] = stop_destroy_app(
                    q, temp_app, temp_name, temp_manifest)
            if firmware_may_have_changed:
                try:
                    restore_sha, proof = restore_v17_original_pair(q, baseline, args.serial)
                    report['restore_firmware_sha256'] = restore_sha
                    report['restore_spi_proof'] = proof
                    restore_verified = True
                except Exception as exc:
                    report['errors'].append('Restauración V17: ' + str(exc))
                    report['restore_error'] = str(exc)
            try:
                final_apps = q.apps()
                final_running = q.containers(all_=False)
                final_app_keys = {(r.get('id'), r.get('name'), r.get('status'), r.get('default')) for r in final_apps}
                original_app_keys = {(r.get('id'), r.get('name'), r.get('status'), r.get('default')) for r in baseline['apps']}
                final_containers = {name: q.inspect(name)['Id'] for name in q.containers(all_=True)}
                report['final_state'] = dict(running_apps=[r.get('name') for r in final_apps if r.get('status') == 'running'],
                    running_containers=final_running,
                    original_app_inventory_equal=final_app_keys == original_app_keys,
                    original_container_ids_equal=final_containers == baseline['containers'],
                    v17_source_manifest_equal=q.remote_manifest(V17_APP) == baseline['v17_sources'],
                    v18_source_manifest_equal=q.remote_manifest(V18_APP) == baseline['v18_sources'],
                    v17_cached_firmware_unchanged=q.sha(V17_APP + '/.cache/sketch/sketch.ino.bin') == baseline['v17_cached_firmware_sha256'],
                    v18_cached_firmware_absent=not q.exists(V18_APP + '/.cache/sketch/sketch.ino.bin'),
                    v19_production_absent=not any(r.get('name') == V19_PRODUCTION_NAME for r in final_apps),
                    v17_firmware_restored=restore_verified)
                report['restored'] = bool(restore_verified and not final_running and
                    report['final_state']['original_app_inventory_equal'] and
                    report['final_state']['original_container_ids_equal'] and
                    report['final_state']['v17_source_manifest_equal'] and
                    report['final_state']['v18_source_manifest_equal'] and
                    report['final_state']['v17_cached_firmware_unchanged'] and
                    report['final_state']['v18_cached_firmware_absent'] and
                    report['final_state']['v19_production_absent'] and
                    report.get('restore_spi_proof', {}).get('first_verified_frame') is True and
                    not report.get('cleanup_relay_errors') and
                    report.get('cleanup_relay_cache_error') is None and
                    not report.get('cleanup_probe_app_errors'))
            except Exception as exc:
                report['errors'].append('Verificación final: ' + str(exc))
                report['final_state_error'] = str(exc)
            report['finished_utc'] = datetime.now(timezone.utc).isoformat()
            atomic_json(args.output, report)

    print(json.dumps({k: report.get(k) for k in ('restored', 'capture', 'errors', 'report')},
                     ensure_ascii=False, indent=2))
    return 0 if (report.get('restored') and report.get('capture', {}).get('acquisition_applied') and
                 report.get('capture', {}).get('native_frames', 0) and
                 report.get('capture', {}).get('dropped_nodes_max') == 0 and
                 report.get('capture', {}).get('fatal_errors_max') == 0 and
                 report.get('capture', {}).get('spi_error_total') == 0 and
                 report.get('capture', {}).get('adc_configuration_restored')) else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='1060031107')
    parser.add_argument('--duration', type=float, default=120)
    parser.add_argument('--output', type=Path, default=ROOT / 'diagnosticos/resultados_v19/normal_pair_probe_20261027/report.json')
    parser.add_argument('--capture-output', type=Path, default=ROOT / 'diagnosticos/resultados_v19/normal_pair_probe_20261027/capture.json')
    args = parser.parse_args()
    if not 5 <= args.duration <= 3600:
        parser.error('--duration debe estar entre 5 and 3600 s')
    try:
        return run(args)
    except Exception as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
