#!/usr/bin/env python3
"""Ensayo controlado de alta frecuencia para Scope V20 (v20Gemini) con restauracion estricta de V19."""
import argparse
import base64
import json
import os
from pathlib import Path
import select
import socket
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monitor.v20.receiver.unoq_acquisition import Configuration, acquisition_request

ADB_DEFAULT = '/Users/fmgarciadiaz/Library/Arduino15/packages/arduino/tools/adb/32.0.0/adb'
ADB = os.environ.get('UNOQ_ADB', ADB_DEFAULT)
SERIAL = '1060031107'


def adb_cmd(*args, capture=True):
    cmd = [ADB, '-s', SERIAL] + list(args)
    res = subprocess.run(cmd, capture_output=capture, text=True)
    if res.returncode != 0 and capture:
        raise RuntimeError(f"Error en ADB {' '.join(args)}: {res.stderr}")
    return res


def adb_shell(*cmd, capture=True):
    return adb_cmd('shell', *cmd, capture=capture)


def normalize_app_id(app_id):
    if not app_id:
        return app_id
    if app_id.startswith('user:'):
        return app_id
    try:
        padded = app_id + '=' * ((4 - len(app_id) % 4) % 4)
        decoded = base64.b64decode(padded).decode('utf-8')
        if decoded.startswith('user:'):
            return decoded
    except Exception:
        pass
    return app_id


def get_inventory():
    out = adb_shell('arduino-app-cli', 'app', 'list', '--format', 'json').stdout
    listing = json.loads(out)
    containers = adb_shell('docker', 'ps', '--format', '{{.Names}}').stdout.splitlines()
    apps = listing.get('apps', [])
    for a in apps:
        a['id'] = normalize_app_id(a.get('id', ''))
    return apps, set(containers)


def do_ready_boot():
    adb_shell('gpioset', '-c', 'gpiochip1', '-t0', '38=0')
    try:
        adb_shell('gpioset', '-c', 'gpiochip1', '-t0', '70=1')
    finally:
        adb_shell('gpioset', '-c', 'gpiochip1', '-t0', '38=1')


def compile_v20_relay():
    print("-> Compilando relay ARM64 para V20 en la placa...")
    stage = '/tmp/v20_relay_src'
    adb_shell('mkdir', '-p', stage)
    relay_dir = ROOT / 'arduino/v20/relay'
    for f in relay_dir.glob('*'):
        if f.is_file():
            adb_cmd('push', str(f), f"{stage}/{f.name}", capture=False)

    build_cmd = (
        'docker run --rm --user 0:0 --security-opt no-new-privileges '
        f'-v {stage}:/build q-gcc '
        'cc -O2 -std=c11 -Wall -Wextra /build/unoq_config_stream.c -lm -o /build/unoq_stream_v20'
    )
    adb_shell(build_cmd, capture=False)
    # Copiar binario resultante a /tmp/unoq_stream_v20
    adb_shell('cp', f"{stage}/unoq_stream_v20", '/tmp/unoq_stream_v20')
    adb_shell('chmod', '+x', '/tmp/unoq_stream_v20')
    print("-> Relay V20 compilado con éxito.")


def parse_scp1_frame(data):
    if len(data) < 992 or data[:4] != b'SCP1':
        return None
    ver, kind = struct.unpack('<HH', data[4:8])
    seq = struct.unpack('<I', data[8:12])[0]
    # Header de métricas nativas V4
    # offset 48: rate, 52: sample_idx, 56: dropped, 60: fatal
    rate, sample_idx, dropped, fatal = struct.unpack('<IIII', data[48:64])
    count, bits, channels = struct.unpack('<HBB', data[64:68])
    period, node_idx, epoch = struct.unpack('<III', data[68:80])
    timestamp = struct.unpack('<I', data[80:84])[0]
    node_pairs, queue_slots_used, queue_peak, copy_max, poll_max, slack_min = struct.unpack('<IIIIII', data[84:108])
    send_previous, produced = struct.unpack('<II', data[108:116])
    return {
        'seq': seq,
        'rate': rate,
        'bits': bits,
        'channels': channels,
        'period': period,
        'dropped': dropped,
        'fatal': fatal,
        'queue_peak': queue_peak,
        'queue_slots_used': queue_slots_used,
        'slack_min': slack_min,
        'copy_max': copy_max,
        'poll_max': poll_max,
        'produced': produced,
        'timestamp': timestamp,
    }


