#!/usr/bin/env python3
"""Same GUI smoke/counter observer with the strict accepted production pair."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.relay_wire_metrics_v19 import ENV,ACK_LATENCY_ENV,accepted_metrics_connection


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metrics-output',required=True,type=Path)
    parser.add_argument('--ack-latency',action='store_true',help='Private raw-read versus decoded ACK timing')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--private-ack-refresh',action='store_true',
                        help='Private RADIO40k ACK/QUERY candidate; no production edits')
    mode.add_argument('--private-ack-sham',action='store_true',
                      help='Same private callback wrapper without deadline renewal')
    mode.add_argument('--private-ack-burst2',action='store_true',
                      help='Private ACK renewal plus RADIO40k chunk burst limit 2')
    args,remaining=parser.parse_known_args();path=args.metrics_output.resolve()
    os.environ[ENV]=str(path)
    os.environ[ACK_LATENCY_ENV]='1' if args.ack_latency else '0'
    factory=accepted_metrics_connection
    if args.private_ack_refresh:
        from tools.radio_query_candidate_v19 import candidate_metrics_connection
        factory=candidate_metrics_connection
    elif args.private_ack_sham:
        from tools.radio_query_candidate_v19 import sham_metrics_connection
        factory=sham_metrics_connection
    elif args.private_ack_burst2:
        from tools.radio_query_candidate_v19 import burst2_metrics_connection
        factory=burst2_metrics_connection
    from tools.relay_wire_metrics_v19 import set_metrics_profile
    target_parser=argparse.ArgumentParser(add_help=False)
    target_parser.add_argument('--bits',type=int,default=8)
    target_parser.add_argument('--rate',type=int,default=1600000)
    target,_=target_parser.parse_known_args(remaining)
    set_metrics_profile(target.bits,target.rate)
    from monitor.v19.io import receiver_process
    original=receiver_process.ReceiverProcess
    class MetricsReceiverProcess(original):
        def __init__(self,*values,**options):
            options.update(connection_factory=factory,capture_lifecycle=True,
                           snapshot_dir=str(path.parent/'accepted_gui_sessions'))
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=MetricsReceiverProcess
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v19.py'),*remaining]
    from tools.gui_live_smoke_v19 import main as smoke
    try:return smoke()
    finally:receiver_process.ReceiverProcess=original


if __name__=='__main__':raise SystemExit(main())
