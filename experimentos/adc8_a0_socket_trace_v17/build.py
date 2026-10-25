"""Build the isolated Linux relay with acquisition stopped; restore and verify Q."""
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]


def main():
    from experimentos.adc8_a0_socket_trace_v17.run import certified_sources
    from experimentos.otros_bits_cpu_relay_v17.run import RelayCampaign
    from tools.unoq import Board, config_path
    from monitor.v17.board_owner import board_owner
    from spi_benchmark import IMAGE
    import usb_stream
    _, _, sources, hashes = certified_sources()
    x = RelayCampaign.__new__(RelayCampaign)
    x.board = Board(json.loads(config_path('v17').read_text()))
    x.folder = Path(__file__).parent/('build_'+time.strftime('%Y%m%d_%H%M%S'))
    x.folder.mkdir()
    x.sources = sources
    x.normal = None
    x.report = dict(ok=False, restored=False, cases=[], source_hashes=hashes)
    stopped = False
    with board_owner(x.board.serial, 'Build isolated socket trace with acquisition stopped'):
        try:
            x.snapshot()
            info = json.loads(x.board.shell('docker','inspect',usb_stream.CONTAINER,capture=True).stdout)[0]
            x.normal = x.policy()
            x.report.update(old_mounts=info['Mounts'], old_cpuset=info['HostConfig']['CpusetCpus'])
            stopped = True
            usb_stream.stop(x.board)
            x.board.stop()
            x.build()
            x.report['binary_sha256'] = x.board.shell('sha256sum',x.relay,capture=True).stdout.split()[0]
            x.report['ok'] = True
        except BaseException as exc:
            x.report.update(error=repr(exc), traceback=traceback.format_exc())
        finally:
            try:
                if stopped:
                    x.board.start()
                    flags = []
                    for cap in x.report['old_cap_add']: flags += ['--cap-add',cap]
                    for mount in x.report['old_mounts']:
                        flags += ['--mount',f"type=bind,src={mount['Source']},dst={mount['Destination']}"+('' if mount['RW'] else ',readonly')]
                    for env in x.report['old_scope_environment']: flags += ['--env',env]
                    if x.report['old_cpuset']: flags += ['--cpuset-cpus',x.report['old_cpuset']]
                    x.board.shell('docker','run','-d','--name',usb_stream.CONTAINER,'--network','host','--read-only',
                                  '--cap-drop','ALL',*flags,'--security-opt','no-new-privileges','--user','0:0',
                                  '--device','/dev/spidev0.0:/dev/spidev0.0:rw','--device','/dev/gpiochip1:/dev/gpiochip1:rw',
                                  '--entrypoint','/work/unoq_stream',IMAGE)
                if x.report.get('prior'): x.restore_settings()
            except BaseException as exc:
                x.report.update(ok=False, restored=False, restore_error=repr(exc))
            x.save()
            print('REPORT',x.folder/'report.json',flush=True)
    return x.report


if __name__ == '__main__':
    result = main()
    raise SystemExit(0 if result['ok'] and result['restored'] else 1)
