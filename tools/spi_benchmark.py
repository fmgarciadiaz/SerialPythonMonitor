#!/usr/bin/env python3
"""Ejecuta el verificador en el MPU del UNO Q y guarda su salida localmente."""
import argparse
import hashlib
from datetime import datetime
import json
import math
import shlex
import subprocess
import uuid

from unoq import Board, ROOT, config_path


IMAGE = 'ghcr.io/arduino/app-bricks/python-apps-base:0.12.0'
BUILD_IMAGE = 'debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a'


def native_binary(board, build=False):
    source = ROOT / 'diagnosticos/verificar_spi.c'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # El ejecutable sobrevive a reinicios; sólo el contenedor de compilación es efímero.
    folder = '/home/arduino/.cache/serialmonitor/spi-native-' + digest[:20]
    binary = folder + '/verificar_spi'
    if build:
        board.shell('mkdir', '-p', folder)
        board.run('push', str(source), folder + '/verificar_spi.c')
        # Sólo el contenedor efímero instala paquetes; el sistema del Q no cambia.
        board.shell('docker', 'run', '--rm', '--user', '0:0', '--security-opt', 'no-new-privileges',
                    '--mount', f'type=bind,src={folder},dst=/build', '--entrypoint', 'sh', BUILD_IMAGE,
                    '-c', 'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev '
                    '&& cc -O2 -std=c11 -Wall -Wextra -Werror /build/verificar_spi.c '
                    '-lm -o /build/verificar_spi')
    board.shell('test', '-x', binary)
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hz', type=int, default=1000000)
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--gap-us', type=float, default=None)
    parser.add_argument('--implementation', choices=('python', 'c'), default='python')
    parser.add_argument('--firmware', choices=('v6', 'v6_polling', 'v6_dma', 'v6_irq', 'v6_adc'), default='v6')
    parser.add_argument('--build-native', action='store_true',
                        help='Sólo compilar C en un contenedor temporal con paquetes Debian; requiere red.')
    args = parser.parse_args()
    if args.gap_us is None:
        args.gap_us = 0 if args.firmware in ('v6_irq', 'v6_adc') else 1000
    if args.firmware in ('v6_irq', 'v6_adc') and not args.build_native and (args.implementation != 'c' or args.gap_us != 0):
        parser.error('IRQ/ADC requiere --implementation c y --gap-us 0: sincroniza por READY.')
    if not (0 < args.hz <= 0xffffffff and math.isfinite(args.seconds)
            and args.seconds > 0 and math.isfinite(args.gap_us) and args.gap_us >= 0):
        parser.error('Frecuencia y duración positivas; pausa finita no negativa.')
    board = Board(json.loads(config_path(args.firmware).read_text()))
    if args.build_native:
        print('Binario C:', native_binary(board, build=True))
        return 0
    apps = json.loads(board.cli('app', 'list', '--format', 'json', capture=True).stdout)
    matches = [app for app in apps.get('apps', []) if app.get('name') == board.config['name']]
    print('Aplicación:', json.dumps(matches, ensure_ascii=False), flush=True)
    if len(matches) != 1 or matches[0].get('status') != 'running':
        parser.error(f'Iniciar {args.firmware} y esperar que termine tools/unoq.py start antes de medir.')
    remote = '/tmp/verificar-spi-' + uuid.uuid4().hex + '.py'
    folder = ROOT / 'diagnosticos/resultados_spi'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
    try:
        if args.implementation == 'c':
            target = native_binary(board)
            mount = f'type=bind,src={target},dst=/work/verificar_spi,readonly'
            executable = '/work/verificar_spi'
            prefix = []
        else:
            board.run('push', str(ROOT / 'diagnosticos/verificar_spi.py'), remote)
            mount = f'type=bind,src={remote},dst=/work/verificar_spi.py,readonly'
            executable = 'python3'
            prefix = ['/work/verificar_spi.py']
        ready_options = ['--ready-chip', '/dev/gpiochip1', '--ready-line', '70'] if args.firmware in ('v6_irq', 'v6_adc') else []
        gpio_device = ['--device', '/dev/gpiochip1:/dev/gpiochip1:rw'] if ready_options else []
        command = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--user', '0:0', '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
                   *gpio_device, '--mount', mount, '--entrypoint', executable, IMAGE,
                   *prefix, '--hz', str(args.hz),
                   '--seconds', str(args.seconds), '--gap-us', str(args.gap_us), *ready_options, *(['--adc'] if args.firmware == 'v6_adc' else [])]
        with output.open('w') as log:
            source = ROOT / ('diagnosticos/verificar_spi.c' if args.implementation == 'c'
                             else 'diagnosticos/verificar_spi.py')
            log.write(json.dumps({'implementation': args.implementation, 'firmware': args.firmware,
                                 'sketch_files_sha256': {str(p.relative_to(board.local)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((board.local/'sketch').glob('*')) if p.is_file()},
                                 'sketch_sha256': hashlib.sha256((board.local/'sketch/sketch.ino').read_bytes()).hexdigest(),
                                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}) + '\n')
            with subprocess.Popen([board.adb, '-s', board.serial, 'shell', shlex.join(command)],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
                for line in proc.stdout:
                    print(line, end='', flush=True)
                    log.write(line)
                    log.flush()
                result = proc.wait()
        print(f'Resultado guardado: {output}')
        return result
    finally:
        board.shell('python3', '-c',
                    'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)', remote)


if __name__ == '__main__':
    raise SystemExit(main())
