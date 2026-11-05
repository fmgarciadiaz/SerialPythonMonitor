#!/usr/bin/env python3
"""GUI smoke with a separate exact firmware binding, never a receipt override."""
import argparse
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.private_firmware_v19 import ENV,binding_identity,private_connection


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--firmware-binding',required=True,type=Path)
    args,remaining=parser.parse_known_args()
    os.environ[ENV]=str(args.firmware_binding.resolve())
    from tools.relay_wire_metrics_v19 import ENV as METRICS_ENV
    os.environ[METRICS_ENV]=str(args.firmware_binding.resolve().parent/'wire_metrics.json')
    serial_parser=argparse.ArgumentParser(add_help=False);serial_parser.add_argument('--serial',required=True)
    serial,_=serial_parser.parse_known_args(remaining);binding_identity(serial.serial)
    from tools.relay_wire_metrics_v19 import set_metrics_profile
    target_parser=argparse.ArgumentParser(add_help=False)
    target_parser.add_argument('--bits',type=int,default=8)
    target_parser.add_argument('--rate',type=int,default=1600000)
    target,_=target_parser.parse_known_args(remaining)
    set_metrics_profile(target.bits,target.rate)
    from monitor.v19.io import receiver_process
    original=receiver_process.ReceiverProcess
    class PrivateFirmwareReceiver(original):
        def __init__(self,*values,**options):
            options.update(connection_factory=private_connection,capture_lifecycle=True,
                snapshot_dir=str(args.firmware_binding.resolve().parent/'private_gui_sessions'))
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=PrivateFirmwareReceiver
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v19.py'),*remaining]
    from tools.gui_live_smoke_v19 import main as smoke
    try:return smoke()
    finally:receiver_process.ReceiverProcess=original


if __name__=='__main__':raise SystemExit(main())
