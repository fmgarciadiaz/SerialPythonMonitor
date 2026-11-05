#!/usr/bin/env python3
"""Run the existing GUI smoke using one exact, explicit private relay binding."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_relay_gui_v19 import ENV,ACK_ENV,binding_identity,private_connection


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--binding',required=True,type=Path)
    parser.add_argument('--metrics',action='store_true')
    parser.add_argument('--private-ack-refresh',action='store_true')
    parser.add_argument('--inline-burst',type=int,choices=(1,4,8))
    parser.add_argument('--inline-interval-ms',type=int,choices=(6,8,10))
    parser.add_argument('--startup-only',action='store_true')
    args,remaining=parser.parse_known_args()
    if (args.inline_interval_ms is not None or args.startup_only) and args.inline_burst is None:
        parser.error('Explicit inline burst required')
    if args.inline_burst is not None and args.private_ack_refresh:parser.error('Inline arm cannot replay legacy ACK')
    if args.inline_burst==1 and not args.startup_only:parser.error('Burst1 is prefill-only; explicit startup-only required')
    from tools.radio_burst_inline_v19 import ENV as BURST_ENV,INTERVAL_ENV,STARTUP_ENV
    for key in (BURST_ENV,INTERVAL_ENV,STARTUP_ENV):os.environ.pop(key,None)
    if args.inline_burst is not None:os.environ[BURST_ENV]=str(args.inline_burst)
    if args.inline_interval_ms is not None:os.environ[INTERVAL_ENV]=str(args.inline_interval_ms)
    if args.startup_only:os.environ[STARTUP_ENV]='1'
    os.environ[ENV]=str(args.binding.resolve())
    if args.private_ack_refresh:os.environ[ACK_ENV]='1'
    else:os.environ.pop(ACK_ENV,None)
    from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV
    if args.metrics:os.environ[METRICS_ENV]=str(args.binding.resolve().parent/'wire_metrics.json')
    else:os.environ.pop(METRICS_ENV,None)
    serial_parser=argparse.ArgumentParser(add_help=False)
    serial_parser.add_argument('--serial',required=True)
    serial,_=serial_parser.parse_known_args(remaining)
    binding_identity(serial.serial)
    from monitor.v19.io import receiver_process
    original=receiver_process.ReceiverProcess
    class PrivateReceiverProcess(original):
        def __init__(self,*values,**options):
            options.update(connection_factory=private_connection,capture_lifecycle=True,
                           snapshot_dir=str(args.binding.resolve().parent/'private_gui_sessions'))
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=PrivateReceiverProcess
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v19.py'),*remaining]
    from tools.gui_live_smoke_v19 import main as smoke
    try:return smoke()
    finally:receiver_process.ReceiverProcess=original


if __name__=='__main__':raise SystemExit(main())
