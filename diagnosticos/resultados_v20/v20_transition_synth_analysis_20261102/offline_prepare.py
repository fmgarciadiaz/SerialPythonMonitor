"""Diagnostic measurement only: spawn and prepare Synth without any Q imports."""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monitor.v20.synth_process import initialize_worker,prepare,render
from monitor.v20.fm_source import FMParameters


def main():
    parameters=FMParameters(notes=tuple((note,100) for note in range(48,68)))
    began=time.monotonic()
    with ProcessPoolExecutor(max_workers=1,mp_context=mp.get_context('spawn'),initializer=initialize_worker) as pool:
        future=pool.submit(prepare,20000,parameters)
        submitted=time.monotonic();ready_at_smoke_stop=None
        try:
            ready_at_smoke_stop=future.done()
            while not future.done():
                elapsed=time.monotonic()-began
                if elapsed>=10.393 and ready_at_smoke_stop is not True:
                    ready_at_smoke_stop=future.done()
                if elapsed>120:raise TimeoutError('Offline Synth preparation exceeded 120 s')
                time.sleep(.05)
            result=future.result();prepared=time.monotonic()
            codes,metrics=pool.submit(render,0,480,parameters,(1.,1.65)).result(30)
            report=dict(ok=bool(result),rate=20000,voices=20,submit_seconds=submitted-began,
                prepare_seconds=prepared-began,smoke_stop_after_request_seconds=10.393,
                exceeds_smoke_window=prepared-began>10.393,rendered_samples=len(codes),render_metrics=metrics,
                scope='Offline host spawn/prepare/render only; no Q. Not the exact prior failed process.')
        except BaseException as exc:
            report=dict(ok=False,error=repr(exc),elapsed_seconds=time.monotonic()-began)
    Path(__file__).with_name('offline_prepare.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
