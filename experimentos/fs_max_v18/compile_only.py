"""Compile isolated sources at low ADC load. Never installs candidate firmware."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.unoq import Board
from monitor.v18.io.live_connection import installed_connection
from monitor.v18.io.receiver_lifecycle import ReceiverLifecycle
from monitor.v18.receiver.unoq_config_receiver import OutputReceiver
from monitor.v18.receiver.unoq_acquisition import Configuration

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifacts",type=Path)
    args=parser.parse_args()
    folder=Path(__file__).resolve().parent
    config=json.loads((ROOT/'arduino/v18/unoq.json').read_text())
    config['local_app']='experimentos/fs_max_v18/oscilloscope'
    board=Board(config)
    report=dict(compiled=False,installed=False,restored=False)
    try:
        with installed_connection(board.serial) as connection:
            receiver=OutputReceiver(connection,lambda records:None)
            receiver.decoder.numeric=True
            lifecycle=ReceiverLifecycle(receiver,connection.identity)
            lifecycle.capture()
            try:
                receiver.select(0)
                receiver.configure(Configuration(14,40000))
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(board.compile,args.artifacts)
                    while not future.done():receiver.pump()
                    future.result()
                report['compiled']=True
            finally:
                result=lifecycle.restore()
                report['restoration']=result
                report['restored']=result['hardware_restored']
    except Exception as exc:
        report['error']=repr(exc)
    path=folder/'compile_report.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['compiled'] and report['restored'] else 1
if __name__=='__main__':raise SystemExit(main())
