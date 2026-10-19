"""Analyze Linux durations; MCU cycles remain separate, correlated by sequence."""
import json
from pathlib import Path
import sys
STAGES=['prepare','ready','spi','validate','recv_control','accept','send','loop','between_loops']
FIELDS=['seq','index','node','epoch','queue','peak','mcu_previous_send_ticks','mcu_slack_ticks','produced','host_ns']
def analyze(log):
    rows=[];stages={};summary={}
    for line in log.splitlines():
        parts=line.split()
        if line.startswith('CAUSAL_SUMMARY '):summary={k:int(v) for k,v in (x.split('=') for x in parts[1:])}
        elif line.startswith('CAUSAL_STAGE '):
            i,total,maximum=map(int,parts[1:]);stages[STAGES[i]]=dict(total_ns=total,max_us=maximum/1000)
        elif line.startswith('CAUSAL '):
            values=list(map(int,parts[2:]));row=dict(zip(FIELDS,values[:10]));row['group']=parts[1]
            row['us']=dict(zip(STAGES,[v/1000 for v in values[10:]]));rows.append(row)
    count=summary.get('count',0)
    for value in stages.values():value['mean_us']=value['total_ns']/count/1000 if count else None
    unique={r['seq']:r for r in rows};slow=sorted(unique.values(),key=lambda r:r['us']['loop']+r['us']['between_loops'],reverse=True)
    for row in slow:row['largest_stage']=max((s for s in STAGES if s!='loop'),key=lambda s:row['us'][s])
    context=sorted([r for r in rows if r['group']=='event'],key=lambda r:r['host_ns'])
    peak4=next((r for r in context if r['peak']>=4),None)
    nearby=[]
    if peak4:
        at=context.index(peak4);nearby=context[max(0,at-32):at+16]
    return dict(summary=summary,stages=stages,slowest=slow[:20],first_peak4=peak4,peak4_context=nearby,
                note='Elapsed inclusive Linux times, not exclusive CPU. No subtraction between MCU and Linux clocks. Instrumented diagnostic is not rate acceptance.')
if __name__=='__main__':
    folder=Path(sys.argv[1]);result=analyze((folder/'causal_relay.log').read_text())
    (folder/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('slowest','peak4_context')},indent=2))
