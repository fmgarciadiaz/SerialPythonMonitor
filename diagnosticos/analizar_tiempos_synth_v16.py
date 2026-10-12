"""Host ACK interval accounting. Remaining time is NOT pure relay/Q RTT."""
import argparse,json,bisect
from pathlib import Path
import numpy as np

def analyze(trace,parent_pauses=()):
    metadata=trace.get('metadata',{}) if isinstance(trace,dict) else {}
    if isinstance(trace,dict):trace=trace['events']
    intervals={stage:[] for stage in ('generate','decode','read','send','adc_ipc','controls')}
    requests={};rows=[]
    for entry in trace:
        stage,start,end,rid=entry[:4]
        if stage in intervals:intervals[stage].append((start,end))
        if stage=='send':requests[rid]=end
        elif stage=='ack' and rid in requests:rows.append(dict(request_id=rid,start=requests.pop(rid),end=start))
    starts={stage:[a for a,b in values] for stage,values in intervals.items()}
    for row in rows:
        a,b=row.pop('start'),row.pop('end');row['send_return_to_ack_ms']=(b-a)*1000
        for stage,values in intervals.items():
            first=max(0,bisect.bisect_right(starts[stage],a)-1)
            last=bisect.bisect_left(starts[stage],b)
            row[stage+'_ms']=sum(max(0,min(y,b)-max(x,a)) for x,y in values[first:last])*1000
        row['unaccounted_ms']=max(0,row['send_return_to_ack_ms']-sum(row[s+'_ms'] for s in intervals))
    summary={key:dict(median=float(np.median([r[key] for r in rows])),p95=float(np.percentile([r[key] for r in rows],95)),max=float(max(r[key] for r in rows))) for key in rows[0] if key!='request_id'} if rows else {}
    gc_events=[e for e in trace if e[0]=='gc']
    gc_intervals=sorted((e[1],e[2]) for e in gc_events)
    gc_starts=[a for a,b in gc_intervals]
    def gc_overlap(start,end):
        first=max(0,bisect.bisect_right(gc_starts,start)-1)
        last=bisect.bisect_left(gc_starts,end)
        return sum(max(0,min(b,end)-max(a,start))*1000 for a,b in gc_intervals[first:last])
    decode=[dict(wall_ms=(e[2]-e[1])*1000,cpu_ms=e[4]*1000 if e[4] is not None else None,process_cpu_ms=e[5]*1000 if len(e)>5 else None,
                 gc_overlap_ms=gc_overlap(e[1],e[2]))
            for e in trace if e[0]=='decode' and len(e)>4]
    generated=[dict(wall_ms=(e[2]-e[1])*1000,cpu_ms=e[4]*1000 if len(e)>4 and e[4] is not None else None,process_cpu_ms=e[5]*1000 if len(e)>5 else None,
                    gc_overlap_ms=gc_overlap(e[1],e[2]))
               for e in trace if e[0]=='generate']
    slow_stages={stage:sorted([dict(start=e[1],wall_ms=(e[2]-e[1])*1000,cpu_ms=e[4]*1000 if len(e)>4 and e[4] is not None else None,process_cpu_ms=e[5]*1000 if len(e)>5 else None,gc_overlap_ms=gc_overlap(e[1],e[2])) for e in trace if e[0]==stage],key=lambda r:r['wall_ms'],reverse=True)[:10] for stage in (*intervals,'pump','source_render','voice_prepare','voice_render','piano_post','dac_convert')}
    for spans in slow_stages.values():
        for span in spans:
            a=span['start'];b=a+span['wall_ms']/1000
            span['parent_pause_overlap_ms']=sum(max(0,min(b,p['end'])-max(a,p['start']))*1000 for p in parent_pauses)
            span['parent_gc_overlap_ms']=sum(max(0,min(b,p['start']+p['gc_ms']/1000)-max(a,p['start']))*1000 for p in parent_pauses)
    return dict(parent_pause_events=len(parent_pauses),trace_metadata=metadata,trace_window=dict(events=len(trace),seconds=max((e[2] for e in trace),default=0)-min((e[1] for e in trace),default=0),receiver_limit_reached=bool(metadata.get('overwritten',0)) if metadata else len(trace)>=100000),queue_growth=[dict(time=e[1],target=e[3]) for e in trace if e[0]=='queue_growth'],slow_stages=slow_stages,scope='Host intervals; read includes waiting/ADC arrival; unaccounted includes other host work and transport, not pure Q RTT',requests=len(rows),summary_ms=summary,worst=sorted(rows,key=lambda r:r['send_return_to_ack_ms'],reverse=True)[:10],
                slow_decode=sorted(decode,key=lambda r:r['wall_ms'],reverse=True)[:10],slow_generate=sorted(generated,key=lambda r:r['wall_ms'],reverse=True)[:10],gc=dict(count=len(gc_events),max_ms=max(((e[2]-e[1])*1000 for e in gc_events),default=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--report',type=Path);args=p.parse_args()
    pauses=[]
    if args.report:
        cases=json.loads(args.report.read_text())['cases']
        pauses=next((c.get('parent_pause_events',[]) for c in cases if Path(c.get('trace_path','')).resolve()==args.trace.resolve()),[])
    result=analyze(json.loads(args.trace.read_text()),pauses)
    args.trace.with_name(args.trace.stem+'_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
