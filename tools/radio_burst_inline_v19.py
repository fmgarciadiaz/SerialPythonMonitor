"""Private RADIO40k cadence experiments; preserve the production inline ACK path."""
from contextlib import contextmanager
import os

ENV = 'ARDUSCOPIO_PRIVATE_RADIO_BURST'
INTERVAL_ENV = 'ARDUSCOPIO_PRIVATE_RADIO_INTERVAL_MS'
STARTUP_ENV = 'ARDUSCOPIO_PRIVATE_RADIO_STARTUP_ONLY'
POLL_ENV = 'ARDUSCOPIO_PRIVATE_RADIO_POLL_MS'
PLAY_ENV = 'ARDUSCOPIO_PRIVATE_RADIO_PLAY_BURST'


def selected_descriptor(descriptor, burst, interval_ms=None, poll_ms=None):
    if burst not in (1, 4, 8):
        raise ValueError('Only private prefill 1, reviewed burst 4/control 8 are supported')
    if interval_ms not in (None, 6, 8, 10):
        raise ValueError('Private intervals are 6/control, 8 or 10 ms')
    if poll_ms not in (None,12,24,30,40):raise ValueError('Private query intervals are 12, 24, 30 or 40 ms')
    result = dict(descriptor)
    if result.get('radio_audio') is True and result.get('rate') == 40000:
        result['chunk_burst'] = burst
        if interval_ms is not None:
            result['chunk_interval'] = interval_ms / 1000
        if poll_ms is not None:result['poll_interval']=poll_ms/1000
    return result


@contextmanager
def inline_burst(burst, interval_ms=None, startup_only=False, poll_ms=None, play_burst=None):
    from monitor.v19.io.receiver_process import RemotePcmSource
    from monitor.v19.receiver.unoq_config_receiver import OutputReceiver
    if (burst not in (1, 4, 8) or (burst==1 and not startup_only) or interval_ms not in (None, 6, 8, 10) or poll_ms not in (None,12,24,30,40)
            or play_burst not in (None,1,2) or (play_burst is not None and not startup_only)
            or not OutputReceiver._radio_chunk_ack_refresh):
        raise ValueError('Reviewed burst and production inline ACK required')
    original = RemotePcmSource.__init__
    service = OutputReceiver.service_wav
    def initialize(source, descriptor, emit):
        original(source, selected_descriptor(descriptor, burst, interval_ms,poll_ms), emit)
    RemotePcmSource.__init__ = initialize
    if startup_only:
        def service_after_start(receiver):
            source=receiver.wav_codes
            if (receiver.wav_started and source is not None and
                    getattr(source,'radio_audio',False) and receiver.wav_rate==40000):
                # Default arm restores accepted PLAY. The separately declared
                # private PLAY arm caps burst only, retaining 6 ms recovery.
                source.chunk_burst=8 if play_burst is None else play_burst
                source.chunk_interval=.006
            return service(receiver)
        OutputReceiver.service_wav=service_after_start
    try:
        yield
    finally:
        RemotePcmSource.__init__ = original
        OutputReceiver.service_wav = service


@contextmanager
def burst_metrics_connection(serial):
    from tools.relay_wire_metrics_v19 import accepted_metrics_connection
    burst = int(os.environ[ENV])
    interval = os.environ.get(INTERVAL_ENV)
    with inline_burst(burst, None if interval is None else int(interval),
                      os.environ.get(STARTUP_ENV)=='1'), accepted_metrics_connection(serial) as connection:
        yield connection


def main():
    import argparse
    import sys
    from pathlib import Path
    from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV, set_metrics_profile
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--private-burst', type=int, choices=(4, 8), required=True)
    parser.add_argument('--private-interval-ms', type=int, choices=(6, 8, 10))
    parser.add_argument('--startup-only',action='store_true',
                        help='Use selected cadence for prefill; restore 8/6ms when PLAY is submitted')
    parser.add_argument('--metrics-output', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    os.environ[ENV] = str(args.private_burst)
    os.environ[STARTUP_ENV]='1' if args.startup_only else '0'
    if args.private_interval_ms is None:
        os.environ.pop(INTERVAL_ENV, None)
    else:
        os.environ[INTERVAL_ENV] = str(args.private_interval_ms)
    path = args.metrics_output.resolve()
    if path.exists():
        parser.error('New metrics output required')
    os.environ[METRICS_ENV] = str(path)
    target_parser = argparse.ArgumentParser(add_help=False)
    target_parser.add_argument('--bits', type=int, required=True)
    target_parser.add_argument('--rate', type=int, required=True)
    target, _ = target_parser.parse_known_args(remaining)
    set_metrics_profile(target.bits, target.rate)
    from monitor.v19.io import receiver_process
    original = receiver_process.ReceiverProcess
    class BurstReceiverProcess(original):
        def __init__(self, *values, **options):
            options.update(connection_factory=burst_metrics_connection,
                           capture_lifecycle=True,
                           snapshot_dir=str(path.parent / 'sessions'))
            super().__init__(*values, **options)
    receiver_process.ReceiverProcess = BurstReceiverProcess
    sys.argv = [str(Path(__file__).with_name('gui_live_smoke_v19.py')), *remaining]
    from tools.gui_live_smoke_v19 import main as smoke
    try:
        return smoke()
    finally:
        receiver_process.ReceiverProcess = original


if __name__ == '__main__':
    # The tool also runs directly from the repository root.
    from pathlib import Path
    import sys
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    raise SystemExit(main())