def run_benchmark_rate(s, config, duration=5.0):
    print(f"\n--- Probando {config.bits} bits @ {config.rate} Hz (periodo {config.request_period & 0xffff} ticks) durante {duration}s ---")
    req = acquisition_request(0x80000001, config)
    s.sendall(req)

    start_time = time.time()
    frames_received = 0
    metrics = []
    buf = bytearray()

    while time.time() - start_time < duration:
        r, _, _ = select.select([s], [], [], 0.5)
        if not r:
            continue
        chunk = s.recv(4096)
        if not chunk:
            raise RuntimeError("Conexión cerrada por el relay")
        buf.extend(chunk)

        while len(buf) >= 992:
            frame_data = buf[:992]
            del buf[:992]
            m = parse_scp1_frame(frame_data)
            if m and m['bits'] == config.bits and m['period'] == (config.request_period & 0xffff):
                metrics.append(m)
                frames_received += 1

    if not metrics:
        print("  [FALLO] No se recibieron tramas con la configuración solicitada")
        return False, None

    last = metrics[-1]
    peak_queue = max(m['queue_peak'] for m in metrics)
    min_slack = min(m['slack_min'] for m in metrics)
    dropped = last['dropped']
    fatal = last['fatal']

    passed = (dropped == 0 and fatal == 0 and peak_queue < 16)
    status_str = "PASS" if passed else "FAIL"
    print(f"  Resultado: [{status_str}] Tramas: {frames_received}")
    print(f"  Pérdidas: dropped={dropped}, fatal={fatal}")
    print(f"  Cola pico: {peak_queue}/16 slots (capacidad SRAM3: 16)")
    print(f"  Slack mínimo: {min_slack} ticks")

    res = {
        'rate': config.rate,
        'ticks': config.request_period & 0xffff,
        'frames': frames_received,
        'dropped': dropped,
        'fatal': fatal,
        'queue_peak': peak_queue,
        'slack_min': min_slack,
        'passed': passed
    }
    return passed, res


