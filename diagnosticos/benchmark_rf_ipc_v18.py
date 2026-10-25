"""Local decoder -> bounded spawn Queue -> exact consumer comparison. No Q/ADB.

Run as: python -m diagnosticos.benchmark_rf_ipc_v18 --output path.json
One message per RF frame, historical tuples versus the numeric V18 contract.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import multiprocessing as mp
from multiprocessing.reduction import ForkingPickler
from pathlib import Path
import platform
import queue
import sys
import time
import numpy as np
from monitor.v18.io.prototype import Rf,RfBarrier
from monitor.v18.io.wire_adapter import ProtocolIngress
from monitor.v18.receiver.unoq_acquisition import Configuration
from monitor.v18.receiver.unoq_native import PROFILES,code
from tests.v18.io.rf_vectors import native_frame


def produce(packets,numeric,rf,control,result):
    ingress=ProtocolIngress(lambda *_:None);ingress.decoder.numeric=numeric
    blocked=0;wait_seconds=0.;ordinal=0;examples={};sizes=Counter()
    def publish(kind,value):
        nonlocal blocked,wait_seconds,ordinal
        if kind!='samples':return
        rows=value.array if numeric else tuple(value)
        if numeric:rows.setflags(write=False)
        frame=Rf(int(rows[0][3]),len(rows),rows,1,ordinal);ordinal+=1
        sizes[len(rows)]+=1
        if len(rows) not in examples:examples[len(rows)]=frame
        try:rf.put_nowait(frame)
        except queue.Full:
            blocked+=1;started=time.perf_counter();rf.put(frame,timeout=10)
            wait_seconds+=time.perf_counter()-started
    ingress.on_event=publish
    try:
        control.send('ready');control.recv()
        start_cpu=time.process_time();start=time.perf_counter()
        for packet in packets:ingress.feed(packet)
        rf.put(None,timeout=10);rf.close();rf.join_thread()
        cpu=time.process_time()-start_cpu;elapsed=time.perf_counter()-start
        # Measure serialization separately, so instrumentation is not CPU work
        # in the timed decoder/Queue path. Examples span every fragment length.
        serialized={str(count):len(ForkingPickler.dumps(frame)) for count,frame in examples.items()}
        result.send(dict(producer_cpu_s=cpu,producer_elapsed_s=elapsed,full_events=blocked,
                         blocking_put_s=wait_seconds,frames=ordinal,fragment_counts=dict(sizes),
                         example_pickle_bytes_by_count=serialized))
    except BaseException as exc:result.send(dict(error=repr(exc)));raise
    finally:control.close();result.close()


def measure(packets,expected,numeric,capacity,consumer_pause):
    ctx=mp.get_context('spawn');rf=ctx.Queue(capacity)
    control,child_control=ctx.Pipe();result,child_result=ctx.Pipe(duplex=False)
    process=ctx.Process(target=produce,args=(packets,numeric,rf,child_control,child_result))
    process.start();child_control.close();child_result.close()
    gate=RfBarrier(block_size=None);gate.configure(1,0,0);verified=0;frames=0
    try:
        if not control.poll(10) or control.recv()!='ready':raise RuntimeError('Producer startup failed')
        start=time.perf_counter();start_cpu=time.process_time();control.send('start')
        if consumer_pause:time.sleep(consumer_pause)
        while True:
            frame=rf.get(timeout=10)
            if frame is None:break
            if numeric and (not isinstance(frame.payload,np.ndarray) or frame.payload.dtype!=np.uint32):
                raise AssertionError('Numeric payload changed through spawn Queue')
            if not gate.consume(frame):raise AssertionError('Unexpected barrier')
            rows=np.asarray(frame.payload,dtype=np.uint32)
            if not np.array_equal(rows,expected[frames]):raise AssertionError('RF sample corruption')
            verified+=len(rows);frames+=1
        consumer_cpu=time.process_time()-start_cpu;elapsed=time.perf_counter()-start
        if not result.poll(10):raise RuntimeError('Producer summary missing')
        summary=result.recv();process.join(10)
        if process.is_alive() or process.exitcode!=0 or 'error' in summary:raise RuntimeError(str(summary))
        if frames!=len(expected):raise AssertionError('Missing frame')
        return dict(mode='numeric' if numeric else 'tuples',elapsed_s=elapsed,
                    consumer_cpu_s=consumer_cpu,total_cpu_s=consumer_cpu+summary['producer_cpu_s'],
                    verified_samples=verified,verified_columns=verified*4,
                    numeric_equivalent_bytes=verified*4*4,wire_bytes=len(packets)*992,
                    queue_capacity=capacity,consumer_initial_pause_s=consumer_pause,**summary)
    finally:
        if process.is_alive():process.terminate();process.join(2)
        process.close();control.close();result.close();rf.close();rf.join_thread()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--frames',type=int,default=1500)
    args=parser.parse_args()
    if not 1<=args.frames<=3000:parser.error('--frames must be 1..3000')
    rows=[]
    for bits,channels in ((8,1),(14,2)):
        profile=next(p for p in PROFILES if (p['bits'],p['channels'])==(bits,channels))
        config=Configuration.from_wire(bits,code(profile));packets=[];expected=[];index=0
        capacity=(872*8//(bits*channels))&~3
        for sequence in range(args.frames):
            count=min(capacity,config.node_pairs-index%config.node_pairs)
            packet,samples=native_frame(config,index,count,(0xfffffff0+index*config.period)&0xffffffff,sequence)
            packets.append(packet);expected.append(samples);index+=count
        for queue_capacity,pause in ((16,0.),(2,.05)):
            for numeric in (False,True):
                measurement=measure(packets,expected,numeric,queue_capacity,pause)
                rows.append(dict(bits=bits,channels=channels,rate=config.rate,**measurement))
    root=Path(__file__).resolve().parents[1]
    sources=[Path(__file__).relative_to(root),Path('tests/v18/io/rf_vectors.py')]
    sources+=sorted(path.relative_to(root) for path in (root/'monitor/v18').rglob('*.py'))
    sources+=sorted(path.relative_to(root) for path in (root/'monitor/v18/receiver').glob('*profiles.json'))
    report=dict(at=datetime.now(timezone.utc).isoformat(),python=sys.version,executable=sys.executable,
                platform=platform.platform(),numpy=np.__version__,start_method='spawn',model_only=True,
                scope='Local full decoder -> Queue -> exact four-column consumer; no physical rate qualification',
                bytes_note='Pickle sizes are per observed fragment length examples, not compression; tuple sizes also depend on integer values.',
                pressure_note='full_events count observed queue.Full; blocking_put_s measures waiting; no qsize/peak inference.',
                timing_note='Spawn/input generation and serialization-size probes excluded; Queue feeder CPU included; consumer checks every column.',
                sources={str(path):hashlib.sha256((root/path).read_bytes()).hexdigest() for path in sources},measurements=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(output=str(args.output),measurements=rows),indent=2))


if __name__=='__main__':main()
