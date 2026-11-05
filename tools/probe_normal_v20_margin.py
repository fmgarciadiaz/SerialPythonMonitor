#!/usr/bin/env python3
"""One short V20 GUI/A0 observation with the normal product rate and audio guards."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
OUTPUT_ENV='ARDUSCOPIO_NORMAL_V20_MARGIN_OUTPUT'


@contextmanager
def observed_connection(serial):
    from monitor.v20.io.live_connection import installed_connection
    from monitor.v20.receiver.unoq_acquisition import Configuration
    from monitor.v20.receiver.unoq_config_receiver import OutputReceiver
    from tools.relay_wire_metrics_v19 import observe_connection
    folder=Path(os.environ[OUTPUT_ENV])
    with installed_connection(serial) as connected:
        with observe_connection(connected,folder/'wire_metrics.json',
                                receiver_class=OutputReceiver,configuration=Configuration):
            yield connected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rate',type=int,choices=(1860465,2000000),required=True)
    args=parser.parse_args()
    folder=args.output.resolve()
    if folder.exists() or not folder.is_relative_to(ROOT/'diagnosticos/resultados_v20'):
        parser.error('A new directory under diagnosticos/resultados_v20 is required')
    folder.mkdir(parents=True)
    os.environ[OUTPUT_ENV]=str(folder)
    os.environ['MONITOR_V19_CHILD_STAGE_TIMING']='0'
    os.environ['ARDUSCOPIO_PRIVATE_RAW_ACK_LATENCY']='0'
    from monitor.v20.receiver.unoq_acquisition import Configuration
    from tools.relay_wire_metrics_v19 import set_metrics_profile
    set_metrics_profile(8,args.rate,configuration=Configuration)
    from monitor.v20.io import receiver_process
    original=receiver_process.ReceiverProcess
    class ObservedReceiver(original):
        def __init__(self,*values,**options):
            options.update(connection_factory=observed_connection,capture_lifecycle=True,
                           snapshot_dir=str(folder/'sessions'),recovery_seconds=10)
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=ObservedReceiver
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v20.py'),
              '--serial',args.serial,'--output',str(folder/'gui.json'),
              '--bits','8','--rate',str(args.rate),'--fft-size','16384',
              '--frequency-khz','710','--hold-radio-seconds','20',
              '--duration','25','--no-retune']
    try:
        from tools.gui_live_smoke_v20 import main as smoke
        smoke()
    finally:
        receiver_process.ReceiverProcess=original
    gui=json.loads((folder/'gui.json').read_text())
    metrics=json.loads((folder/'wire_metrics.json').read_text())
    sessions=[json.loads(path.read_text()) for path in (folder/'sessions').glob('session_*.json')]
    periodic=[row for row in gui['stages'] if row['stage']=='periodic']
    restored=bool(sessions) and all(s.get('hardware_restored') is True and
        s.get('recovery',{}).get('seconds',0)>=10 and not s.get('errors') for s in sessions)
    report=dict(profile=metrics.get('profile'),rate=args.rate,
        method='normal V20 selector/A0; read-only WireMetrics; native-only diagnostics; no rate/audio override',
        hold_seconds=gui.get('radio_hold_seconds'),playing=metrics.get('radio_playing'),
        all=metrics.get('all'),exposed=sum(bool(s.get('exposed')) for s in periodic),
        periodic=len(periodic),gui_assertions=gui.get('assertions'),gui_errors=gui.get('errors'),
        sessions=sessions,restored=restored,
        ok=not gui.get('errors') and all(gui.get('assertions',{}).values()) and restored)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'ok':report['ok'],'rate':args.rate,'playing_margin':report['playing'].get('mean_send_margin'),
                      'all_margin':report['all'].get('mean_send_margin'),
                      'exposed':f"{report['exposed']}/{report['periodic']}",
                      'restored':restored,'report':str(folder/'report.json')}),flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