def main():
    print("=== INICIO DE ENSAYO DE ALTA FRECUENCIA V20 ===")
    apps, containers = get_inventory()
    v19_app = next((a for a in apps if a.get('name') == 'Scope V19' and 'v19' in a.get('id', '')), None)
    if not v19_app:
        v19_app = next((a for a in apps if a.get('name') == 'Scope V19'), None)
    if not v19_app or v19_app.get('status') != 'running':
        print("ADVERTENCIA: Scope V19 no está en estado running. Verificar antes de proceder.")

    v20_app = next((a for a in apps if '225916' in a.get('id', '')), None)
    if not v20_app:
        v20_app = next((a for a in apps if a.get('name') == 'Scope V20'), None)
    if not v20_app:
        raise RuntimeError("No se encontró Scope V20 importada en el UNO Q.")

    # 1. Compilar relay V20
    compile_v20_relay()

    # Asegurar reenvío de puertos ADB
    adb_cmd('forward', 'tcp:8766', 'tcp:8766')

    # Guardar ID de apps
    v19_id = v19_app['id']
    v20_id = v20_app['id']

    results = []
    try:
        print("\n-> Deteniendo temporalmente Scope V19...")
        adb_shell('docker', 'stop', 'serialmonitor-usb-stream-v19')
        adb_shell('arduino-app-cli', 'app', 'stop', '/home/arduino/ArduinoApps/scope-v19')
        time.sleep(1)

        print("-> Iniciando Scope V20 (con buffers en SRAM3)...")
        do_ready_boot()
        adb_shell('arduino-app-cli', 'app', 'start', '/home/arduino/ArduinoApps/scope-v20-20261031-225916')
        time.sleep(3)

        print("-> Levantando contenedor relay V20...")
        # Limpiar contenedor previo si existiera
        adb_shell('docker', 'rm', '-f', 'serialmonitor-usb-stream-v20')
        run_relay = (
            'docker run -d --name serialmonitor-usb-stream-v20 --net host '
            '--user 0:0 --cap-add SYS_NICE --security-opt no-new-privileges '
            '--device /dev/spidev0.0:/dev/spidev0.0:rw '
            '--device /dev/gpiochip1:/dev/gpiochip1:rw '
            '-v /tmp/unoq_stream_v20:/work/unoq_stream:ro '
            '--mount type=bind,src=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor,dst=/scope_cpu_governor '
            '--entrypoint /work/unoq_stream '
            'ghcr.io/arduino/app-bricks/python-apps-base:0.12.0'
        )
        adb_shell(run_relay)

        # Esperar que el relay esté listo
        print("-> Esperando sincronización de primer frame SPI...")
        deadline = time.time() + 20
        relay_ready = False
        while time.time() < deadline:
            out = adb_shell('docker', 'logs', 'serialmonitor-usb-stream-v20')
            logs = (out.stdout or '') + (out.stderr or '')
            if 'SPI ready: first verified frame' in logs:
                relay_ready = True
                break
            time.sleep(0.5)

        if not relay_ready:
            out = adb_shell('docker', 'logs', '--tail', '30', 'serialmonitor-usb-stream-v20')
            logs = (out.stdout or '') + (out.stderr or '')
            print(f"Log del relay:\n{logs}")
            raise RuntimeError("El relay V20 no sincronizó con SPI en 20 segundos.")

        print("-> Relay V20 activo y sincronizado en puerto 8766.")

        # Conectar cliente TCP
        time.sleep(1)
        s = socket.create_connection(('127.0.0.1', 8766), timeout=5.0)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # 1. Probar Baseline: 86 ticks (1.86 MSPS)
        c86 = Configuration(8, 1860465)
        ok86, r86 = run_benchmark_rate(s, c86, duration=5.0)
        results.append(r86)

        # 2. Probar 80 ticks (2.00 MSPS)
        c80 = Configuration(8, 2000000)
        ok80, r80 = run_benchmark_rate(s, c80, duration=5.0)
        results.append(r80)

        # 3. Probar 78 ticks (2.05 MSPS)
        c78 = Configuration(8, 2051282)
        ok78, r78 = run_benchmark_rate(s, c78, duration=5.0)
        results.append(r78)

        s.close()

    finally:
        print("\n=== RESTAURANDO PAREJA V19 ORIGINAL ===")
        adb_shell('docker', 'rm', '-f', 'serialmonitor-usb-stream-v20')
        adb_shell('arduino-app-cli', 'app', 'stop', '/home/arduino/ArduinoApps/scope-v20-20261031-225916')
        time.sleep(1)

        print("-> Reactivando Scope V19...")
        do_ready_boot()
        adb_shell('arduino-app-cli', 'app', 'start', '/home/arduino/ArduinoApps/scope-v19')
        time.sleep(2)
        adb_shell('docker', 'start', 'serialmonitor-usb-stream-v19')
        time.sleep(2)

        apps, containers = get_inventory()
        v19_now = next((a for a in apps if a.get('name') == 'Scope V19'), None)
        status_v19 = v19_now.get('status') if v19_now else 'missing'
        relay_v19 = 'serialmonitor-usb-stream-v19' in containers
        print(f"-> Estado de restauración: App Scope V19={status_v19}, Relay V19={'running' if relay_v19 else 'stopped'}")
        if status_v19 == 'running' and relay_v19:
            print("✓ Scope V19 restaurada y corriendo como pareja activa única.")
        else:
            print("ADVERTENCIA: Revisar estado final de V19.")

    print("\n=== RESUMEN DE RESULTADOS DE ALTA FRECUENCIA V20 ===")
    for r in results:
        if r:
            st = "PASS" if r['passed'] else "FAIL"
            print(f"  Tasa {r['rate']} Hz ({r['ticks']} ticks): [{st}] dropped={r['dropped']} fatal={r['fatal']} cola_pico={r['queue_peak']}/16 slack={r['slack_min']}")


if __name__ == '__main__':
    raise SystemExit('Ensayo anterior deshabilitado: usar tools/probe_v20_sram3.py con --serial y --output para CRC/ACK y restauración verificados.')
