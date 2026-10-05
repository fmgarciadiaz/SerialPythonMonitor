#!/usr/bin/env python3
"""Inicia/detiene el relay SPI → USB/ADB; no cambia los servicios USB del Q."""
import argparse
import hashlib
import json
import time
from unoq import Board, ROOT, config_path
from spi_benchmark import BUILD_IMAGE, IMAGE

CONTAINER = 'serialmonitor-usb-stream'


def binary(board, build=False, dual=False, configurable=False, experimental=False, diagnostic=False, p992=False):
    relay = 'experimentos/timing_spi/relay/unoq_config_stream.c' if diagnostic else 'experimentos/tasas_spi/relay/unoq_config_stream.c' if experimental else ('transport/unoq_config_stream.c' if configurable else ('transport/unoq_dual_stream.c' if dual else 'transport/unoq_stream.c'))
    if p992:
        relay = 'arduino/v11_p992/relay/unoq_config_stream.c'
    sources = [relay, 'arduino/v11_p992/relay/base_verifier.c' if p992 else 'diagnosticos/verificar_spi.c']
    if p992:
        sources.append('arduino/v11_p992/relay/config_relay_protocol.h')
    elif diagnostic:
        sources.append('experimentos/timing_spi/relay/config_relay_protocol.h')
    elif experimental:
        sources.append('experimentos/tasas_spi/relay/config_relay_protocol.h')
    elif configurable:
        sources.append('transport/config_relay_protocol.h')
    elif dual:
        sources.append('transport/dual_protocol.h')
    digest = hashlib.sha256(b''.join((ROOT/p).read_bytes() for p in sources)).hexdigest()
    folder = '/home/arduino/.cache/serialmonitor/usb-stream-' + digest[:20]
    if build:
        for relative in sources:
            target = folder + '/' + relative
            board.shell('mkdir', '-p', target.rsplit('/', 1)[0])
            board.run('push', str(ROOT/relative), target)
        board.shell('docker', 'run', '--rm', '--user', '0:0', '--security-opt', 'no-new-privileges',
                    '--mount', f'type=bind,src={folder},dst=/build', '--entrypoint', 'sh', BUILD_IMAGE,
                    '-c', 'apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev '
                    f'&& cc -O2 -std=c11 -Wall -Wextra -Werror /build/{relay} '
                    '-lm -o /build/unoq_stream')
    board.shell('test', '-x', folder + '/unoq_stream')
    return folder + '/unoq_stream'


def stop(board):
    # Remove only our named, disposable relay container, never other apps.
    names = board.shell('docker', 'ps', '-a', '--format', '{{.Names}}', capture=True).stdout.splitlines()
    if CONTAINER in names:
        board.shell('docker', 'stop', '--time', '3', CONTAINER)
        board.shell('docker', 'rm', CONTAINER)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('start', 'stop', 'status', 'logs', 'build'))
    parser.add_argument('--build-native', action='store_true')
    parser.add_argument('--firmware', choices=('v6_adc', 'v7_dual', 'v8_config', 'v9_fast', 'v10_diag', 'v11_p992'), default='v8_config')
    args = parser.parse_args()
    board = Board(json.loads(config_path(args.firmware).read_text()))
    if args.command == 'build':
        print(binary(board, build=True, dual=args.firmware == 'v7_dual', configurable=args.firmware in ('v8_config','v9_fast','v10_diag'), experimental=args.firmware == 'v9_fast', diagnostic=args.firmware == 'v10_diag', p992=args.firmware == 'v11_p992'))
    elif args.command == 'start':
        target = binary(board, args.build_native, dual=args.firmware == 'v7_dual', configurable=args.firmware in ('v8_config','v9_fast','v10_diag'), experimental=args.firmware == 'v9_fast', diagnostic=args.firmware == 'v10_diag', p992=args.firmware == 'v11_p992')
        stop(board)
        # Reset acquisition counters/queue before taking over READY.
        board.start()
        board.shell('docker', 'run', '-d', '--name', CONTAINER,
                    '--network', 'host', '--read-only', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--user', '0:0',
                    '--device', '/dev/spidev0.0:/dev/spidev0.0:rw',
                    '--device', '/dev/gpiochip1:/dev/gpiochip1:rw',
                    '--mount', f'type=bind,src={target},dst=/work/unoq_stream,readonly',
                    '--entrypoint', '/work/unoq_stream', IMAGE)
        time.sleep(1)
        state = json.loads(board.shell('docker', 'inspect', '--format', '{{json .State}}', CONTAINER, capture=True).stdout)
        if not state.get('Running'):
            board.shell('docker', 'logs', '--tail', '20', CONTAINER)
            raise RuntimeError('El relay no quedó en ejecución.')
        if args.firmware == 'v11_p992':
            print('Relay P992 iniciado. Abrir: python monitor/v12/app.py (SCP1 V3/992).')
        elif args.firmware == 'v10_diag':
            print('Relay de diagnóstico iniciado. Usar experimentos/timing_spi; no abrir V11.')
        elif args.firmware == 'v9_fast':
            print('Relay experimental iniciado. Abrir: python monitor/v11/app.py; CLI en experimentos/tasas_spi.')
        elif args.firmware == 'v8_config':
            print('Relay configurable iniciado. Abrir: python monitor/v10/app.py')
        else:
            print('Relay dual iniciado. Abrir: python monitor/historico/v9/app.py' if args.firmware == 'v7_dual'
              else 'Relay iniciado. Abrir: python monitor/historico/v8/app.py')
    elif args.command == 'stop':
        stop(board)
    elif args.command == 'status':
        board.shell('docker', 'inspect', '--format', '{{json .State}}', CONTAINER)
    else:
        board.shell('docker', 'logs', '--tail', '30', CONTAINER)


if __name__ == '__main__':
    main()
