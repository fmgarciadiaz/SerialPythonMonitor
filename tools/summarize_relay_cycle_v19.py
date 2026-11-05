"""Summarize private full-cycle wall-time logs without Q access."""
import argparse
import json
from pathlib import Path


def summarize(log):
    phases={};events=[];ends=[]
    for line in log.splitlines():
        if line.startswith('SCOPE_CYCLE '):
            r=json.loads(line[len('SCOPE_CYCLE '):])
            if type(r['phase']) is not int or r['phase'] not in range(4):raise ValueError('Invalid phase')
            fields=('count','covered_ns','gap_ns','cycle_ns','max_gap_ns','max_cycle_ns')
            if any(type(r[k]) is not int or r[k]<0 for k in fields) or not r['count']:raise ValueError('Invalid totals')
            if r['covered_ns']+r['gap_ns']!=r['cycle_ns']:raise ValueError('Cycle partition mismatch')
            if r['max_gap_ns']>r['gap_ns'] or r['max_cycle_ns']>r['cycle_ns']:raise ValueError('Invalid maxima')
            g=phases.setdefault(str(r['phase']),dict.fromkeys(fields,0))
            for k in fields:g[k]=max(g[k],r[k]) if k.startswith('max_') else g[k]+r[k]
        elif line.startswith('SCOPE_CYCLE_EVENT '):
            r=json.loads(line[len('SCOPE_CYCLE_EVENT '):])
            if r['kind'] not in ('slow_cycle','peak_observed'):raise ValueError('Unknown event')
            if any(type(v) is not int or v<0 for k,v in r.items() if k!='kind'):raise ValueError('Invalid event value')
            if r['covered_ns']+r['gap_ns']!=r['cycle_ns']:raise ValueError('Event partition mismatch')
            if len(events)>=128:raise ValueError('Too many retained cycle events')
            events.append(r)
        elif line.startswith('SCOPE_CYCLE_END '):
            ends.append(json.loads(line[len('SCOPE_CYCLE_END '):]))
    if not phases:raise ValueError('No completed cycle summaries')
    for g in phases.values():
        for k in ('covered','gap','cycle'):g[k+'_mean_us']=g[k+'_ns']/g['count']/1000
        g['gap_fraction']=g['gap_ns']/g['cycle_ns'] if g['cycle_ns'] else None
    return dict(phases=phases,events=events,ends=ends,
        note='Relay monotonic wall time, not CPU. Cycle=covered stages+gap to next iteration; gap includes diagnostics/progress logging. MCU fields are reply-observed cumulative maxima/previous-node send, not simultaneous causal timestamps. Final incomplete cycles explicitly excluded.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('New output required')
    args.output.write_text(json.dumps(summarize(args.log.read_text()),indent=2)+'\n')

if __name__=='__main__':main()
