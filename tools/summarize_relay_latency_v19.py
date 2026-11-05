"""Read private relay latency summaries; no Q access."""
import argparse
import json
from pathlib import Path

STAGES=('tx_prepare','ready_wait','spi_ioctl','validate','policy','pc_receive','pc_send')
LIMITS=(5,20,50,100,200,400,600,1000,2000,10000)


def summarize(log):
    groups={}
    for line in log.splitlines():
        if not line.startswith('SCOPE_LATENCY '):continue
        row=json.loads(line[len('SCOPE_LATENCY '):]);phase=row['phase'];count=row['count']
        if phase not in range(4) or type(count) is not int or count<=0:
            raise ValueError('Invalid trace phase/count')
        if set(row['stages'])!=set(STAGES):raise ValueError('Incomplete trace stages')
        group=groups.setdefault(phase,dict(count=0,tcp_queue_peak=0,stages={
            stage:dict(sum_ns=0,max_ns=0,hist=[0]*11) for stage in STAGES}))
        group['count']+=count;group['tcp_queue_peak']=max(group['tcp_queue_peak'],row['tcp_queue_peak'])
        for stage in STAGES:
            value=row['stages'][stage];hist=value['hist']
            if len(hist)!=11 or any(type(n) is not int or n<0 for n in hist) or sum(hist)!=count:
                raise ValueError('Invalid histogram coverage')
            if (type(value['sum_ns']) is not int or type(value['max_ns']) is not int or
                    not 0<=value['max_ns']<=value['sum_ns']):raise ValueError('Invalid timing totals')
            target=group['stages'][stage];target['sum_ns']+=value['sum_ns']
            target['max_ns']=max(target['max_ns'],value['max_ns'])
            target['hist']=[a+b for a,b in zip(target['hist'],hist)]
    if not groups:raise ValueError('No completed relay latency summaries')
    for group in groups.values():
        total=sum(stage['sum_ns'] for stage in group['stages'].values())
        group['covered_mean_us']=total/group['count']/1000
        for stage in group['stages'].values():
            stage['mean_us']=stage['sum_ns']/group['count']/1000
            stage['max_us']=stage['max_ns']/1000
            stage['covered_fraction']=stage['sum_ns']/total if total else None
    return dict(phases=groups,histogram_upper_bounds_exclusive_us=LIMITS,
        caveat='Sequential wall times, not CPU utilization. Reply-observed phases. Excludes aggregation/logging and epoch-transition batches; READY includes MCU preparation and scheduling. Instrumented relay is diagnostic only.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=json.loads(args.report.read_text())
    result=summarize(report['candidate_relay_log'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for phase,group in result['phases'].items():
        print(phase,group['count'],{k:round(v['mean_us'],2) for k,v in group['stages'].items()})


if __name__=='__main__':main()
