"""Private receiver-stage capture with accepted Q pair and existing timers."""
from contextlib import contextmanager
from collections import deque
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
TRACE_ENV='ARDUSCOPIO_PRIVATE_READER_STAGE_REPORT'
BACKOFF_ENV='ARDUSCOPIO_PRIVATE_IPC_EMPTY_BACKOFF_US'


@contextmanager
def capture_stage_connection(serial):
    from tools.relay_wire_metrics_v19 import accepted_metrics_connection
    from monitor.v19.receiver import unoq_config_receiver as core
    from monitor.v19.q_support.prepare import atomic_report
    if not core._child_stage_timing_enabled:raise RuntimeError('Existing receiver timers must be explicitly enabled')
    cls=core._ChildStageTiming;initialize=cls.__init__;observe=cls._observe
    instances=[];instance_ids=set();slow=deque(maxlen=64)
    def register(tracker):
        if id(tracker) not in instance_ids and len(instances)<8:
            instances.append(tracker);instance_ids.add(id(tracker))
    def start(tracker):
        initialize(tracker)
        register(tracker)
    def measured(tracker,stage,start,end,cpu_seconds=None,**details):
        # The receiver-process tracker may predate connection entry.
        register(tracker)
        observe(tracker,stage,start,end,cpu_seconds,**details)
        if end-start>=.1:
            slow.append(dict(tracker=hex(id(tracker)),stage=stage,start=start,end=end,
                wall_ms=(end-start)*1000,cpu_ms=None if cpu_seconds is None else cpu_seconds*1000,
                active=[entry[0] for entry in tracker.active],details=details))
    cls.__init__=start;cls._observe=measured
    from tools.ipc_wait_timing_v19 import QueueWaitTiming
    ipc=QueueWaitTiming(lambda: [entry[0] for tracker in instances for entry in tracker.active])
    from tools.ipc_empty_backoff_v19 import empty_backoff
    backoff={}
    try:
        with ipc.installed(), empty_backoff(int(os.environ.get(BACKOFF_ENV,'0'))) as backoff:
            with accepted_metrics_connection(serial) as connection:yield connection
    finally:
        try:
            atomic_report(Path(os.environ[TRACE_ENV]),dict(slow=list(slow),
                ipc=ipc.report(),
                private_empty_backoff=backoff,
                trackers=[dict(id=hex(id(t)),snapshot=t.snapshot(detail=True)) for t in instances],
                note='Private capture of existing opt-in wall/thread-CPU timers. Includes restoration; slow ring retains >=100ms stages beyond the normal 3s trace window. No RF arrays retained.'))
        finally:cls.__init__=initialize;cls._observe=observe


def main():
    import argparse
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metrics-output',type=Path,required=True)
    parser.add_argument('--stage-output',type=Path,required=True)
    parser.add_argument('--ipc-empty-backoff-us',type=int,choices=(0,500),default=0)
    args,remaining=parser.parse_known_args()
    if args.metrics_output.exists() or args.stage_output.exists():parser.error('New diagnostic outputs required')
    if args.metrics_output.resolve()==args.stage_output.resolve():parser.error('Distinct report paths required')
    os.environ[TRACE_ENV]=str(args.stage_output.resolve())
    os.environ[BACKOFF_ENV]=str(args.ipc_empty_backoff_us)
    os.environ['MONITOR_V19_CHILD_STAGE_TIMING']='1'
    from tools.relay_wire_metrics_v19 import ENV,ACK_LATENCY_ENV,set_metrics_profile
    os.environ[ENV]=str(args.metrics_output.resolve());os.environ[ACK_LATENCY_ENV]='1'
    target=argparse.ArgumentParser(add_help=False)
    target.add_argument('--bits',type=int,required=True);target.add_argument('--rate',type=int,required=True)
    profile,_=target.parse_known_args(remaining);set_metrics_profile(profile.bits,profile.rate)
    from monitor.v19.io import receiver_process
    original=receiver_process.ReceiverProcess
    class StageReceiverProcess(original):
        def __init__(self,*values,**options):
            options.update(connection_factory=capture_stage_connection,capture_lifecycle=True,
                           snapshot_dir=str(args.metrics_output.resolve().parent/'sessions'))
            super().__init__(*values,**options)
    receiver_process.ReceiverProcess=StageReceiverProcess
    sys.argv=[str(ROOT/'tools/gui_live_smoke_v19.py'),*remaining]
    from tools.gui_live_smoke_v19 import main as smoke
    try:return smoke()
    finally:receiver_process.ReceiverProcess=original


if __name__=='__main__':raise SystemExit(main())
