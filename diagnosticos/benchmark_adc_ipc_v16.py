"""Local IPC throughput/CPU comparison with forced consumer pauses; no Q."""
import sys,time,gc,json,argparse,queue,multiprocessing as mp
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from monitor.historico.v16.adc_ipc import SharedAdcRing


def produce(channel,result,batches,rows):
    wall=time.perf_counter();cpu=time.process_time();durations=[];full=0
    for i in range(batches):
        data=np.full((rows,4),i,dtype=np.uint32)
        # Retry only for this throughput benchmark. The Q diagnostic rejects full.
        deadline=time.perf_counter()+10
        while True:
            began=time.perf_counter()
            try:channel.put_nowait(data)
            except queue.Full:
                full+=1
                if time.perf_counter()>deadline:raise TimeoutError('consumer stalled')
                time.sleep(.0001)
                continue
            durations.append((time.perf_counter()-began)*1000);break
    channel.close();channel.join_thread()
    result.send(dict(producer_cpu_ms=(time.process_time()-cpu)*1000,producer_wall_ms=(time.perf_counter()-wall)*1000,
        put_median_ms=float(np.median(durations)),put_p95_ms=float(np.percentile(durations,95)),put_max_ms=max(durations),full_retries=full))
    result.close()


def trial(shared,batches,rows):
    context=mp.get_context('spawn');channel=SharedAdcRing(context,rows=rows) if shared else context.Queue(32)
    parent,child=context.Pipe(False);process=context.Process(target=produce,args=(channel,child,batches,rows));process.start();child.close()
    began=time.perf_counter();cpu=time.process_time();pauses=[]
    try:
        for i in range(batches):
            data=channel.get(timeout=10)
            if data.shape!=(rows,4) or data.dtype!=np.uint32 or not np.all(data==i):raise ValueError('corrupt or reordered ADC IPC')
            if i%100==99:
                before=time.perf_counter();gc.collect();time.sleep(.02);pauses.append((time.perf_counter()-before)*1000)
        report=parent.recv();process.join(10)
        if process.exitcode!=0:raise RuntimeError('producer failed')
        report.update(transport='shared_ring' if shared else 'queue',samples=batches*rows,exact=True,
            total_wall_ms=(time.perf_counter()-began)*1000,consumer_cpu_ms=(time.process_time()-cpu)*1000,parent_pause_max_ms=max(pauses,default=0))
        return report
    finally:
        if process.is_alive():process.terminate();process.join()
        parent.close();channel.close();channel.join_thread()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--batches',type=int,default=1000);p.add_argument('--rows',type=int,default=2048);p.add_argument('--output',type=Path);args=p.parse_args()
    if args.batches<1 or args.rows<1:p.error('positive batches/rows required')
    result=dict(scope='Local IPC only; includes forced parent GC and 20 ms sleeps. Full retries measure throughput, not real-time acceptance.',cases=[])
    # Alternate order to expose order-dependent effects rather than one comparison.
    for shared in (False,True,True,False):result['cases'].append(trial(shared,args.batches,args.rows))
    text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text)

if __name__=='__main__':main()
